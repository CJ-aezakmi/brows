# ============================================================
# ФИНАЛЬНЫЙ РАБОЧИЙ БЛОК ДЛЯ ANTIC BROWSER (ДЕКАБРЬ 2025)
# Работает с PyInstaller --onedir + упакованная папка playwright-browsers
# Никаких установок, никаких ошибок Executable doesn't exist
# КРОССПЛАТФОРМЕННАЯ ВЕРСИЯ (Windows, macOS, Linux)
# ============================================================
import os
import sys
import platform
from pathlib import Path

# Защита от дублей в .exe (кроссплатформенная)
if getattr(sys, 'frozen', False):
    if platform.system() == 'Windows':
        import ctypes
        try:
            mutex = ctypes.windll.kernel32.CreateMutexW(None, True, "Global\\ANTIC_BROWSER_2025")
            if ctypes.windll.kernel32.GetLastError() == 183:
                sys.exit(0)
        except:
            pass  # Если не удалось создать mutex, продолжаем работу
    else:
        # Для Unix-систем (macOS, Linux) используем файл-блокировку
        import fcntl
        import tempfile as temp_module
        lock_file = os.path.join(temp_module.gettempdir(), 'antic_browser.lock')
        try:
            lock_handle = open(lock_file, 'w')
            fcntl.lockf(lock_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except IOError:
            sys.exit(0)  # Другой экземпляр уже запущен

# ─────── НАХОДИМ РАБОЧУЮ ПАПКУ playwright-browsers (в .exe она в _internal) ───────
# Кроссплатформенное определение папки браузеров
if getattr(sys, 'frozen', False):
    exe_dir = Path(sys.executable).parent
    search_paths = [
        exe_dir / "_internal" / "playwright-browsers",
        exe_dir / "playwright-browsers",
    ]
else:
    search_paths = [Path(__file__).parent / "playwright-browsers"]

# Определяем имя папки Chromium в зависимости от ОС
system = platform.system()
if system == 'Windows':
    chromium_subpath = "chrome-win"
    chromium_executable = "chrome.exe"
elif system == 'Darwin':  # macOS
    chromium_subpath = "chrome-mac"
    chromium_executable = "Chromium.app"
else:  # Linux
    chromium_subpath = "chrome-linux"
    chromium_executable = "chrome"

browsers_path = None
for p in search_paths:
    if p.exists():
        # Ищем папку chromium-* с правильным подкаталогом для текущей ОС
        for chromium_dir in os.listdir(p):
            if chromium_dir.startswith("chromium-"):
                chromium_path = p / chromium_dir / chromium_subpath
                if system == 'Darwin':
                    # На macOS проверяем наличие .app бандла
                    if (chromium_path / chromium_executable).exists():
                        browsers_path = p
                        break
                else:
                    # На Windows/Linux проверяем исполняемый файл
                    if (chromium_path / chromium_executable).exists():
                        browsers_path = p
                        break
        if browsers_path:
            break

if not browsers_path:
    # Если не нашли упакованные браузеры, используем стандартное расположение Playwright
    print("Используем стандартное расположение браузеров Playwright...")
    # Playwright установит браузеры в стандартное место, путь не нужно задавать
else:
    # Устанавливаем правильный путь только если нашли упакованные браузеры
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(browsers_path)
    print(f"Playwright браузер найден: {browsers_path}")

# ============================================================
# ВСЁ ГОТОВО — СТАНДАРТНЫЕ ИМПОРТЫ
# ============================================================
import json
import requests
import zipfile
import time
import tempfile
import threading
import warnings
import re
import subprocess
import shutil
warnings.filterwarnings("ignore", category=UserWarning, module="pproxy")

import flet as ft
if not hasattr(ft, "Colors") and hasattr(ft, "colors"):
    ft.Colors = ft.colors
if not hasattr(ft, "Icons") and hasattr(ft, "icons"):
    ft.Icons = ft.icons

import pytz
import pproxy
import asyncio
import geoip2.database
import random
from functools import lru_cache
from timezonefinder import TimezoneFinder
from playwright.async_api import async_playwright
from playwright.async_api._generated import BrowserContext

# ============================================================
# ТВОЙ КОД — АВТООБНОВЛЕНИЕ И ВЕРСИЯ
# ============================================================
CURRENT_VERSION = "1.0.0"
GITHUB_REPO = "CJ-aezakmi/brows"
UPDATE_CHECK_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

# Пути к файлам
BASE_DIR = os.path.dirname(__file__) if "__file__" in globals() else os.getcwd()
COUNTRY_DATABASE_PATH = os.path.join(BASE_DIR, "GeoLite2-Country.mmdb")
CITY_DATABASE_PATH = os.path.join(BASE_DIR, "GeoLite2-City.mmdb")
PROXY_CACHE_PATH = os.path.join(BASE_DIR, "proxy_cache.json")
CONFIG_DIR = os.path.join(BASE_DIR, "config")
COOKIES_DIR = os.path.join(BASE_DIR, "cookies")
PROXIES_FILE = os.path.join(BASE_DIR, "proxies.json")
API_KEYS_FILE = os.path.join(BASE_DIR, "api_keys.json")  # Файл для сохранения API ключей

# Пути к файлам
BASE_DIR = os.path.dirname(__file__)
COUNTRY_DATABASE_PATH = os.path.join(BASE_DIR, "GeoLite2-Country.mmdb")
CITY_DATABASE_PATH = os.path.join(BASE_DIR, "GeoLite2-City.mmdb")
PROXY_CACHE_PATH = os.path.join(BASE_DIR, "proxy_cache.json")
CONFIG_DIR = os.path.join(BASE_DIR, "config")
COOKIES_DIR = os.path.join(BASE_DIR, "cookies")
PROXIES_FILE = os.path.join(BASE_DIR, "proxies.json")

# Константы
SCREENS = ("800×600", "960×540", "1024×768", "1152×864", "1280×720", "1280×768", "1280×800", "1280×1024", "1366×768", "1408×792", "1440×900", "1400×1050", "1440×1080", "1536×864", "1600×900", "1600×1024", "1600×1200", "1680×1050", "1920×1080", "1920×1200", "2048×1152", "2560×1080", "2560×1440", "3440×1440")
LANGUAGES = ("en-US", "en-GB", "fr-FR", "ru-RU", "es-ES", "pl-PL", "pt-PT", "nl-NL", "zh-CN")
TIMEZONES = pytz.common_timezones

# Маппинг стран к языкам и timezone (для автонастройки под GEO прокси)
COUNTRY_SETTINGS = {
    "US": {"lang": "en-US", "timezone": "America/New_York"},
    "GB": {"lang": "en-GB", "timezone": "Europe/London"},
    "FR": {"lang": "fr-FR", "timezone": "Europe/Paris"},
    "DE": {"lang": "de-DE", "timezone": "Europe/Berlin"},
    "RU": {"lang": "ru-RU", "timezone": "Europe/Moscow"},
    "ES": {"lang": "es-ES", "timezone": "Europe/Madrid"},
    "IT": {"lang": "it-IT", "timezone": "Europe/Rome"},
    "PL": {"lang": "pl-PL", "timezone": "Europe/Warsaw"},
    "PT": {"lang": "pt-PT", "timezone": "Europe/Lisbon"},
    "NL": {"lang": "nl-NL", "timezone": "Europe/Amsterdam"},
    "CN": {"lang": "zh-CN", "timezone": "Asia/Shanghai"},
    "JP": {"lang": "ja-JP", "timezone": "Asia/Tokyo"},
    "KR": {"lang": "ko-KR", "timezone": "Asia/Seoul"},
    "BR": {"lang": "pt-BR", "timezone": "America/Sao_Paulo"},
    "CA": {"lang": "en-US", "timezone": "America/Toronto"},
    "AU": {"lang": "en-AU", "timezone": "Australia/Sydney"},
    "IN": {"lang": "en-IN", "timezone": "Asia/Kolkata"},
    "TR": {"lang": "tr-TR", "timezone": "Europe/Istanbul"},
    "MX": {"lang": "es-MX", "timezone": "America/Mexico_City"},
    "AR": {"lang": "es-AR", "timezone": "America/Argentina/Buenos_Aires"},
    "UA": {"lang": "uk-UA", "timezone": "Europe/Kiev"},
    "SE": {"lang": "sv-SE", "timezone": "Europe/Stockholm"},
    "NO": {"lang": "no-NO", "timezone": "Europe/Oslo"},
    "DK": {"lang": "da-DK", "timezone": "Europe/Copenhagen"},
    "FI": {"lang": "fi-FI", "timezone": "Europe/Helsinki"},
}

# Логирование
def log_message(message, level="INFO"):
    """Логирование сообщений с временной меткой"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")

# Функции для управления API ключами
def load_api_keys():
    """Загрузка сохраненных API ключей"""
    try:
        if os.path.isfile(API_KEYS_FILE):
            with open(API_KEYS_FILE, "r", encoding="utf-8") as f:
                keys = json.load(f)
                log_message("API ключи загружены")
                return keys
    except Exception as e:
        log_message(f"Ошибка загрузки API ключей: {str(e)}", "ERROR")
    return {"sx_org": "", "cyberyozh": ""}

def save_api_key(service: str, key: str):
    """Сохранение API ключа"""
    try:
        keys = load_api_keys()
        keys[service] = key
        with open(API_KEYS_FILE, "w", encoding="utf-8") as f:
            json.dump(keys, f, indent=4)
        log_message(f"API ключ для {service} сохранен")
        return True
    except Exception as e:
        log_message(f"Ошибка сохранения API ключа: {str(e)}", "ERROR")
        return False

# Система автообновления
class AutoUpdater:
    def __init__(self):
        self.current_version = CURRENT_VERSION
        self.github_repo = GITHUB_REPO
        self.update_url = UPDATE_CHECK_URL
        
    def check_for_updates(self):
        """Проверка наличия обновлений"""
        try:
            log_message("Проверяем наличие обновлений...")
            response = requests.get(self.update_url, timeout=10)
            response.raise_for_status()
            
            latest_release = response.json()
            latest_version = latest_release["tag_name"].lstrip("v")
            
            if self.is_newer_version(latest_version, self.current_version):
                log_message(f"Найдено обновление: {latest_version}")
                return {
                    "available": True,
                    "version": latest_version,
                    "download_url": latest_release["assets"][0]["browser_download_url"] if latest_release["assets"] else None,
                    "changelog": latest_release["body"]
                }
            else:
                log_message("Обновлений не найдено")
                return {"available": False}
                
        except Exception as e:
            log_message(f"Ошибка проверки обновлений: {str(e)}", "ERROR")
            return {"available": False, "error": str(e)}
    
    def is_newer_version(self, latest, current):
        """Сравнение версий"""
        try:
            latest_parts = [int(x) for x in latest.split('.')]
            current_parts = [int(x) for x in current.split('.')]
            
            # Дополняем до одинаковой длины
            while len(latest_parts) < len(current_parts):
                latest_parts.append(0)
            while len(current_parts) < len(latest_parts):
                current_parts.append(0)
            
            return latest_parts > current_parts
        except:
            return False
    
    def download_and_install_update(self, download_url, progress_callback=None):
        """Загрузка и установка обновления"""
        try:
            log_message("Загружаем обновление...")
            
            # Создаем временную директорию
            temp_dir = tempfile.mkdtemp()
            update_file = os.path.join(temp_dir, "update.zip")
            
            # Загружаем файл
            response = requests.get(download_url, stream=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(update_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback and total_size > 0:
                            progress = (downloaded / total_size) * 100
                            progress_callback(progress)
            
            log_message("Обновление загружено, устанавливаем...")
            
            # Извлекаем архив
            extract_dir = os.path.join(temp_dir, "extracted")
            with zipfile.ZipFile(update_file, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            # Создаем кроссплатформенный скрипт обновления
            current_exe = sys.executable if getattr(sys, 'frozen', False) else __file__
            current_dir = os.path.dirname(current_exe)
            
            if platform.system() == 'Windows':
                # Windows batch script
                update_script = os.path.join(temp_dir, "update.bat")
                with open(update_script, 'w', encoding='utf-8') as f:
                    f.write(f"""@echo off
timeout /t 3 /nobreak > nul
taskkill /f /im "{os.path.basename(current_exe)}" > nul 2>&1
xcopy /s /y "{extract_dir}\\*" "{current_dir}\\" > nul
start "" "{current_exe}"
del /q "{update_script}"
""")
                log_message("Запускаем установку обновления (Windows)...")
                subprocess.Popen([update_script], shell=True)
            else:
                # Unix shell script (macOS/Linux)
                update_script = os.path.join(temp_dir, "update.sh")
                with open(update_script, 'w', encoding='utf-8') as f:
                    f.write(f"""#!/bin/bash
sleep 3
pkill -f "{os.path.basename(current_exe)}" 2>/dev/null
cp -rf "{extract_dir}"/* "{current_dir}/"
chmod +x "{current_exe}"
"{current_exe}" &
rm -f "{update_script}"
""")
                os.chmod(update_script, 0o755)
                log_message("Запускаем установку обновления (Unix)...")
                subprocess.Popen(['/bin/bash', update_script])
            
            return True
            
        except Exception as e:
            log_message(f"Ошибка установки обновления: {str(e)}", "ERROR")
            return False

# Инициализация автообновления
updater = AutoUpdater()

# Безопасная загрузка USER_AGENTS
try:
    USER_AGENTS = requests.get("https://raw.githubusercontent.com/microlinkhq/top-user-agents/refs/heads/master/src/index.json", timeout=10).json()
    log_message(f"Загружено {len(USER_AGENTS)} User Agents")
except:
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ]
    log_message("Используются стандартные User Agents")

# Загрузка кэша прокси
_proxy_check_cache = {}
if os.path.isfile(PROXY_CACHE_PATH):
    try:
        with open(PROXY_CACHE_PATH, "r", encoding="utf-8") as f:
            _proxy_check_cache = json.load(f)
        log_message(f"Загружен кэш прокси: {len(_proxy_check_cache)} записей")
    except:
        _proxy_check_cache = {}
        log_message("Не удалось загрузить кэш прокси")

# SX.ORG API класс с улучшенной обработкой ошибок
class SXOrgAPI:
    def __init__(self):
        self.base_url = "https://api.sx.org/"
        self.api_key = ""
        self.countries = []
        self.states = []
        self.cities = []
        self.ports = []
        self.balance = "0.00"
        self.authenticated = False
        log_message("SXOrgAPI инициализирован")
    
    def validate_key(self, api_key):
        log_message(f"Проверяем API ключ: {api_key[:10]}...")
        self.api_key = api_key
        try:
            # Используем более надежный способ запроса с повторными попытками
            for attempt in range(3):
                try:
                    response = requests.get(
                        f"{self.base_url}v2/plan/info", 
                        params={"apiKey": api_key}, 
                        timeout=15,
                        headers={'User-Agent': 'Antic Browser v1.0.0'}
                    )
                    response.raise_for_status()
                    data = response.json()
                    break
                except requests.exceptions.RequestException as e:
                    if attempt == 2:
                        raise e
                    time.sleep(1)
            
            if not data.get('success'):
                self.authenticated = False
                log_message("API ключ неверный")
                return False, "Неверный API ключ или недостаточно прав"
            
            # Получаем баланс
            resp_balance = requests.get(
                f"{self.base_url}v2/user/balance", 
                params={"apiKey": api_key}, 
                timeout=15,
                headers={'User-Agent': 'Antic Browser v1.0.0'}
            )
            resp_balance.raise_for_status()
            balance_data = resp_balance.json()
            self.balance = balance_data.get('balance', '0.00') if balance_data.get('success') else '0.00'
            
            # Получаем страны
            resp_countries = requests.get(
                f"{self.base_url}v2/dir/countries", 
                params={"apiKey": api_key}, 
                timeout=15,
                headers={'User-Agent': 'Antic Browser v1.0.0'}
            )
            resp_countries.raise_for_status()
            countries_data = resp_countries.json()
            if countries_data.get('success'):
                self.countries = countries_data['countries']
                priority_countries = {"United States", "Russia", "Germany", "United Kingdom", "Canada"}
                prioritized = [c for c in self.countries if c['name'] in priority_countries]
                others = [c for c in self.countries if c['name'] not in priority_countries]
                others.sort(key=lambda x: x['name'])
                self.countries = prioritized + others
                log_message(f"Загружено {len(self.countries)} стран")
            
            self.authenticated = True
            log_message(f"API ключ валиден, баланс: ${self.balance}")
            return True, f"Баланс: ${self.balance}"
        except Exception as e:
            self.authenticated = False
            log_message(f"Ошибка валидации API: {str(e)}", "ERROR")
            return False, str(e)
    
    def get_states(self, country_id):
        log_message(f"Получаем штаты для страны ID: {country_id}")
        try:
            resp = requests.get(
                f"{self.base_url}v2/dir/states", 
                params={"apiKey": self.api_key, "countryId": country_id}, 
                timeout=15,
                headers={'User-Agent': 'Antic Browser v1.0.0'}
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get('success'):
                self.states = sorted(data['states'], key=lambda x: x['name'])
                log_message(f"Загружено {len(self.states)} штатов")
                return True, self.states
            log_message("Ошибка получения штатов")
            return False, "Ошибка получения штатов"
        except Exception as e:
            log_message(f"Исключение при получении штатов: {str(e)}", "ERROR")
            return False, str(e)
    
    def get_cities(self, state_id, country_id):
        log_message(f"Получаем города для штата ID: {state_id}")
        try:
            resp = requests.get(
                f"{self.base_url}v2/dir/cities", 
                params={"apiKey": self.api_key, "stateId": state_id, "countryId": country_id}, 
                timeout=15,
                headers={'User-Agent': 'Antic Browser v1.0.0'}
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get('success'):
                self.cities = sorted(data['cities'], key=lambda x: x['name'])
                log_message(f"Загружено {len(self.cities)} городов")
                return True, self.cities
            log_message("Ошибка получения городов")
            return False, "Ошибка получения городов"
        except Exception as e:
            log_message(f"Исключение при получении городов: {str(e)}", "ERROR")
            return False, str(e)
    
    def create_proxy(self, country_code, state_name, city_name, connection_type, proxy_types, proxy_name):
        log_message(f"Создаем прокси: {proxy_name}")
        try:
            type_map = {"keep-connection": 2, "rotate-connection": 3}
            type_id = type_map.get(connection_type)
            
            proxy_type_id = 1 if "residential" in proxy_types else 3 if "mobile" in proxy_types else 4 if "corporate" in proxy_types else 2
            
            data = {
                "country_code": country_code,
                "state": state_name,
                "city": city_name,
                "type_id": type_id,
                "proxy_type_id": proxy_type_id,
                "server_port_type_id": 0,
                "name": proxy_name
            }
            
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "Antic Browser v1.0.0"
            }
            
            resp = requests.post(
                f"{self.base_url}v2/proxy/create-port", 
                params={"apiKey": self.api_key}, 
                headers=headers, 
                data=json.dumps(data), 
                timeout=30
            )
            resp.raise_for_status()
            result = resp.json()
            
            if result.get('success'):
                proxy_data = result.get('data', [result]) if isinstance(result.get('data'), list) else [result.get('data')]
                proxies = []
                for p in proxy_data:
                    proxy_str = f"http://{p.get('login')}:{p.get('password')}@{p.get('server')}:{p.get('port')}"
                    proxies.append(proxy_str)
                log_message(f"Создано {len(proxies)} прокси")
                return True, proxies
            else:
                log_message(f"Ошибка создания прокси: {result.get('message', 'Неизвестная ошибка')}")
                return False, result.get('message', 'Неизвестная ошибка')
        except Exception as e:
            log_message(f"Исключение при создании прокси: {str(e)}", "ERROR")
            return False, str(e)
    
    def get_ports(self):
        log_message("Получаем список портов")
        try:
            resp = requests.get(
                f"{self.base_url}v2/proxy/ports", 
                params={"apiKey": self.api_key}, 
                timeout=15,
                headers={'User-Agent': 'Antic Browser v1.0.0'}
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get('success'):
                self.ports = data['message'].get('proxies', [])
                log_message(f"Загружено {len(self.ports)} портов")
                return True, self.ports
            log_message(f"Ошибка получения портов: {data.get('message', 'Неизвестная ошибка')}")
            return False, data.get('message', 'Неизвестная ошибка')
        except Exception as e:
            log_message(f"Исключение при получении портов: {str(e)}", "ERROR")
            return False, str(e)

# CyberYozh API класс с улучшенной обработкой ошибок
class CyberYozhAPI:
    def __init__(self):
        self.base_url = "https://app.cyberyozh.com/api/v1/"
        self.api_key = ""
        self.balance = 0
        self.countries = []
        self.proxies = []
        self.authenticated = False
        log_message("CyberYozhAPI инициализирован")
    
    def validate_key(self, api_key):
        log_message(f"Проверяем API ключ CyberYozh: {api_key[:10]}...")
        self.api_key = api_key
        try:
            # Баланс доступен только на v2
            response = requests.get(
                "https://app.cyberyozh.com/api/v2/users/balance/", 
                headers={
                    'X-Api-Key': api_key,  # Правильный заголовок с заглавными буквами
                    'User-Agent': 'Antic Browser v1.0.0'
                },
                timeout=15
            )
            response.raise_for_status()
            
            # Ответ возвращает просто число: "1.71$"
            balance_text = response.text.strip()
            try:
                # Убираем символ $ и конвертируем в число
                self.balance = float(balance_text.replace('$', '').strip())
            except:
                self.balance = balance_text
            
            self.authenticated = True
            log_message(f"API ключ CyberYozh валиден, баланс: {self.balance}")
            return True, f"Баланс: ${self.balance}"
        except Exception as e:
            self.authenticated = False
            log_message(f"Ошибка валидации API CyberYozh: {str(e)}", "ERROR")
            return False, str(e)
    
    def get_countries(self):
        """Получение списка доступных стран из магазина прокси"""
        log_message("Получаем список стран CyberYozh")
        try:
            response = requests.get(
                f"{self.base_url}proxies/shop/",
                headers={
                    'X-Api-Key': self.api_key,
                    'User-Agent': 'Antic Browser v1.0.0'
                },
                timeout=15
            )
            response.raise_for_status()
            data = response.json()
            
            # Парсим данные магазина и извлекаем уникальные страны
            countries = []
            if isinstance(data, dict) and 'results' in data:
                # Извлекаем уникальные коды стран
                country_codes = set()
                for item in data['results']:
                    if 'country_code' in item:
                        country_codes.add(item['country_code'])
                countries = sorted(list(country_codes))
            
            self.countries = countries
            log_message(f"Загружено {len(countries)} стран CyberYozh")
            return True, countries
        except Exception as e:
            log_message(f"Ошибка получения стран CyberYozh: {str(e)}", "ERROR")
            return False, str(e)
    
    def create_proxy(self, proxy_id, auto_renew=False):
        """Покупка прокси по ID продукта из магазина"""
        log_message(f"Покупаем прокси CyberYozh: id={proxy_id}, auto_renew={auto_renew}")
        try:
            # API v1 PurchaseRequest schema: array of objects with 'id' (uuid) and 'auto_renew'
            data = [{
                "id": proxy_id,
                "auto_renew": auto_renew
            }]
            
            response = requests.post(
                f"{self.base_url}proxies/shop/buy_proxies/",
                json=data,
                headers={
                    'X-Api-Key': self.api_key,
                    'Content-Type': 'application/json',
                    'User-Agent': 'Antic Browser v1.0.0'
                },
                timeout=30
            )
            # Обрабатываем дружелюбные сообщения
            if response.status_code >= 400:
                try:
                    err = response.json()
                except:
                    err = {"detail": response.text}
                msg = err.get('message') or err.get('detail') or 'Ошибка запроса'
                return False, translate_cyberyozh_message(msg)

            result = response.json()
            
            log_message(f"Прокси куплен успешно: {result}")
            # Возвращаем дружелюбное сообщение, если есть статус/сообщение
            try:
                if isinstance(result, list) and result:
                    item = result[0]
                    status = item.get('status')
                    msg = item.get('message')
                    friendly = translate_cyberyozh_message(msg) if msg else None
                    if status and friendly:
                        return False if status == 'canceled' else True, friendly
            except Exception:
                pass
            return True, 'Покупка успешно инициирована'
        except Exception as e:
            log_message(f"Ошибка покупки прокси CyberYozh: {str(e)}", "ERROR")
            return False, str(e)
    
    def get_shop_proxies(self, country_code=None, access_type=None, category=None):
        """Получение списка доступных прокси в магазине"""
        log_message(f"Получаем список прокси в магазине CyberYozh")
        try:
            params = {}
            if country_code:
                params['country_code'] = country_code
            if access_type:
                params['access_type'] = access_type
            if category:
                params['category'] = category
            
            response = requests.get(
                f"{self.base_url}proxies/shop/",
                params=params,
                headers={
                    'X-Api-Key': self.api_key,
                    'User-Agent': 'Antic Browser v1.0.0'
                },
                timeout=15
            )
            response.raise_for_status()
            result = response.json()
            
            proxies = result.get('results', []) if isinstance(result, dict) else result
            log_message(f"Найдено {len(proxies)} прокси в магазине")
            return True, proxies
        except Exception as e:
            log_message(f"Ошибка получения магазина CyberYozh: {str(e)}", "ERROR")
            return False, str(e)

def translate_cyberyozh_message(msg: str) -> str:
    """Переводит системные ответы CyberYozh в понятные русские сообщения."""
    if not msg:
        return "Неизвестная ошибка"
    text = msg.strip()
    mapping = {
        "Not enough money.": "Недостаточно средств",
        "Request was throttled.": "Слишком много запросов. Попробуйте позже",
        "Invalid API Key": "Неверный API ключ",
        "Bad Request": "Некорректный запрос",
        "Unauthorized": "Неавторизовано",
        "Forbidden": "Доступ запрещён",
        "Not Found": "Элемент не найден",
        "Too Many Requests": "Слишком много запросов",
        "Internal Server Error": "Внутренняя ошибка сервера",
    }
    # Точное совпадение
    if text in mapping:
        return mapping[text]
    # Эвристики
    if "money" in text.lower():
        return "Недостаточно средств"
    if "throttle" in text.lower() or "too many" in text.lower():
        return "Слишком много запросов. Попробуйте позже"
    return text
    
    def get_proxies(self, protocol='http', type_format='full_url'):
            """Получение списка купленных прокси с credentials"""
            log_message(f"Получаем список купленных прокси CyberYozh (protocol={protocol}, format={type_format})")
            try:
                # Используем /proxies/history/ который возвращает полную информацию
                response = requests.get(
                    f"{self.base_url}proxies/history/",
                    headers={
                        'X-Api-Key': self.api_key,
                        'User-Agent': 'Antic Browser v1.0.0'
                    },
                    timeout=15
                )
                response.raise_for_status()
                result = response.json()
            
                proxies = []
                # Парсим ответ с полной информацией о прокси
                if isinstance(result, dict) and 'results' in result:
                    for item in result['results']:
                        try:
                            # Пропускаем истекшие прокси
                            if item.get('expired', False):
                                continue
                        
                            # Извлекаем данные для подключения
                            host = item.get('connection_host', '')
                            port = item.get('connection_port', '')
                            login = item.get('connection_login', '')
                            password = item.get('connection_password', '')
                        
                            # Определяем протокол из URL или используем заданный
                            url = item.get('url', '')
                            if url.startswith('socks5://') or url.startswith('socks5_http://'):
                                proxy_protocol = 'socks5'
                            else:
                                proxy_protocol = protocol
                        
                            # Формируем прокси в нужном формате
                            if type_format == 'full_url':
                                proxy_str = f"{proxy_protocol}://{login}:{password}@{host}:{port}"
                            elif type_format == 'ip_port_user_pass':
                                proxy_str = f"{host}:{port}:{login}:{password}"
                            elif type_format == 'user_pass_at_ip_port':
                                proxy_str = f"{login}:{password}@{host}:{port}"
                            else:
                                proxy_str = f"{proxy_protocol}://{login}:{password}@{host}:{port}"
                        
                            proxies.append(proxy_str)
                        except Exception as e:
                            log_message(f"Ошибка парсинга прокси: {str(e)}", "ERROR")
                            continue
            
                log_message(f"Получено {len(proxies)} прокси CyberYozh")
                return True, proxies if proxies else []
            except Exception as e:
                log_message(f"Ошибка получения прокси CyberYozh: {str(e)}", "ERROR")
                return False, str(e)
    
    def download_proxies_txt(self, protocol='http', type_format='full_url'):
        """Скачивание всех прокси в текстовом формате (для импорта)"""
        log_message(f"Скачиваем прокси CyberYozh в TXT формате (protocol={protocol}, format={type_format})")
        try:
            params = {
                'type_format': type_format
            }
            if protocol:
                params['protocol'] = protocol
            
            response = requests.get(
                f"{self.base_url}proxies/proxy-credentials/download/",
                params=params,
                headers={
                    'X-Api-Key': self.api_key,
                    'User-Agent': 'Antic Browser v1.0.0'
                },
                timeout=30
            )
            response.raise_for_status()
            
            # Ответ в формате plain text со списком прокси
            proxies_text = response.text.strip()
            proxies = [p.strip() for p in proxies_text.split('\n') if p.strip()]
            
            log_message(f"Скачано {len(proxies)} прокси CyberYozh")
            return True, proxies
        except Exception as e:
            log_message(f"Ошибка скачивания прокси CyberYozh: {str(e)}", "ERROR")
            return False, str(e)

# Глобальные переменные для API
sx_api = SXOrgAPI()
cyberyozh_api = CyberYozhAPI()

# Загружаем сохраненные API ключи
saved_api_keys = load_api_keys()
if saved_api_keys.get("sx_org"):
    sx_api.api_key = saved_api_keys["sx_org"]
if saved_api_keys.get("cyberyozh"):
    cyberyozh_api.api_key = saved_api_keys["cyberyozh"]

# Глобальные переменные для UI
current_page = "proxies"
main_page_ref = None

# Улучшенная система уведомлений
class NotificationSystem:
    def __init__(self, page: ft.Page):
        self.page = page
        self.notifications = []
        
    def show_notification(self, title, message, type="info", duration=5000):
        """Показать уведомление"""
        try:
            color = ft.Colors.BLUE
            icon = ft.Icons.INFO
            
            if type == "success":
                color = ft.Colors.GREEN
                icon = ft.Icons.CHECK_CIRCLE
            elif type == "error":
                color = ft.Colors.RED
                icon = ft.Icons.ERROR
            elif type == "warning":
                color = ft.Colors.ORANGE
                icon = ft.Icons.WARNING
            
            # Создаем уведомление
            notification = ft.Container(
                content=ft.Row([
                    ft.Icon(icon, color=ft.Colors.WHITE, size=20),
                    ft.Column([
                        ft.Text(title, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD, size=14),
                        ft.Text(message, color=ft.Colors.WHITE, size=12)
                    ], expand=True, spacing=2),
                    ft.IconButton(
                        ft.Icons.CLOSE,
                        icon_color=ft.Colors.WHITE,
                        icon_size=16,
                        on_click=lambda e: self.hide_notification(notification)
                    )
                ], spacing=10),
                bgcolor=color,
                padding=15,
                border_radius=10,
                margin=ft.margin.only(bottom=10),
                shadow=ft.BoxShadow(blur_radius=10, color=ft.Colors.BLACK26),
                animate_opacity=300
            )
            
            # Добавляем в список уведомлений
            self.notifications.append(notification)
            
            # Обновляем интерфейс
            self.update_notifications_display()
            
            # Автоматически скрываем через указанное время
            def auto_hide():
                time.sleep(duration / 1000)
                if notification in self.notifications:
                    self.hide_notification(notification)
            
            threading.Thread(target=auto_hide, daemon=True).start()
            
        except Exception as e:
            log_message(f"Ошибка показа уведомления: {str(e)}", "ERROR")
    
    def hide_notification(self, notification):
        """Скрыть уведомление"""
        try:
            if notification in self.notifications:
                self.notifications.remove(notification)
                self.update_notifications_display()
        except Exception as e:
            log_message(f"Ошибка скрытия уведомления: {str(e)}", "ERROR")
    
    def update_notifications_display(self):
        """Обновить отображение уведомлений"""
        try:
            # Создаем контейнер для уведомлений в правом верхнем углу
            if hasattr(self.page, 'overlay'):
                # Очищаем старые уведомления
                self.page.overlay.clear()
                
                if self.notifications:
                    notifications_container = ft.Container(
                        content=ft.Column(
                            controls=self.notifications[-5:],  # Показываем только последние 5
                            spacing=5
                        ),
                        right=20,
                        top=80,
                        width=350
                    )
                    self.page.overlay.append(notifications_container)
                
                self.page.update()
        except Exception as e:
            log_message(f"Ошибка обновления уведомлений: {str(e)}", "ERROR")

# Глобальная система уведомлений
notification_system = None

async def save_cookies(context: BrowserContext, profile: str) -> None:
    """Сохранение cookies с улучшенной обработкой ошибок"""
    try:
        cookies = await context.cookies()
        for cookie in cookies:
            cookie.pop("sameSite", None)
        
        os.makedirs(COOKIES_DIR, exist_ok=True)
        cookies_file = os.path.join(COOKIES_DIR, profile)
        
        with open(cookies_file, "w", encoding="utf-8") as f:
            json.dump(obj=cookies, fp=f, indent=4)
        
        log_message(f"Cookies сохранены для профиля: {profile}")
    except Exception as e:
        log_message(f"Ошибка сохранения cookies: {str(e)}", "ERROR")

def parse_netscape_cookies(netscape_cookie_str: str) -> list[dict]:
    """Парсинг cookies в формате Netscape"""
    cookies = []
    lines = netscape_cookie_str.strip().split("\n")
    for line in lines:
        if not line.startswith("#") and line.strip():
            parts = line.split()
            if len(parts) == 7:
                cookie = {
                    "domain": parts[0],
                    "httpOnly": parts[1].upper() == "TRUE",
                    "path": parts[2],
                    "secure": parts[3].upper() == "TRUE",
                    "expires": float(parts[4]),
                    "name": parts[5],
                    "value": parts[6]
                }
                cookies.append(cookie)
    return cookies

@lru_cache(maxsize=256)
def get_proxy_info(ip: str) -> dict:
    """Получение информации о прокси по IP"""
    try:
        with geoip2.database.Reader(COUNTRY_DATABASE_PATH) as reader:
            response = reader.country(ip)
            country_code = response.country.iso_code
    except:
        country_code = "UNK"
    
    latitude = None
    longitude = None
    city = "UNK"
    timezone = None
    
    try:
        with geoip2.database.Reader(CITY_DATABASE_PATH) as reader:
            response = reader.city(ip)
            city = response.city.name if response.city.name else "UNK"
            latitude = response.location.latitude
            longitude = response.location.longitude
            timezone = TimezoneFinder().timezone_at(lng=longitude, lat=latitude)
    except:
        pass
    
    result = {"country_code": country_code, "city": city, "timezone": timezone}
    if latitude is not None and longitude is not None:
        result["latitude"] = latitude
        result["longitude"] = longitude
    
    return result

async def run_proxy(protocol: str, ip: str, port: int, login: str, password: str):
    """Запуск прокси сервера"""
    try:
        server = pproxy.Server("socks5://127.0.0.1:1337")
        remote = pproxy.Connection(f"{protocol}://{ip}:{port}#{login}:{password}")
        args = dict(rserver=[remote], verbose=print)
        await server.start_server(args)
    except Exception as e:
        log_message(f"Ошибка запуска прокси сервера: {str(e)}", "ERROR")

async def run_browser(user_agent: str, height: int, width: int, timezone: str, lang: str, proxy: str | bool, cookies: str | bool, webgl: bool, vendor: str, cpu: int, ram: int, is_touch: bool, profile: str) -> None:
    """Запуск браузера с улучшенной обработкой ошибок и уведомлениями"""
    log_message(f"Запускаем браузер для профиля: {profile}")
    
    try:
        async with async_playwright() as p:
            args = [
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-web-security",
                "--ignore-certificate-errors",
                "--disable-infobars",
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",  # Для стабильности в режиме администратора
                "--no-first-run",
                "--disable-default-apps",
                "--enable-features=NetworkService,NetworkServiceInProcess"  # DoNotTrack
            ]
            
            if not webgl:
                args.append("--disable-webgl")
            
            proxy_settings = None
            proxy_task = None
            proxy_ip = None
            
            if proxy:
                try:
                    protocol = proxy.split("://")[0]
                    if "@" in proxy:
                        splitted = proxy.split("://")[1].split("@")
                        ip = splitted[1].split(":")[0]
                        port = int(splitted[1].split(":")[1])
                        username = splitted[0].split(":")[0]
                        password = splitted[0].split(":")[1]
                    else:
                        splitted = proxy.split("://")[1].split(":")
                        ip = splitted[0]
                        port = int(splitted[1])
                        username = ""
                        password = ""
                    
                    proxy_ip = ip  # Сохраняем IP для автонастройки
                    
                    # Получаем GEO информацию о прокси
                    try:
                        proxy_geo = get_proxy_info(ip)
                        country_code = proxy_geo.get("country_code", "US")
                        
                        # Автонастройка языка и timezone по GEO прокси
                        if country_code in COUNTRY_SETTINGS:
                            auto_settings = COUNTRY_SETTINGS[country_code]
                            # Используем GEO timezone если он доступен, иначе дефолтный для страны
                            timezone = proxy_geo.get("timezone") or auto_settings["timezone"]
                            lang = auto_settings["lang"]
                            log_message(f"Автонастройка под прокси: {country_code}, язык={lang}, timezone={timezone}")
                        else:
                            # Используем GEO timezone если он доступен
                            if proxy_geo.get("timezone"):
                                timezone = proxy_geo["timezone"]
                                log_message(f"Использую GEO timezone: {timezone}")
                    except Exception as e:
                        log_message(f"Ошибка получения GEO данных прокси: {e}", "ERROR")
                        
                    if protocol == "http":
                        proxy_settings = {
                            "server": f"{ip}:{port}",
                            "username": username,
                            "password": password
                        }
                    else:
                        proxy_task = asyncio.create_task(run_proxy(protocol, ip, port, username, password))
                        proxy_settings = {
                            "server": "socks5://127.0.0.1:1337"
                        }
                except Exception as e:
                    log_message(f"Ошибка настройки прокси: {str(e)}", "ERROR")
                    if notification_system:
                        notification_system.show_notification("Ошибка прокси", f"Не удалось настроить прокси: {str(e)}", "error")
            
            # Загружаем расширение CyberYozh, если есть распакованная папка extensions/cyberyozh
            extension_id = None
            temp_user_data = None
            try:
                ext_dir = Path(__file__).parent / "extensions" / "cyberyozh"
                if ext_dir.exists():
                    args.extend([
                        f"--disable-extensions-except={ext_dir}",
                        f"--load-extension={ext_dir}"
                    ])
                    # ID расширения CyberYozh (вычислен из public key в manifest.json)
                    extension_id = "paljcopanhinogelplkpgfnljiomaapc"
                    
                    # Создаем временную директорию для persistent context с закрепленным расширением
                    import tempfile
                    temp_user_data = tempfile.mkdtemp(prefix="antic_browser_")
                    prefs_dir = Path(temp_user_data) / "Default"
                    prefs_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Создаем Preferences файл с закрепленным расширением в toolbar
                    preferences = {
                        "extensions": {
                            "pinned_extensions": [extension_id],
                            "toolbar": [extension_id]
                        }
                    }
                    
                    with open(prefs_dir / "Preferences", "w") as f:
                        json.dump(preferences, f)
                    
                    log_message(f"Загружаем расширение CyberYozh из {ext_dir} с закреплением")
                else:
                    log_message("Папка расширения CyberYozh не найдена (extensions/cyberyozh), пропускаем загрузку")
            except Exception as e:
                log_message(f"Ошибка загрузки расширения: {e}", "ERROR")

            # Получаем координаты для геолокации из GEO данных прокси
            geolocation = None
            if proxy_ip:
                try:
                    proxy_geo = get_proxy_info(proxy_ip)
                    if "latitude" in proxy_geo and "longitude" in proxy_geo:
                        geolocation = {
                            "latitude": proxy_geo["latitude"],
                            "longitude": proxy_geo["longitude"]
                        }
                        log_message(f"Геолокация установлена: {geolocation}")
                except Exception as e:
                    log_message(f"Ошибка получения координат: {e}", "ERROR")
            
            # Формируем Accept-Language заголовок
            accept_language = f"{lang},{lang.split('-')[0]};q=0.9,en-US;q=0.8,en;q=0.7"
            
            # Используем persistent context если нужно закрепить расширение
            if temp_user_data:
                context = await p.chromium.launch_persistent_context(
                    temp_user_data,
                    headless=False,
                    args=args,
                    user_agent=user_agent,
                    viewport={"width": width, "height": height},
                    locale=lang,
                    timezone_id=timezone,
                    geolocation=geolocation,
                    permissions=["geolocation"] if geolocation else None,
                    extra_http_headers={"Accept-Language": accept_language},
                    proxy=proxy_settings if proxy_settings else None
                )
                browser = None  # При persistent context нет отдельного объекта browser
            else:
                browser = await p.chromium.launch(headless=False, args=args)
                context = await browser.new_context(
                    user_agent=user_agent,
                    viewport={"width": width, "height": height},
                    locale=lang,
                    timezone_id=timezone,
                    has_touch=is_touch,
                    geolocation=geolocation,
                    permissions=["geolocation"] if geolocation else None,
                    extra_http_headers={"Accept-Language": accept_language},
                    proxy=proxy_settings if proxy_settings else None
                )
            
            # Добавляем скрипты для маскировки
            await context.add_init_script(f"""
                Object.defineProperty(navigator, 'vendor', {{
                    get: function() {{
                        return '{vendor}';
                    }}
                }});
            """)
            
            await context.add_init_script(f"""
                Object.defineProperty(navigator, 'hardwareConcurrency', {{
                    get: function() {{
                        return {cpu};
                    }}
                }});
            """)
            
            await context.add_init_script(f"""
                Object.defineProperty(navigator, 'deviceMemory', {{
                    get: function() {{
                        return {ram};
                    }}
                }});
            """)
            
            # Маскировка языков
            await context.add_init_script(f"""
                Object.defineProperty(navigator, 'language', {{
                    get: function() {{
                        return '{lang}';
                    }}
                }});
                Object.defineProperty(navigator, 'languages', {{
                    get: function() {{
                        return ['{lang}', '{lang.split("-")[0]}', 'en-US', 'en'];
                    }}
                }});
            """)
            
            # Блокировка WebRTC утечек IP
            await context.add_init_script("""
                // Отключаем enumerateDevices для WebRTC
                if (navigator.mediaDevices && navigator.mediaDevices.enumerateDevices) {
                    navigator.mediaDevices.enumerateDevices = function() {
                        return Promise.resolve([]);
                    };
                }
                
                // Переопределяем RTCPeerConnection для маскировки IP
                const original_RTCPeerConnection = window.RTCPeerConnection || window.webkitRTCPeerConnection || window.mozRTCPeerConnection;
                if (original_RTCPeerConnection) {
                    window.RTCPeerConnection = function(...args) {
                        const pc = new original_RTCPeerConnection(...args);
                        const original_createOffer = pc.createOffer;
                        pc.createOffer = function() {
                            return Promise.reject(new Error('WebRTC is disabled'));
                        };
                        return pc;
                    };
                }
            """)
            
            # Загрузка cookies
            cookies_parsed = []
            if cookies and not os.path.isfile(os.path.join(COOKIES_DIR, profile)):
                try:
                    with open(cookies, "r", encoding="utf-8") as f:
                        cookies_content = f.read()
                        try:
                            cookies_parsed = json.loads(cookies_content)
                        except json.decoder.JSONDecodeError:
                            cookies_parsed = parse_netscape_cookies(cookies_content)
                except Exception as e:
                    log_message(f"Ошибка загрузки cookies из файла: {str(e)}", "ERROR")
                    
            elif os.path.exists(os.path.join(COOKIES_DIR, profile)):
                try:
                    with open(os.path.join(COOKIES_DIR, profile), "r", encoding="utf-8") as f:
                        cookies_parsed = json.loads(f.read())
                except Exception as e:
                    log_message(f"Ошибка загрузки сохраненных cookies: {str(e)}", "ERROR")
                    cookies_parsed = []
            
            # Добавляем cookies в контекст
            for cookie in cookies_parsed:
                try:
                    cookie["sameSite"] = "Strict"
                    await context.add_cookies([cookie])
                except Exception as e:
                    log_message(f"Ошибка добавления cookie: {str(e)}", "ERROR")
            
            page = await context.new_page()
            await page.evaluate("navigator.__proto__.webdriver = undefined;")
            
            # Показываем уведомление об успешном запуске
            if notification_system:
                notification_system.show_notification(
                    "Браузер запущен", 
                    f"Профиль '{profile}' успешно загружен", 
                    "success"
                )
            
            # Открываем вкладку whoer.net автоматически при старте профиля (после загрузки cookies)
            try:
                await page.goto("https://whoer.net/", timeout=30000, wait_until="domcontentloaded")
                log_message("Открыта вкладка whoer.net")
            except Exception as e:
                log_message(f"Не удалось открыть whoer.net: {e}", "ERROR")
                # В случае ошибки переходим на пустую страницу
                try:
                    await page.goto("about:blank", timeout=60000)
                except Exception as e2:
                    log_message(f"Не удалось открыть about:blank: {e2}", "ERROR")
            
            try:
                await page.wait_for_event("close", timeout=0)
            finally:
                if proxy_task:
                    proxy_task.cancel()
                await save_cookies(context, profile)
                
                # Очищаем временную директорию
                if temp_user_data:
                    try:
                        shutil.rmtree(temp_user_data, ignore_errors=True)
                        log_message(f"Временная директория удалена: {temp_user_data}")
                    except Exception as e:
                        log_message(f"Не удалось удалить временную директорию: {e}", "ERROR")
                
                if notification_system:
                    notification_system.show_notification(
                        "Браузер закрыт", 
                        f"Профиль '{profile}' завершен, cookies сохранены", 
                        "info"
                    )
                    
    except Exception as e:
        log_message(f"Критическая ошибка браузера: {str(e)}", "ERROR")
        if notification_system:
            notification_system.show_notification(
                "Критическая ошибка", 
                f"Не удалось запустить браузер: {str(e)}", 
                "error"
            )

# Улучшенная функция проверки прокси
async def check_proxy_async(proxy: str) -> dict:
    """Асинхронная проверка прокси: корректная поддержка HTTP/HTTPS и SOCKS5 (без использования кэша)"""
    log_message(f"Проверяем прокси: {proxy}")
    
    # Всегда выполняем живую проверку; кэш не используем для чтения
    
    # Парсинг прокси
    try:
        if "://" in proxy:
            protocol = proxy.split("://")[0]
            rest = proxy.split("://")[1]
        else:
            protocol = "http"
            rest = proxy
            
        if "@" in rest:
            auth_part, server_part = rest.split("@", 1)
            if ":" in auth_part:
                username, password = auth_part.split(":", 1)
            else:
                username, password = auth_part, ""
        else:
            username, password = "", ""
            server_part = rest
            
        if ":" in server_part:
            ip, port = server_part.split(":", 1)
            port = int(port)
        else:
            ip = server_part
            port = 8080
            
    except Exception as e:
        log_message(f"Ошибка парсинга прокси {proxy}: {str(e)}", "ERROR")
        result = {"status": "error", "proxy_str": proxy, "error": f"Ошибка парсинга: {str(e)}"}
        _proxy_check_cache[proxy] = result
        return result
    
    # Формируем строку прокси
    if username and password:
        proxy_str = f"{protocol}://{username}:{password}@{ip}:{port}"
    else:
        proxy_str = f"{protocol}://{ip}:{port}"
        
    # Корректная поддержка SOCKS5 для requests (требует PySocks)
    proxy_dict = {}
    if protocol.startswith("socks"):
        # Use socks5h to resolve DNS via proxy; normalize socks5_http -> socks5h
        normalized = proxy_str.replace("socks5_http://", "socks5h://").replace("socks5://", "socks5h://")
        proxy_dict = {
            "http": normalized,
            "https": normalized
        }
    else:
        proxy_dict = {
            "http": proxy_str,
            "https": proxy_str
        }
    
    # Список сервисов для проверки: сначала HTTP, затем HTTPS (уменьшаем блокировки)
    check_services = [
        ("http://api.ipify.org?format=json", "ip"),
        ("https://api.ipify.org?format=json", "ip"),
        ("http://httpbin.org/ip", "origin"),
        ("https://httpbin.org/ip", "origin"),
        ("http://checkip.amazonaws.com", None),
        ("https://checkip.amazonaws.com", None),
    ]
    
    # Проверяем прокси с повторными попытками
    for attempt in range(3):
        try:
            for service_url, ip_field in check_services:
                try:
                    start_time = time.time()
                    response = requests.get(
                        service_url, 
                        proxies=proxy_dict, 
                        timeout=8,
                        headers={'User-Agent': 'Antic Browser v1.0.0'}
                    )
                    latency = time.time() - start_time
                    
                    if response.status_code == 200:
                        # Парсим IP в зависимости от сервиса
                        try:
                            if ip_field:
                                data = response.json()
                                returned_ip = data.get(ip_field, ip)
                            else:
                                returned_ip = response.text.strip()
                        except:
                            returned_ip = ip
                        
                        # Получаем геоданные - используем локальную базу GeoIP
                        country = "UNK"
                        city = "UNK"
                        
                        try:
                            with geoip2.database.Reader(COUNTRY_DATABASE_PATH) as reader:
                                geo_response = reader.country(returned_ip)
                                country = geo_response.country.iso_code or "UNK"
                            with geoip2.database.Reader(CITY_DATABASE_PATH) as reader:
                                geo_response = reader.city(returned_ip)
                                city = geo_response.city.name or "UNK"
                        except Exception as _:
                            pass
                        
                        result = {
                            "status": "ok", 
                            "country": country, 
                            "city": city, 
                            "type": protocol, 
                            "proxy_str": proxy_str, 
                            "latency": latency,
                            "ip": returned_ip
                        }
                        
                        _proxy_check_cache[proxy] = result
                        
                        # Сохраняем кэш
                        try:
                            with open(PROXY_CACHE_PATH, "w", encoding="utf-8") as f:
                                json.dump(_proxy_check_cache, f, indent=4)
                        except Exception as e:
                            log_message(f"Ошибка сохранения кэша: {str(e)}", "ERROR")
                            
                        log_message(f"Прокси работает: {country}, {city}, IP: {returned_ip}, время: {latency:.2f}с")
                        return result
                        
                except (requests.exceptions.RequestException, requests.exceptions.Timeout) as err:
                    log_message(f"Ошибка запроса через прокси: {err}", "ERROR")
                    # Пробуем следующий сервис
                    continue
            
            # Если все сервисы не сработали, небольшая пауза
            if attempt < 2:
                await asyncio.sleep(1.5)
                
        except Exception as e:
            log_message(f"Ошибка проверки на попытке {attempt + 1}: {str(e)}", "ERROR")
            if attempt < 2:
                await asyncio.sleep(1.5)
    
    # Если дошли сюда, значит все попытки неудачны
    result = {"status": "error", "proxy_str": proxy_str, "error": "Прокси не отвечает или блокирует подключение"}
    _proxy_check_cache[proxy] = result
    
    try:
        with open(PROXY_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(_proxy_check_cache, f, indent=4)
    except:
        pass
    
    log_message(f"Прокси не работает: {proxy_str}", "ERROR")
    return result

def show_snackbar(page: ft.Page, message: str, color: ft.Colors = ft.Colors.BLUE):
    """Улучшенная функция показа snackbar"""
    try:
        log_message(f"Snackbar: {message}")
        page.snack_bar = ft.SnackBar(
            content=ft.Text(message, color=ft.Colors.WHITE, font_family="SF Pro"),
            bgcolor=color,
            duration=4000
        )
        page.snack_bar.open = True
        page.update()
        
        # Также показываем через систему уведомлений
        if notification_system:
            notification_type = "success" if color == ft.Colors.GREEN else "error" if color == ft.Colors.RED else "warning" if color == ft.Colors.ORANGE else "info"
            notification_system.show_notification("Уведомление", message, notification_type)
            
    except Exception as e:
        log_message(f"Ошибка показа snackbar: {str(e)}", "ERROR")

def get_proxy():
    """Получение списка прокси из файла"""
    proxies = []
    if os.path.isfile(PROXIES_FILE):
        try:
            with open(PROXIES_FILE, "r", encoding="utf-8") as f:
                proxies = json.load(f)
            log_message(f"Загружено {len(proxies)} прокси")
        except Exception as e:
            log_message(f"Ошибка загрузки прокси: {str(e)}", "ERROR")
            proxies = []
    else:
        log_message("Файл прокси не найден")
    return proxies

def save_proxy_to_file(proxy_str: str):
    """Сохранение прокси в файл"""
    try:
        proxies = get_proxy()
        if proxy_str not in proxies:
            proxies.append(proxy_str)
            with open(PROXIES_FILE, "w", encoding="utf-8") as f:
                json.dump(proxies, f, indent=4)
            log_message(f"Прокси добавлен: {proxy_str}")
            return True
        return False
    except Exception as e:
        log_message(f"Ошибка сохранения прокси: {str(e)}", "ERROR")
        return False

def remove_proxy_from_file(proxy_str: str):
    """Удаление прокси из файла"""
    try:
        proxies = get_proxy()
        if proxy_str in proxies:
            proxies.remove(proxy_str)
            with open(PROXIES_FILE, "w", encoding="utf-8") as f:
                json.dump(proxies, f, indent=4)
            log_message(f"Прокси удален: {proxy_str}")
            return True
        return False
    except Exception as e:
        log_message(f"Ошибка удаления прокси: {str(e)}", "ERROR")
        return False

# Улучшенная функция обновления страницы
def refresh_proxies_page():
    """Обновление страницы прокси с защитой от ошибок"""
    global main_page_ref, current_page
    if main_page_ref and current_page == "proxies":
        log_message("Обновляем страницу прокси")
        try:
            # Используем более безопасный способ обновления
            def update_page():
                try:
                    main_page_ref.controls.clear()
                    main_page_ref.controls = get_proxies_content(main_page_ref)
                    main_page_ref.update()
                    log_message("Страница прокси обновлена")
                except Exception as e:
                    log_message(f"Ошибка обновления страницы: {str(e)}", "ERROR")
            
            # Выполняем обновление в отдельном потоке для избежания блокировки UI
            threading.Thread(target=update_page, daemon=True).start()
            
        except Exception as e:
            log_message(f"Ошибка запуска обновления: {str(e)}", "ERROR")

def parse_quick_input(text: str, page: ft.Page):
    """Парсинг быстрого ввода прокси"""
    text = text.strip()
    if not text:
        return
    
    proxy_fields = getattr(page, 'proxy_fields', None)
    if not proxy_fields:
        log_message("Поля прокси не найдены в page.proxy_fields", "ERROR")
        return
        
    log_message(f"Парсим быстрый ввод: {text}")
    
    # IP:port:login:password
    match = re.match(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d+):(.+):(.+)", text)
    if match:
        proxy_fields['ip'].value = match.group(1)
        proxy_fields['port'].value = match.group(2)
        proxy_fields['username'].value = match.group(3)
        proxy_fields['password'].value = match.group(4)
        proxy_fields['protocol'].value = "http"
        proxy_fields['quick_input'].value = ""
        page.update()
        log_message("Парсинг IP:port:login:password успешен")
        return
    
    # protocol://login:password@IP:port
    match = re.match(r"(http|socks5)://(.+):(.+)@(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d+)", text)
    if match:
        proxy_fields['protocol'].value = match.group(1)
        proxy_fields['username'].value = match.group(2)
        proxy_fields['password'].value = match.group(3)
        proxy_fields['ip'].value = match.group(4)
        proxy_fields['port'].value = match.group(5)
        proxy_fields['quick_input'].value = ""
        page.update()
        log_message("Парсинг protocol://login:password@IP:port успешен")
        return
    
    # IP:port
    match = re.match(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d+)", text)
    if match:
        proxy_fields['ip'].value = match.group(1)
        proxy_fields['port'].value = match.group(2)
        proxy_fields['username'].value = ""
        proxy_fields['password'].value = ""
        proxy_fields['protocol'].value = "http"
        proxy_fields['quick_input'].value = ""
        page.update()
        log_message("Парсинг IP:port успешен")
        return
    
    log_message("Неверный формат строки", "ERROR")
    show_snackbar(page, "Неверный формат строки! Используйте IP:port:login:password, protocol://login:password@IP:port или IP:port", ft.Colors.RED)

# Улучшенная функция сохранения прокси
def save_proxy(page: ft.Page, add_button: ft.ElevatedButton):
    """Сохранение прокси с улучшенной обработкой ошибок"""
    log_message("Сохраняем прокси...")
    
    proxy_fields = getattr(page, 'proxy_fields', None)
    if not proxy_fields:
        log_message("Поля прокси не найдены!", "ERROR")
        show_snackbar(page, "Ошибка: поля прокси не инициализированы!", ft.Colors.RED)
        return
    
    # Показываем индикатор загрузки
    original_content = add_button.content
    add_button.content = ft.ProgressRing(width=16, height=16, color=ft.Colors.WHITE)
    page.update()
    
    def save_async():
        try:
            ip = proxy_fields['ip'].value.strip() if proxy_fields['ip'].value else ""
            port = proxy_fields['port'].value.strip() if proxy_fields['port'].value else ""
            protocol = proxy_fields['protocol'].value
            username = proxy_fields['username'].value.strip() if proxy_fields['username'].value else ""
            password = proxy_fields['password'].value.strip() if proxy_fields['password'].value else ""
            
            log_message(f"Данные прокси: {protocol}://{ip}:{port} (логин: {username})")
            
            if not ip or not port or not protocol:
                log_message("Не все обязательные поля заполнены", "ERROR")
                show_snackbar(page, "Заполните IP, порт и протокол!", ft.Colors.RED)
                return
                
            try:
                port = int(port)
            except ValueError:
                log_message("Порт не является числом", "ERROR")
                show_snackbar(page, "Порт должен быть числом!", ft.Colors.RED)
                return
            
            # Формируем строку прокси
            if username and password:
                proxy_str = f"{protocol}://{username}:{password}@{ip}:{port}"
            else:
                proxy_str = f"{protocol}://{ip}:{port}"
            
            log_message(f"Проверяем прокси: {proxy_str}")
            
            # Асинхронная проверка прокси
            async def check_and_save():
                result = await check_proxy_async(proxy_str)
                
                if result["status"] == "ok":
                    # Сохраняем прокси
                    if save_proxy_to_file(result["proxy_str"]):
                        # Очищаем поля
                        proxy_fields['ip'].value = ""
                        proxy_fields['port'].value = ""
                        proxy_fields['username'].value = ""
                        proxy_fields['password'].value = ""
                        proxy_fields['protocol'].value = "http"
                        proxy_fields['quick_input'].value = ""
                        
                        latency = result.get('latency', 'N/A')
                        latency_str = f"{latency:.2f}" if isinstance(latency, (int, float)) else latency
                        log_message(f"Прокси добавлен: {result['country']}, {result['city']}, {latency_str}с")
                        show_snackbar(page, f"Прокси успешно добавлен! Страна: {result['country']}, Город: {result['city']}, Задержка: {latency_str}с", ft.Colors.GREEN)
                        
                        # Обновляем страницу
                        refresh_proxies_page()
                    else:
                        log_message("Прокси уже существует")
                        show_snackbar(page, "Прокси уже существует!", ft.Colors.ORANGE)
                else:
                    error_msg = result.get('error', 'Неизвестная ошибка')
                    log_message(f"Прокси не работает: {error_msg}", "ERROR")
                    show_snackbar(page, f"Прокси не добавлен: {error_msg}", ft.Colors.RED)
            
            # Запускаем асинхронную проверку
            asyncio.run(check_and_save())
            
        except Exception as e:
            log_message(f"Ошибка сохранения прокси: {str(e)}", "ERROR")
            show_snackbar(page, f"Ошибка: {str(e)}", ft.Colors.RED)
        finally:
            # Восстанавливаем кнопку
            add_button.content = original_content
            page.update()
    
    # Запускаем в отдельном потоке
    threading.Thread(target=save_async, daemon=True).start()

# Улучшенная функция удаления прокси
def delete_proxy(proxy: str, page: ft.Page):
    """Удаление прокси с улучшенной обработкой"""
    log_message(f"Удаляем прокси: {proxy}")
    
    try:
        if remove_proxy_from_file(proxy):
            log_message("Прокси удален")
            show_snackbar(page, "Прокси успешно удалён!", ft.Colors.GREEN)
            refresh_proxies_page()
        else:
            log_message("Прокси не найден", "ERROR")
            show_snackbar(page, "Прокси не найден!", ft.Colors.RED)
    except Exception as e:
        log_message(f"Ошибка удаления прокси: {str(e)}", "ERROR")
        show_snackbar(page, f"Ошибка удаления: {str(e)}", ft.Colors.RED)

# Улучшенная функция проверки прокси с кнопки
def check_proxy_button(proxy: str, page: ft.Page, button: ft.ElevatedButton):
    """Проверка прокси с кнопки с улучшенной обработкой"""
    log_message(f"Проверяем прокси с кнопки: {proxy}")
    
    # Показываем индикатор загрузки
    original_content = button.content
    button.content = ft.ProgressRing(width=16, height=16, color=ft.Colors.WHITE)
    page.update()
    
    def check_async():
        try:
            # Асинхронная проверка
            async def check_and_update():
                result = await check_proxy_async(proxy)
                
                if result["status"] == "ok":
                    latency = result.get('latency', 'N/A')
                    latency_str = f"{latency:.2f}" if isinstance(latency, (int, float)) else latency
                    show_snackbar(page, f"Прокси работает! Страна: {result['country']}, Город: {result['city']}, Задержка: {latency_str}с", ft.Colors.GREEN)
                else:
                    error_msg = result.get('error', 'Неизвестная ошибка')
                    show_snackbar(page, f"Прокси не работает: {error_msg}", ft.Colors.RED)
                
                # Обновляем страницу
                refresh_proxies_page()
            
            # Запускаем проверку
            asyncio.run(check_and_update())
            
        except Exception as e:
            log_message(f"Ошибка проверки прокси: {str(e)}", "ERROR")
            show_snackbar(page, f"Ошибка проверки: {str(e)}", ft.Colors.RED)
        finally:
            # Восстанавливаем кнопку
            button.content = original_content
            page.update()
    
    # Запускаем в отдельном потоке
    threading.Thread(target=check_async, daemon=True).start()

def open_api_help_url(e):
    """Открытие ссылки на получение API ключа с исправленным URL"""
    log_message("Открываем ссылку на API ключ")
    try:
        import webbrowser
        webbrowser.open("https://sx.org/?c=ANTIC3")  # Исправленная ссылка
    except Exception as error:
        log_message(f"Ошибка открытия ссылки: {str(error)}", "ERROR")

def open_psb_url(e):
    """Открытие ссылки на PSB proxy (новая кнопка)"""
    log_message("Открываем ссылку на PSB proxy")
    try:
        import webbrowser
        webbrowser.open("http://psbproxy.io/?utm_source=partner&utm_medium=soft&utm_term=antic&utm_campaign=openincognito")
    except Exception as error:
        log_message(f"Ошибка открытия ссылки PSB: {str(error)}", "ERROR")

def open_sx_org_page(page: ft.Page):
    """Открытие страницы SX.ORG с улучшенным дизайном и обработкой ошибок"""
    log_message("Открываем страницу SX.ORG")
    global current_page
    current_page = "sx_org"
    
    # Поля для авторизации
    api_key_field = ft.TextField(
        label="API Ключ SX.ORG",
        hint_text="Введите ваш API ключ",
        width=400,
        border_radius=8,
        content_padding=15,
        text_style=ft.TextStyle(size=14),
        label_style=ft.TextStyle(size=12),
        value=saved_api_keys.get("sx_org", "")  # Загружаем сохраненный ключ
    )
    
    balance_text = ft.Text("", size=16, color=ft.Colors.GREEN, weight=ft.FontWeight.BOLD)
    
    # Контейнер для кнопок функций (скрыт по умолчанию)
    functions_container = ft.Container(
        content=ft.Column([]),
        visible=False
    )
    
    # Контейнер для интерфейсов создания/импорта (скрыт по умолчанию)
    interface_container = ft.Container(
        content=ft.Column([]),
        visible=False
    )
    
    def validate_api_key(e):
        """Валидация API ключа с улучшенной обработкой"""
        api_key = api_key_field.value.strip()
        if not api_key:
            show_snackbar(page, "Введите API ключ", ft.Colors.RED)
            return
        
        original_text = e.control.text
        e.control.disabled = True
        e.control.text = "Проверяем..."
        page.update()
        
        def validate_async():
            try:
                success, message = sx_api.validate_key(api_key)
                if success:
                    # Сохраняем API ключ
                    save_api_key("sx_org", api_key)
                    
                    balance_text.value = f"💰 {message}"
                    
                    # Показываем кнопки функций
                    functions_container.content = ft.Row([
                        ft.ElevatedButton(
                            "Создать прокси",
                            bgcolor=ft.Colors.GREEN,
                            color=ft.Colors.WHITE,
                            style=ft.ButtonStyle(
                                padding=ft.padding.all(15),
                                text_style=ft.TextStyle(size=14, weight=ft.FontWeight.W_500),
                                shape=ft.RoundedRectangleBorder(radius=8)
                            ),
                            on_click=lambda e: show_create_interface()
                        ),
                        ft.ElevatedButton(
                            "Импортировать прокси",
                            bgcolor=ft.Colors.BLUE,
                            color=ft.Colors.WHITE,
                            style=ft.ButtonStyle(
                                padding=ft.padding.all(15),
                                text_style=ft.TextStyle(size=14, weight=ft.FontWeight.W_500),
                                shape=ft.RoundedRectangleBorder(radius=8)
                            ),
                            on_click=lambda e: show_import_interface()
                        )
                    ], spacing=20, alignment=ft.MainAxisAlignment.CENTER)
                    functions_container.visible = True
                    
                    page.update()
                    show_snackbar(page, "API ключ успешно проверен!", ft.Colors.GREEN)
                else:
                    show_snackbar(page, f"Ошибка: {message}", ft.Colors.RED)
            except Exception as ex:
                log_message(f"Ошибка валидации API: {str(ex)}", "ERROR")
                show_snackbar(page, f"Ошибка валидации: {str(ex)}", ft.Colors.RED)
            finally:
                e.control.disabled = False
                e.control.text = original_text
                page.update()
        
        # Запускаем в отдельном потоке
        threading.Thread(target=validate_async, daemon=True).start()
    
    def show_create_interface():
        """Показ интерфейса создания прокси с улучшенной обработкой"""
        log_message("Показываем интерфейс создания прокси")
        
        # Поля для создания прокси
        country_dropdown = ft.Dropdown(
            label="Страна",
            width=250,
            border_radius=8,
            content_padding=10,
            options=[ft.dropdown.Option(c['name']) for c in sx_api.countries]
        )
        
        state_dropdown = ft.Dropdown(
            label="Штат/Область",
            width=250,
            border_radius=8,
            content_padding=10,
            options=[]
        )
        
        city_dropdown = ft.Dropdown(
            label="Город",
            width=250,
            border_radius=8,
            content_padding=10,
            options=[]
        )
        
        connection_type = ft.RadioGroup(
            content=ft.Column([
                ft.Radio(value="keep-connection", label="Без ротации", label_style=ft.TextStyle(size=14)),
                ft.Radio(value="rotate-connection", label="С ротацией", label_style=ft.TextStyle(size=14))
            ], spacing=8),
            value="keep-connection"
        )
        
        residential_check = ft.Checkbox(label="Residential", value=True, label_style=ft.TextStyle(size=14))
        mobile_check = ft.Checkbox(label="Mobile", value=False, label_style=ft.TextStyle(size=14))
        corporate_check = ft.Checkbox(label="Corporate", value=False, label_style=ft.TextStyle(size=14))
        
        def on_country_change(e):
            """Обработка изменения страны"""
            if e.control.value:
                try:
                    country = next((c for c in sx_api.countries if c['name'] == e.control.value), None)
                    if country:
                        success, states = sx_api.get_states(country['id'])
                        if success:
                            state_dropdown.options = [ft.dropdown.Option(s['name']) for s in states]
                            state_dropdown.value = None
                            city_dropdown.options = []
                            city_dropdown.value = None
                            page.update()
                except Exception as ex:
                    log_message(f"Ошибка получения штатов: {str(ex)}", "ERROR")
                    show_snackbar(page, f"Ошибка получения штатов: {str(ex)}", ft.Colors.RED)
        
        def on_state_change(e):
            """Обработка изменения штата"""
            if e.control.value:
                try:
                    state = next((s for s in sx_api.states if s['name'] == e.control.value), None)
                    if state:
                        success, cities = sx_api.get_cities(state['id'], state['dir_country_id'])
                        if success:
                            city_dropdown.options = [ft.dropdown.Option(c['name']) for c in cities]
                            city_dropdown.value = None
                            page.update()
                except Exception as ex:
                    log_message(f"Ошибка получения городов: {str(ex)}", "ERROR")
                    show_snackbar(page, f"Ошибка получения городов: {str(ex)}", ft.Colors.RED)
        
        country_dropdown.on_change = on_country_change
        state_dropdown.on_change = on_state_change
        
        def create_proxy_action(e):
            """Создание прокси с улучшенной обработкой"""
            original_text = e.control.text
            e.control.disabled = True
            e.control.text = "Создаем..."
            page.update()
            
            def create_async():
                try:
                    country_name = country_dropdown.value
                    if not country_name:
                        show_snackbar(page, "Выберите страну", ft.Colors.RED)
                        return
                        
                    country = next((c for c in sx_api.countries if c['name'] == country_name), None)
                    state_name = state_dropdown.value
                    city_name = city_dropdown.value
                    
                    proxy_types = []
                    if residential_check.value:
                        proxy_types.append("residential")
                    if mobile_check.value:
                        proxy_types.append("mobile")
                    if corporate_check.value:
                        proxy_types.append("corporate")
                    
                    if not proxy_types:
                        show_snackbar(page, "Выберите хотя бы один тип прокси", ft.Colors.RED)
                        return
                    
                    proxy_type_str = "Residential" if "residential" in proxy_types else "Mobile" if "mobile" in proxy_types else "Corporate"
                    proxy_name = f"{proxy_type_str} - {country_name} - {city_name or 'N/A'}"
                    
                    success, result = sx_api.create_proxy(
                        country['code'], state_name, city_name, 
                        connection_type.value, proxy_types, proxy_name
                    )
                    
                    if success:
                        show_snackbar(page, f"Прокси созданы! {len(result)} шт.", ft.Colors.GREEN)
                        # Добавляем созданные прокси в список
                        for proxy_str in result:
                            save_proxy_to_file(proxy_str)
                        
                        # Обновляем страницу прокси
                        refresh_proxies_page()
                    else:
                        show_snackbar(page, f"Ошибка: {result}", ft.Colors.RED)
                        
                except Exception as ex:
                    log_message(f"Ошибка создания прокси: {str(ex)}", "ERROR")
                    show_snackbar(page, f"Ошибка: {str(ex)}", ft.Colors.RED)
                finally:
                    e.control.disabled = False
                    e.control.text = original_text
                    page.update()
            
            # Запускаем в отдельном потоке
            threading.Thread(target=create_async, daemon=True).start()
        
        # Интерфейс создания прокси
        interface_container.content = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.IconButton(
                        ft.Icons.ARROW_BACK, 
                        icon_color=ft.Colors.BLUE,
                        icon_size=24,
                        on_click=lambda e: hide_interface()
                    ),
                    ft.Text("Создание нового прокси", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.BLACK87)
                ], alignment=ft.MainAxisAlignment.START),
                
                ft.Container(height=20),
                
                ft.Row([country_dropdown, state_dropdown], spacing=20, alignment=ft.MainAxisAlignment.CENTER),
                ft.Container(city_dropdown, alignment=ft.alignment.center),
                
                ft.Container(height=20),
                
                ft.Text("Тип соединения:", size=16, weight=ft.FontWeight.W_500, color=ft.Colors.BLACK87),
                connection_type,
                
                ft.Container(height=15),
                
                ft.Text("Типы прокси:", size=16, weight=ft.FontWeight.W_500, color=ft.Colors.BLACK87),
                ft.Row([residential_check, mobile_check, corporate_check], spacing=20, alignment=ft.MainAxisAlignment.CENTER),
                
                ft.Container(height=30),
                
                ft.Container(
                    content=ft.ElevatedButton(
                        "Создать прокси",
                        bgcolor=ft.Colors.GREEN,
                        color=ft.Colors.WHITE,
                        style=ft.ButtonStyle(
                            padding=ft.padding.all(15),
                            text_style=ft.TextStyle(size=16, weight=ft.FontWeight.W_500),
                            shape=ft.RoundedRectangleBorder(radius=10)
                        ),
                        on_click=create_proxy_action,
                        width=200
                    ),
                    alignment=ft.alignment.center
                )
            ], spacing=15, scroll=ft.ScrollMode.AUTO),
            padding=20,
            bgcolor=ft.Colors.WHITE,
            border_radius=15,
            shadow=ft.BoxShadow(blur_radius=10, color=ft.Colors.BLACK12)
        )
        interface_container.visible = True
        functions_container.visible = False
        page.update()
    
    def show_import_interface():
        """Показ интерфейса импорта прокси с улучшенной обработкой"""
        log_message("Показываем интерфейс импорта прокси")
        
        # Список прокси для импорта
        import_list = ft.Column(
            controls=[],
            height=350,
            spacing=10,
            scroll=ft.ScrollMode.AUTO
        )
        
        selected_proxies = {}
        
        def load_ports():
            """Загрузка портов с улучшенной обработкой"""
            try:
                success, ports = sx_api.get_ports()
                if success:
                    import_list.controls.clear()
                    selected_proxies.clear()
                    
                    if not ports:
                        import_list.controls.append(
                            ft.Container(
                                content=ft.Text(
                                    "Нет доступных прокси. Создайте новые прокси.",
                                    color=ft.Colors.GREY_600,
                                    size=14,
                                    text_align=ft.TextAlign.CENTER
                                ),
                                alignment=ft.alignment.center,
                                padding=20
                            )
                        )
                    else:
                        for p in ports:
                            try:
                                proxy_id = p.get('id', None)
                                server, port = p.get('proxy', 'N/A').split(':', 1) if ':' in p.get('proxy', 'N/A') else ('N/A', 'N/A')
                                login = p.get('login', 'N/A').split('@')[0] if '@' in p.get('login', 'N/A') else p.get('login', 'N/A')
                                password = p.get('password', 'N/A')
                                name = p.get('name', 'Unnamed')
                                
                                proxy_str = f"http://{login}:{password}@{server}:{port}"
                                
                                def make_toggle_handler(pid, pstr):
                                    def handler(e):
                                        toggle_proxy_selection(pid, pstr, e.control.value)
                                    return handler
                                
                                checkbox = ft.Checkbox(
                                    label=name,
                                    value=False,
                                    on_change=make_toggle_handler(proxy_id, proxy_str),
                                    label_style=ft.TextStyle(size=13)
                                )
                                
                                row = ft.Container(
                                    content=ft.Row([
                                        ft.Container(checkbox, expand=True)
                                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                                    padding=10,
                                    border_radius=8,
                                    bgcolor=ft.Colors.GREY_50,
                                    border=ft.border.all(1, ft.Colors.GREY_200)
                                )
                                
                                import_list.controls.append(row)
                            except Exception as e:
                                log_message(f"Ошибка обработки прокси {p}: {str(e)}", "ERROR")
                                continue
                    
                    page.update()
                else:
                    show_snackbar(page, f"Ошибка загрузки: {ports}", ft.Colors.RED)
            except Exception as e:
                log_message(f"Ошибка загрузки портов: {str(e)}", "ERROR")
                show_snackbar(page, f"Ошибка загрузки: {str(e)}", ft.Colors.RED)
        
        def toggle_proxy_selection(proxy_id, proxy_str, selected):
            """Переключение выбора прокси"""
            if selected:
                selected_proxies[proxy_id] = proxy_str
            else:
                selected_proxies.pop(proxy_id, None)
        
        def import_selected_proxies(e):
            """Импорт выбранных прокси"""
            if not selected_proxies:
                show_snackbar(page, "Выберите прокси для импорта", ft.Colors.RED)
                return
            
            original_text = e.control.text
            e.control.disabled = True
            e.control.text = f"Импортируем {len(selected_proxies)} прокси..."
            page.update()
            
            def import_async():
                try:
                    imported_count = 0
                    
                    for proxy_str in selected_proxies.values():
                        if save_proxy_to_file(proxy_str):
                            imported_count += 1
                    
                    if imported_count > 0:
                        show_snackbar(page, f"Импортировано {imported_count} прокси!", ft.Colors.GREEN)
                        refresh_proxies_page()
                    else:
                        show_snackbar(page, "Все выбранные прокси уже существуют", ft.Colors.ORANGE)
                except Exception as ex:
                    log_message(f"Ошибка импорта прокси: {str(ex)}", "ERROR")
                    show_snackbar(page, f"Ошибка импорта: {str(ex)}", ft.Colors.RED)
                finally:
                    e.control.disabled = False
                    e.control.text = original_text
                    page.update()
            
            # Запускаем в отдельном потоке
            threading.Thread(target=import_async, daemon=True).start()
        
        # Интерфейс импорта прокси
        interface_container.content = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.IconButton(
                        ft.Icons.ARROW_BACK, 
                        icon_color=ft.Colors.BLUE,
                        icon_size=24,
                        on_click=lambda e: hide_interface()
                    ),
                    ft.Text("Импорт существующих прокси", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.BLACK87)
                ], alignment=ft.MainAxisAlignment.START),
                
                ft.Container(height=15),
                
                ft.Row([
                    ft.ElevatedButton(
                        "Обновить список",
                        bgcolor=ft.Colors.BLUE,
                        color=ft.Colors.WHITE,
                        style=ft.ButtonStyle(
                            padding=ft.padding.all(12),
                            text_style=ft.TextStyle(size=14),
                            shape=ft.RoundedRectangleBorder(radius=8)
                        ),
                        on_click=lambda e: load_ports()
                    ),
                    ft.ElevatedButton(
                        "Импортировать выбранные",
                        bgcolor=ft.Colors.GREEN,
                        color=ft.Colors.WHITE,
                        style=ft.ButtonStyle(
                            padding=ft.padding.all(12),
                            text_style=ft.TextStyle(size=14),
                            shape=ft.RoundedRectangleBorder(radius=8)
                        ),
                        on_click=import_selected_proxies
                    )
                ], spacing=15, alignment=ft.MainAxisAlignment.CENTER),
                
                ft.Container(height=15),
                
                ft.Container(
                    content=import_list,
                    border=ft.border.all(1, ft.Colors.GREY_300),
                    border_radius=10,
                    padding=10,
                    bgcolor=ft.Colors.WHITE
                )
            ], spacing=10, scroll=ft.ScrollMode.AUTO),
            padding=20,
            bgcolor=ft.Colors.WHITE,
            border_radius=15,
            shadow=ft.BoxShadow(blur_radius=10, color=ft.Colors.BLACK12)
        )
        interface_container.visible = True
        functions_container.visible = False
        page.update()
    
    def hide_interface():
        """Скрытие интерфейса"""
        interface_container.visible = False
        functions_container.visible = True
        page.update()
    
    def go_back_to_main(e):
        """Возврат к главной странице"""
        global current_page
        current_page = "proxies"
        page.controls.clear()
        page.controls = get_proxies_content(page)
        page.update()
    
    # Структура страницы SX.ORG
    main_content = ft.Container(
        content=ft.Column([
            # Заголовок с кнопкой назад
            ft.Container(
                content=ft.Row([
                    ft.IconButton(
                        ft.Icons.ARROW_BACK,
                        icon_color=ft.Colors.BLUE,
                        icon_size=24,
                        on_click=go_back_to_main,
                        tooltip="Назад"
                    ),
                    ft.Text("Proxy SX.ORG", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.BLACK87)
                ], alignment=ft.MainAxisAlignment.START),
                margin=ft.margin.only(bottom=20)
            ),
            
            # ПРОМО-БАННЕР с исправленным промокодом
            ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.CARD_GIFTCARD, color=ft.Colors.ORANGE_600, size=20),
                    ft.Text("🎁 Промокод ANTIC3 = 3GB бесплатно", 
                           size=16, 
                           weight=ft.FontWeight.W_500, 
                           color=ft.Colors.ORANGE_700)
                ], spacing=10, alignment=ft.MainAxisAlignment.CENTER),
                padding=15,
                bgcolor=ft.Colors.ORANGE_50,
                border_radius=10,
                border=ft.border.all(2, ft.Colors.ORANGE_200),
                margin=ft.margin.only(bottom=30)
            ),
            
            # Блок авторизации
            ft.Container(
                content=ft.Column([
                    ft.Text("Авторизация", 
                           size=18, 
                           weight=ft.FontWeight.BOLD, 
                           color=ft.Colors.BLACK87,
                           text_align=ft.TextAlign.CENTER),
                    
                    ft.Container(height=20),
                    
                    # Поле API ключа и кнопки
                    ft.Row([
                        api_key_field,
                        ft.ElevatedButton(
                            "Войти",
                            bgcolor=ft.Colors.BLUE,
                            color=ft.Colors.WHITE,
                            style=ft.ButtonStyle(
                                padding=ft.padding.all(15),
                                text_style=ft.TextStyle(size=14, weight=ft.FontWeight.W_500),
                                shape=ft.RoundedRectangleBorder(radius=8)
                            ),
                            on_click=validate_api_key,
                            height=50
                        ),
                        ft.ElevatedButton(
                            "Получить API ключ",
                            bgcolor=ft.Colors.PURPLE,
                            color=ft.Colors.WHITE,
                            style=ft.ButtonStyle(
                                padding=ft.padding.all(15),
                                text_style=ft.TextStyle(size=14, weight=ft.FontWeight.W_500),
                                shape=ft.RoundedRectangleBorder(radius=8)
                            ),
                            on_click=open_api_help_url,
                            height=50
                        )
                    ], spacing=15, alignment=ft.MainAxisAlignment.CENTER, wrap=True),
                    
                    ft.Container(height=15),
                    
                    # Баланс
                    ft.Container(
                        content=balance_text,
                        alignment=ft.alignment.center
                    ),
                    
                    ft.Container(height=20),
                    
                    # Кнопки функций (скрыты по умолчанию)
                    functions_container
                    
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0),
                padding=30,
                bgcolor=ft.Colors.WHITE,
                border_radius=15,
                shadow=ft.BoxShadow(blur_radius=10, color=ft.Colors.BLACK12),
                margin=ft.margin.only(bottom=20)
            ),
            
            # Контейнер для интерфейсов
            interface_container
            
        ], spacing=0, scroll=ft.ScrollMode.AUTO, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        padding=20,
        gradient=ft.LinearGradient(
            begin=ft.alignment.top_center,
            end=ft.alignment.bottom_center,
            colors=[ft.Colors.BLUE_50, ft.Colors.WHITE]
        ),
        expand=True
    )
    
    page.controls.clear()
    page.controls = [main_content]
    page.update()

def open_cyberyozh_page(page: ft.Page):
    """Открытие страницы CyberYozh с интеграцией API"""
    log_message("Открываем страницу CyberYozh")
    global current_page
    current_page = "cyberyozh"
    
    # Поля для авторизации
    api_key_field = ft.TextField(
        label="API Ключ CyberYozh",
        hint_text="Введите ваш API ключ",
        width=400,
        border_radius=8,
        content_padding=15,
        text_style=ft.TextStyle(size=14),
        label_style=ft.TextStyle(size=12),
        value=saved_api_keys.get("cyberyozh", "")  # Загружаем сохраненный ключ
    )
    
    balance_text = ft.Text("", size=16, color=ft.Colors.GREEN, weight=ft.FontWeight.BOLD)
    
    # Контейнер для кнопок функций
    functions_container = ft.Container(
        content=ft.Column([]),
        visible=False
    )
    
    # Контейнер для интерфейса создания
    interface_container = ft.Container(
        content=ft.Column([]),
        visible=False
    )
    
    def validate_api_key(e):
        """Валидация API ключа CyberYozh"""
        api_key = api_key_field.value.strip()
        if not api_key:
            show_snackbar(page, "Введите API ключ", ft.Colors.RED)
            return
        
        original_text = e.control.text
        e.control.disabled = True
        e.control.text = "Проверяем..."
        page.update()
        
        def validate_async():
            try:
                success, message = cyberyozh_api.validate_key(api_key)
                if success:
                    # Сохраняем API ключ
                    save_api_key("cyberyozh", api_key)
                    
                    balance_text.value = f"💰 {message}"
                    
                    # Показываем кнопки функций
                    functions_container.content = ft.Column([
                        ft.Row([
                        ft.ElevatedButton(
                            "Создать прокси",
                            bgcolor=ft.Colors.GREEN,
                            color=ft.Colors.WHITE,
                            style=ft.ButtonStyle(
                                padding=ft.padding.all(15),
                                text_style=ft.TextStyle(size=14, weight=ft.FontWeight.W_500),
                                shape=ft.RoundedRectangleBorder(radius=8)
                            ),
                            on_click=lambda e: show_create_interface()
                        ),
                        ft.ElevatedButton(
                            "Импортировать прокси",
                            bgcolor=ft.Colors.BLUE,
                            color=ft.Colors.WHITE,
                            style=ft.ButtonStyle(
                                padding=ft.padding.all(15),
                                text_style=ft.TextStyle(size=14, weight=ft.FontWeight.W_500),
                                shape=ft.RoundedRectangleBorder(radius=8)
                            ),
                            on_click=lambda e: show_my_proxies()
                        )
                        ], spacing=20, alignment=ft.MainAxisAlignment.CENTER),
                        ft.Container(height=8),
                        ft.Row([
                            ft.ElevatedButton(
                                "Получить API ключ",
                                icon=ft.Icons.LINK,
                                bgcolor=ft.Colors.BLUE,
                                color=ft.Colors.WHITE,
                                on_click=lambda e: page.launch_url("https://app.cyberyozh.com/ru/?utm_source=antic_browser_soft")
                            )
                        ], alignment=ft.MainAxisAlignment.CENTER),
                        ft.Container(height=6),
                        ft.Container(
                            content=ft.Text(
                                "Промокод CYBERYOZH2025 — скидка 10% при пополнении",
                                size=12,
                                color=ft.Colors.GREEN,
                                weight=ft.FontWeight.W_600
                            ),
                            padding=ft.padding.all(6),
                            bgcolor=ft.Colors.GREEN_50,
                            border_radius=8
                        )
                    ], spacing=10)
                    functions_container.visible = True
                    
                    page.update()
                    show_snackbar(page, "API ключ CyberYozh успешно проверен!", ft.Colors.GREEN)
                else:
                    show_snackbar(page, f"Ошибка: {message}", ft.Colors.RED)
            except Exception as ex:
                log_message(f"Ошибка валидации API CyberYozh: {str(ex)}", "ERROR")
                show_snackbar(page, f"Ошибка: {str(ex)}", ft.Colors.RED)
            finally:
                e.control.disabled = False
                e.control.text = original_text
                page.update()
        
        threading.Thread(target=validate_async, daemon=True).start()
    
    def show_create_interface():
        """Показ интерфейса покупки прокси из магазина"""
        log_message("Показываем интерфейс покупки прокси CyberYozh")
        
        # Полный список ISO стран из спецификации API
        # Словарь ISO -> название страны для отображения (используем ISO как value)
        _countries = {
            "US": "США",
            "RU": "Россия",
            "GB": "Великобритания",
            "DE": "Германия",
            "FR": "Франция",
            "PL": "Польша",
            "UA": "Украина",
            "CA": "Канада",
            "AU": "Австралия",
            "CN": "Китай",
            "JP": "Япония",
            "IT": "Италия",
            "ES": "Испания",
            "NL": "Нидерланды",
            "SE": "Швеция",
            "CH": "Швейцария",
            "CZ": "Чехия",
            "TR": "Турция",
            "IN": "Индия",
            "BR": "Бразилия",
            "MX": "Мексика",
            "AE": "ОАЭ",
            "KZ": "Казахстан",
            "BY": "Беларусь",
            # ... при необходимости можно расширить (полный список есть в YAML)
        }
        country_dropdown = ft.Dropdown(
            label="Страна (ISO код)",
            width=220,
            border_radius=8,
            content_padding=10,
            hint_text="Выберите страну",
            options=[ft.dropdown.Option(key, _countries.get(key, key)) for key in sorted(_countries.keys())]
        )
        
        access_type_dropdown = ft.Dropdown(
            label="Тип доступа",
            value="private",
            width=200,
            border_radius=8,
            content_padding=10,
            options=[
                ft.dropdown.Option("private", "Private"),
                ft.dropdown.Option("shared", "Shared")
            ]
        )
        
        category_dropdown = ft.Dropdown(
            label="Категория",
            width=200,
            border_radius=8,
            content_padding=10,
            options=[
                ft.dropdown.Option("residential_static", "Residential Static"),
                ft.dropdown.Option("residential_rotating", "Residential Rotating"),
                ft.dropdown.Option("datacenter_dedicated", "Datacenter Dedicated"),
                ft.dropdown.Option("datacenter_shared", "Datacenter Shared"),
                ft.dropdown.Option("lte", "LTE")
            ]
        )
        
        shop_list = ft.Column([], scroll=ft.ScrollMode.AUTO, height=300)
        
        def search_shop(e):
            """Поиск прокси в магазине"""
            e.control.disabled = True
            e.control.text = "Ищем..."
            page.update()
            
            def fetch_async():
                try:
                    success, proxies = cyberyozh_api.get_shop_proxies(
                        country_code=country_dropdown.value,
                        access_type=access_type_dropdown.value,
                        category=category_dropdown.value
                    )
                    
                    if success:
                        shop_list.controls.clear()
                        # API returns groups (ProxyShop) with 'proxy_products' array; flatten into product list
                        products = []
                        for grp in proxies:
                            grp_products = grp.get('proxy_products') or []
                            for p in grp_products:
                                p_copy = dict(p)
                                p_copy['group_title'] = grp.get('title')
                                p_copy['country_code'] = grp.get('location_country_code')
                                p_copy['proxy_category'] = grp.get('proxy_category') or p.get('proxy_category')
                                products.append(p_copy)

                        for item in products[:30]:  # Показываем первые 30 товаров
                            proxy_id = item.get('id', 'N/A')
                            price = item.get('price_usd') or item.get('price') or 'N/A'
                            category = item.get('proxy_category') or item.get('category') or 'N/A'
                            # Срок хранения/абонпериод явно не указан в схеме, используем title как подсказку
                            term_hint = item.get('title') or item.get('group_title') or ''

                            shop_list.controls.append(
                                ft.Card(
                                    content=ft.Container(
                                        content=ft.Row([
                                            ft.Column([
                                                ft.Text(f"Тип: {category}", size=12, weight=ft.FontWeight.W_600),
                                                ft.Text(f"Срок: {term_hint}", size=11, color=ft.Colors.GREY_700),
                                                ft.Text(f"Цена: ${price}", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN)
                                            ], spacing=4, expand=True),
                                            ft.ElevatedButton(
                                                "Купить",
                                                bgcolor=ft.Colors.ORANGE,
                                                color=ft.Colors.WHITE,
                                                on_click=lambda e, pid=proxy_id: buy_proxy(pid)
                                            )
                                        ], spacing=10),
                                        padding=10
                                    )
                                )
                            )
                        
                        show_snackbar(page, f"Найдено {len(proxies)} прокси!", ft.Colors.GREEN)
                    else:
                        show_snackbar(page, f"Ошибка: {proxies}", ft.Colors.RED)
                except Exception as ex:
                    show_snackbar(page, f"Ошибка поиска: {str(ex)}", ft.Colors.RED)
                finally:
                    e.control.disabled = False
                    e.control.text = "Искать в магазине"
                    page.update()
            
            threading.Thread(target=fetch_async, daemon=True).start()
        
        def buy_proxy(proxy_id):
            """Покупка выбранного прокси"""
            log_message(f"Покупаем прокси {proxy_id}")
            
            def buy_async():
                try:
                    success, result = cyberyozh_api.create_proxy(proxy_id, auto_renew=False)
                    
                    if success:
                        # Дружелюбное уведомление
                        show_snackbar(page, "Прокси куплен!", ft.Colors.GREEN)
                        # Обновляем баланс
                        cyberyozh_api.validate_key(cyberyozh_api.api_key)
                        balance_text.value = f"💰 Баланс: ${cyberyozh_api.balance}"
                        page.update()
                    else:
                        show_snackbar(page, f"Ошибка покупки: {result}", ft.Colors.RED)
                except Exception as ex:
                    show_snackbar(page, translate_cyberyozh_message(str(ex)), ft.Colors.RED)
            
            threading.Thread(target=buy_async, daemon=True).start()
        
        interface_container.content = ft.Container(
            padding=20,
            content=ft.Column([
                ft.Text("Магазин прокси CyberYozh", size=18, weight=ft.FontWeight.BOLD),
                ft.Container(height=15),
                ft.Row([country_dropdown, access_type_dropdown, category_dropdown], spacing=15),
                ft.Container(height=10),
                ft.ElevatedButton(
                    "Искать в магазине",
                    bgcolor=ft.Colors.BLUE,
                    color=ft.Colors.WHITE,
                    on_click=search_shop
                ),
                ft.Container(height=15),
                shop_list,
                ft.Container(height=20),
                ft.ElevatedButton(
                    "Назад",
                    bgcolor=ft.Colors.GREY,
                    color=ft.Colors.WHITE,
                    on_click=lambda e: hide_interface()
                )
            ], spacing=10, scroll=ft.ScrollMode.AUTO)
        )
        
        interface_container.visible = True
        functions_container.visible = False
        page.update()
    
    def show_my_proxies():
        """Импорт прокси CyberYozh: список с чекбоксами, название и GEO, кнопки под списком"""
        log_message("Показываем интерфейс импорта прокси CyberYozh")
        
        # Список прокси для импорта
        import_list = ft.Column(
            controls=[],
            height=420,
            spacing=8,
            scroll=ft.ScrollMode.AUTO
        )
        
        selected_proxies = {}
        
        def _format_geo(item):
            geo = item.get('geoip') or {}
            cc = geo.get('countryCode2') or 'UNK'
            isp = geo.get('ispName') or ''
            tz = item.get('timezone') or ''
            ip = item.get('public_ipaddress') or item.get('connection_host') or ''
            return cc, isp, tz, ip

        def _status_badge(item):
            expired = item.get('expired', False)
            sys_status = item.get('system_status', 'unknown')
            ok = (not expired) and (sys_status == 'active')
            return ft.Container(
                content=ft.Text("РАБОЧИЙ" if ok else "НЕАКТИВЕН", size=12, color=ft.Colors.WHITE),
                padding=ft.padding.symmetric(6, 4),
                bgcolor=ft.Colors.GREEN if ok else ft.Colors.RED,
                border_radius=6
            )

        def load_proxies():
            """Загрузка купленных прокси"""
            try:
                success, proxies_data = cyberyozh_api.get_proxies(
                    protocol="http",
                    type_format="full_url"
                )
                
                if success:
                    import_list.controls.clear()
                    selected_proxies.clear()
                    
                    if not proxies_data:
                        import_list.controls.append(
                            ft.Container(
                                content=ft.Text(
                                    "Нет доступных прокси. Купите прокси в магазине.",
                                    color=ft.Colors.GREY_600,
                                    size=14,
                                    text_align=ft.TextAlign.CENTER
                                ),
                                alignment=ft.alignment.center,
                                padding=20
                            )
                        )
                    else:
                        # proxies_data сейчас список строк. Запросим историю для метаданных.
                        hist_ok, hist = cyberyozh_api.get_proxies(protocol="http", type_format="full_url")
                        meta_list = hist if hist_ok else []
                        
                        for idx, proxy_str in enumerate(proxies_data):
                            try:
                                proxy_id = f"proxy_{idx}"
                                # Найдем метаданные по ip/host
                                host_port = proxy_str.split('@')[-1] if '@' in proxy_str else proxy_str.split('://')[-1]
                                host = host_port.split(':')[0]
                                meta_item = None
                                for m in meta_list:
                                    if isinstance(m, str):
                                        continue
                                    if m.get('connection_host') == host or m.get('public_ipaddress') == host:
                                        meta_item = m
                                        break
                                cc, isp, tz, ip = _format_geo(meta_item or {})
                                proto = proxy_str.split('://')[0]
                                title = ft.Text(f"{proto}://{host_port}", size=14, color=ft.Colors.BLUE)
                                subtitle = ft.Row([
                                    _status_badge(meta_item or {}),
                                    ft.Text(f" {ip}", size=12, color=ft.Colors.BLACK87),
                                    ft.Text(f"  {cc}", size=12, color=ft.Colors.BLACK54),
                                    ft.Text(f"  {tz}", size=12, color=ft.Colors.BLACK38)
                                ], spacing=8, alignment=ft.MainAxisAlignment.START)

                                def make_toggle_handler(pid, pstr):
                                    def handler(e):
                                        toggle_proxy_selection(pid, pstr, e.control.value)
                                    return handler

                                checkbox = ft.Checkbox(
                                    value=False,
                                    on_change=make_toggle_handler(proxy_id, proxy_str)
                                )

                                row = ft.Container(
                                    content=ft.Row([
                                        checkbox,
                                        ft.Column([title, subtitle], spacing=6, expand=True)
                                    ], alignment=ft.MainAxisAlignment.START),
                                    padding=12,
                                    border_radius=10,
                                    bgcolor=ft.Colors.GREY_50,
                                    border=ft.border.all(1, ft.Colors.GREY_200)
                                )

                                import_list.controls.append(row)
                            except Exception as e:
                                log_message(f"Ошибка обработки прокси: {str(e)}", "ERROR")
                                continue
                    
                    page.update()
                else:
                    show_snackbar(page, f"Ошибка загрузки: {proxies_data}", ft.Colors.RED)
            except Exception as e:
                log_message(f"Ошибка загрузки прокси: {str(e)}", "ERROR")
                show_snackbar(page, f"Ошибка загрузки: {str(e)}", ft.Colors.RED)
        
        def toggle_proxy_selection(proxy_id, proxy_str, selected):
            """Переключение выбора прокси"""
            if selected:
                selected_proxies[proxy_id] = proxy_str
            else:
                selected_proxies.pop(proxy_id, None)
        
        def import_selected_proxies(e):
            """Импорт выбранных прокси"""
            if not selected_proxies:
                show_snackbar(page, "Выберите прокси для импорта", ft.Colors.RED)
                return
            
            original_text = e.control.text
            e.control.disabled = True
            e.control.text = f"Импортируем {len(selected_proxies)} прокси..."
            page.update()
            
            def import_async():
                try:
                    imported_count = 0
                    
                    for proxy_str in selected_proxies.values():
                        if save_proxy_to_file(proxy_str):
                            imported_count += 1
                    
                    if imported_count > 0:
                        show_snackbar(page, f"Импортировано {imported_count} прокси!", ft.Colors.GREEN)
                        hide_interface()
                    else:
                        show_snackbar(page, "Все выбранные прокси уже существуют", ft.Colors.ORANGE)
                except Exception as ex:
                    log_message(f"Ошибка импорта прокси: {str(ex)}", "ERROR")
                    show_snackbar(page, f"Ошибка импорта: {str(ex)}", ft.Colors.RED)
                finally:
                    e.control.disabled = False
                    e.control.text = original_text
                    page.update()
            
            threading.Thread(target=import_async, daemon=True).start()
        
        # Интерфейс импорта: список + кнопки снизу
        action_buttons = ft.Row([
            ft.ElevatedButton(
                "Импортировать выбранные",
                bgcolor=ft.Colors.GREEN,
                color=ft.Colors.WHITE,
                style=ft.ButtonStyle(
                    padding=ft.padding.all(15),
                    text_style=ft.TextStyle(size=14, weight=ft.FontWeight.W_500),
                    shape=ft.RoundedRectangleBorder(radius=8)
                ),
                on_click=import_selected_proxies
            ),
            ft.ElevatedButton(
                "Назад",
                bgcolor=ft.Colors.GREY,
                color=ft.Colors.WHITE,
                style=ft.ButtonStyle(
                    padding=ft.padding.all(15),
                    text_style=ft.TextStyle(size=14, weight=ft.FontWeight.W_500),
                    shape=ft.RoundedRectangleBorder(radius=8)
                ),
                on_click=lambda e: hide_interface()
            )
        ], spacing=15, alignment=ft.MainAxisAlignment.CENTER)

        interface_container.content = ft.Column([
            ft.Container(
                content=ft.Row([
                    ft.Text("Импорт прокси CyberYozh", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.BLACK87),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                margin=ft.margin.only(bottom=15)
            ),
            ft.Container(
                content=ft.Text(
                    "Выберите прокси для импорта в Antic Browser:",
                    size=13,
                    color=ft.Colors.GREY_700
                ),
                margin=ft.margin.only(bottom=10)
            ),
            import_list,
            ft.Container(height=12),
            action_buttons
        ], spacing=10, scroll=ft.ScrollMode.AUTO)
        
        interface_container.visible = True
        functions_container.visible = False
        page.update()
        
        # Загружаем прокси сразу
        threading.Thread(target=load_proxies, daemon=True).start()
    
    def hide_interface():
        """Скрытие интерфейса"""
        interface_container.visible = False
        functions_container.visible = True
        page.update()
    
    def go_back_to_main(e):
        """Возврат к главной странице"""
        global current_page
        current_page = "proxies"
        page.controls.clear()
        page.controls = get_proxies_content(page)
        page.update()
    
    # Структура страницы CyberYozh
    main_content = ft.Container(
        content=ft.Column([
            # Заголовок с кнопкой назад
            ft.Container(
                content=ft.Row([
                    ft.IconButton(
                        ft.Icons.ARROW_BACK,
                        icon_color=ft.Colors.BLUE,
                        icon_size=24,
                        on_click=go_back_to_main,
                        tooltip="Назад"
                    ),
                    ft.Text("Proxy CyberYozh", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.BLACK87)
                ], alignment=ft.MainAxisAlignment.START),
                margin=ft.margin.only(bottom=20)
            ),
            
            # Промо-баннер
            ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.CARD_GIFTCARD, color=ft.Colors.PURPLE_600, size=20),
                    ft.Text("🎁 Получите бонусы при регистрации", 
                           size=16, 
                           weight=ft.FontWeight.W_500, 
                           color=ft.Colors.PURPLE_700)
                ], spacing=10, alignment=ft.MainAxisAlignment.CENTER),
                padding=15,
                bgcolor=ft.Colors.PURPLE_50,
                border_radius=10,
                border=ft.border.all(2, ft.Colors.PURPLE_200),
                margin=ft.margin.only(bottom=30)
            ),
            
            # Блок авторизации
            ft.Container(
                content=ft.Column([
                    ft.Text("Авторизация", size=18, weight=ft.FontWeight.W_600, color=ft.Colors.BLACK87),
                    ft.Container(height=10),
                    api_key_field,
                    ft.Container(height=15),
                    ft.ElevatedButton(
                        "Проверить API ключ",
                        bgcolor=ft.Colors.PURPLE,
                        color=ft.Colors.WHITE,
                        style=ft.ButtonStyle(
                            padding=ft.padding.all(15),
                            text_style=ft.TextStyle(size=14, weight=ft.FontWeight.W_500),
                            shape=ft.RoundedRectangleBorder(radius=8)
                        ),
                        on_click=validate_api_key,
                        expand=True
                    ),
                    ft.Container(height=10),
                    balance_text
                ], spacing=0),
                padding=25,
                bgcolor=ft.Colors.WHITE,
                border_radius=15,
                shadow=ft.BoxShadow(blur_radius=8, color=ft.Colors.BLACK12),
                margin=ft.margin.only(bottom=25)
            ),
            
            # Функции
            functions_container,
            interface_container
        ], scroll=ft.ScrollMode.AUTO, spacing=0, expand=True),
        padding=25,
        bgcolor=ft.Colors.GREY_100,
        expand=True
    )
    
    page.controls.clear()
    page.controls = [main_content]
    page.update()

def get_proxies_content(page: ft.Page):
    """Создание интерфейса прокси с улучшенной обработкой"""
    log_message("Создаем интерфейс прокси...")
    
    try:
        # Создаем поля прокси и сохраняем их в page
        proxy_ip_field = ft.TextField(
            label="IP адрес", 
            width=160, 
            hint_text="192.168.1.1",
            border_radius=8,
            content_padding=10
        )
        
        proxy_port_field = ft.TextField(
            label="Порт", 
            keyboard_type=ft.KeyboardType.NUMBER, 
            width=120, 
            hint_text="8080",
            border_radius=8,
            content_padding=10
        )
        
        proxy_protocol_dropdown = ft.Dropdown(
            label="Протокол",
            value="http",
            width=130,
            border_radius=8,
            content_padding=10,
            options=[ft.dropdown.Option("http"), ft.dropdown.Option("socks5")]
        )
        
        proxy_username_field = ft.TextField(
            label="Логин", 
            width=150, 
            hint_text="username",
            border_radius=8,
            content_padding=10
        )
        
        proxy_password_field = ft.TextField(
            label="Пароль", 
            password=True, 
            width=150, 
            hint_text="password",
            border_radius=8,
            content_padding=10
        )
        
        quick_input_field = ft.TextField(
            label="Быстрый ввод прокси",
            expand=True,
            hint_text="IP:port:login:password или protocol://login:password@IP:port",
            border_radius=8,
            content_padding=12,
            on_change=lambda e: parse_quick_input(e.control.value, page)
        )
        
        # Сохраняем поля в page для доступа из других функций
        page.proxy_fields = {
            'ip': proxy_ip_field,
            'port': proxy_port_field,
            'protocol': proxy_protocol_dropdown,
            'username': proxy_username_field,
            'password': proxy_password_field,
            'quick_input': quick_input_field
        }
        log_message("Поля сохранены в page.proxy_fields")
        
        # Создаем список прокси
        proxies = []
        for proxy in get_proxy():
            try:
                if proxy in _proxy_check_cache:
                    result = _proxy_check_cache[proxy]
                else:
                    result = {"status": "unchecked", "country": "UNK", "city": "UNK", "type": proxy.split("://")[0], "proxy_str": proxy}
                
                status_icon = ft.Icon(
                    ft.Icons.CHECK_CIRCLE if result["status"] == "ok" else ft.Icons.ERROR if result["status"] == "error" else ft.Icons.HELP_OUTLINE,
                    color=ft.Colors.GREEN if result["status"] == "ok" else ft.Colors.RED if result["status"] == "error" else ft.Colors.GREY,
                    size=20
                )
                
                check_button = ft.ElevatedButton(
                    "Проверить",
                    bgcolor=ft.Colors.BLUE,
                    color=ft.Colors.WHITE,
                    style=ft.ButtonStyle(
                        padding=ft.padding.all(10),
                        text_style=ft.TextStyle(size=13),
                        shape=ft.RoundedRectangleBorder(radius=8)
                    ),
                    on_click=lambda e, p=proxy: check_proxy_button(p, page, e.control)
                )
                
                display_text = f"{result.get('country', 'UNK')} | {result.get('city', 'UNK')} | {result.get('type', proxy.split('://')[0])}"
                if result["status"] == "error":
                    display_text = f"Не работает | {proxy.split('://')[0]}"
                
                latency_text = ""
                if result.get('latency'):
                    latency = result['latency']
                    if isinstance(latency, (int, float)):
                        latency_text = f" | {latency:.2f}с"
                
                proxy_row = ft.Container(
                    content=ft.Row([
                        ft.Column([
                            ft.Text(display_text + latency_text, size=14, weight=ft.FontWeight.W_500),
                            ft.Text(proxy[:50] + "..." if len(proxy) > 50 else proxy, size=12, color=ft.Colors.GREY_600)
                        ], expand=True),
                        ft.Row([
                            ft.ElevatedButton(
                                "Удалить", 
                                bgcolor=ft.Colors.RED, 
                                color=ft.Colors.WHITE,
                                style=ft.ButtonStyle(
                                    padding=ft.padding.all(10),
                                    text_style=ft.TextStyle(size=13),
                                    shape=ft.RoundedRectangleBorder(radius=8)
                                ),
                                on_click=lambda e, p=proxy: delete_proxy(p, page)
                            ),
                            check_button,
                            status_icon
                        ], spacing=10)
                    ]),
                    padding=15,
                    border_radius=10,
                    bgcolor=ft.Colors.WHITE,
                    border=ft.border.all(1, ft.Colors.GREY_300),
                    shadow=ft.BoxShadow(blur_radius=2, color=ft.Colors.BLACK12)
                )
                
                proxies.append(proxy_row)
            except Exception as e:
                log_message(f"Ошибка создания элемента прокси {proxy}: {str(e)}", "ERROR")
                continue
        
        log_message(f"Создано {len(proxies)} элементов прокси")
        
        add_button = ft.ElevatedButton(
            content=ft.Row([
                ft.Icon(ft.Icons.ADD, color=ft.Colors.WHITE, size=16), 
                ft.Text("Добавить прокси", color=ft.Colors.WHITE, size=14)
            ], spacing=8, alignment=ft.MainAxisAlignment.CENTER),
            bgcolor=ft.Colors.GREEN,
            style=ft.ButtonStyle(
                padding=ft.padding.all(12),
                shape=ft.RoundedRectangleBorder(radius=10)
            ),
            on_click=lambda e: save_proxy(page, e.control),
            height=44  # чуть поменьше, как просили (все кнопки, кроме SX.ORG)
        )
        
        sx_org_button = ft.ElevatedButton(
            content=ft.Row([
                ft.Icon(ft.Icons.STAR, color=ft.Colors.WHITE, size=16),
                ft.Text("SX.ORG Прокси", color=ft.Colors.WHITE, size=14, weight=ft.FontWeight.W_500)
            ], spacing=8, alignment=ft.MainAxisAlignment.CENTER),
            bgcolor=ft.Colors.PURPLE,
            style=ft.ButtonStyle(
                padding=ft.padding.all(15),
                shape=ft.RoundedRectangleBorder(radius=10)
            ),
            on_click=lambda e: open_sx_org_page(page),
            height=50,
            expand=True  # растягивается по ширине
        )
        
        # Кнопка для CyberYozh (вторая основная кнопка) - ОРАНЖЕВАЯ
        cyberyozh_button = ft.ElevatedButton(
            content=ft.Row([
                ft.Icon(ft.Icons.PETS, color=ft.Colors.WHITE, size=16),
                ft.Text("CyberYozh Прокси", color=ft.Colors.WHITE, size=14, weight=ft.FontWeight.W_500)
            ], spacing=8, alignment=ft.MainAxisAlignment.CENTER),
            bgcolor=ft.Colors.ORANGE,
            style=ft.ButtonStyle(
                padding=ft.padding.all(15),
                shape=ft.RoundedRectangleBorder(radius=10)
            ),
            on_click=lambda e: open_cyberyozh_page(page),
            height=50,
            expand=True  # растягивается по ширине
        )

        # Маленькая текстовая кнопка PSB (как ссылка)
        psb_button = ft.TextButton(
            content=ft.Row([
                ft.Text("PSB Proxy", color=ft.Colors.BLUE, size=13),
                ft.Icon(ft.Icons.ARROW_FORWARD, color=ft.Colors.BLUE, size=14)
            ], spacing=5, alignment=ft.MainAxisAlignment.CENTER),
            on_click=open_psb_url
        )
        
        # Структура интерфейса
        main_content = ft.Container(
            content=ft.Column([
                # Заголовок
                ft.Container(
                    content=ft.Text("Управление прокси", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.BLACK87),
                    margin=ft.margin.only(bottom=25)
                ),
                
                # Форма добавления прокси
                ft.Container(
                    content=ft.Column([
                        ft.Text("Добавить новый прокси", size=18, weight=ft.FontWeight.W_600, color=ft.Colors.BLACK87),
                        ft.Container(height=15),
                        quick_input_field,
                        ft.Container(height=15),
                        ft.Row([proxy_ip_field, proxy_port_field, proxy_protocol_dropdown, proxy_username_field, proxy_password_field], 
                              wrap=True, spacing=15, alignment=ft.MainAxisAlignment.CENTER),
                        ft.Container(height=20),
                        # Кнопка добавления прокси
                        ft.Row([add_button], spacing=20, alignment=ft.MainAxisAlignment.CENTER),
                        ft.Container(height=10),
                        # 2 основные кнопки (SX.ORG фиолетовая и CyberYozh оранжевая) рядом
                        ft.Row([sx_org_button, cyberyozh_button], spacing=15, alignment=ft.MainAxisAlignment.CENTER),
                        ft.Container(height=10),
                        # Маленькая кнопка PSB снизу
                        ft.Row([psb_button], alignment=ft.MainAxisAlignment.CENTER)
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0),
                    padding=25,
                    bgcolor=ft.Colors.WHITE,
                    border_radius=15,
                    shadow=ft.BoxShadow(blur_radius=8, color=ft.Colors.BLACK12),
                    margin=ft.margin.only(bottom=25)
                ),
                
                # Список прокси
                ft.Container(
                    content=ft.Column([
                        ft.Text(f"Список прокси ({len(proxies)})", size=18, weight=ft.FontWeight.W_600, color=ft.Colors.BLACK87),
                        ft.Container(height=15),
                        ft.Column(
                            controls=proxies if proxies else [
                                ft.Container(
                                    content=ft.Text("Нет добавленных прокси", color=ft.Colors.GREY_600, size=16, text_align=ft.TextAlign.CENTER),
                                    alignment=ft.alignment.center,
                                    padding=30
                                )
                            ],
                            spacing=12,
                            scroll=ft.ScrollMode.AUTO
                        )
                    ], spacing=0),
                    padding=25,
                    bgcolor=ft.Colors.WHITE,
                    border_radius=15,
                    shadow=ft.BoxShadow(blur_radius=8, color=ft.Colors.BLACK12)
                )
            ], spacing=0, scroll=ft.ScrollMode.AUTO),
            padding=20,
            gradient=ft.LinearGradient(
                begin=ft.alignment.top_center,
                end=ft.alignment.bottom_center,
                colors=[ft.Colors.BLUE_50, ft.Colors.WHITE]
            ),
            expand=True
        )
        
        log_message("Интерфейс прокси создан")
        return [main_content]
        
    except Exception as e:
        log_message(f"Ошибка создания интерфейса прокси: {str(e)}", "ERROR")
        return [ft.Container(
            content=ft.Text(f"Ошибка создания интерфейса: {str(e)}", color=ft.Colors.RED),
            padding=20
        )]

def show_update_dialog(page: ft.Page, update_info):
    """Показ диалога обновления"""
    def close_dialog(e):
        page.dialog.open = False
        page.update()
    
    def start_update(e):
        page.dialog.open = False
        page.update()
        
        # Показываем прогресс обновления
        progress_dialog = ft.AlertDialog(
            title=ft.Text("Обновление"),
            content=ft.Column([
                ft.Text("Загружаем обновление..."),
                ft.ProgressBar(width=400)
            ], height=100),
            modal=True
        )
        page.dialog = progress_dialog
        page.dialog.open = True
        page.update()
        
        def update_progress(progress):
            if hasattr(progress_dialog.content.controls[1], 'value'):
                progress_dialog.content.controls[1].value = progress / 100
                page.update()
        
        # Запускаем обновление
        success = updater.download_and_install_update(
            update_info["download_url"], 
            update_progress
        )
        
        if success:
            # Закрываем приложение для установки обновления
            page.window_close()
        else:
            page.dialog.open = False
            show_snackbar(page, "Ошибка обновления", ft.Colors.RED)
            page.update()
    
    # Диалог обновления
    update_dialog = ft.AlertDialog(
        title=ft.Text(f"Доступно обновление v{update_info['version']}"),
        content=ft.Column([
            ft.Text("Найдена новая версия программы."),
            ft.Text("Изменения:", weight=ft.FontWeight.BOLD),
            ft.Text(update_info.get('changelog', 'Нет описания изменений'), 
                   max_lines=5, overflow=ft.TextOverflow.ELLIPSIS),
        ], height=200, scroll=ft.ScrollMode.AUTO),
        actions=[
            ft.TextButton("Отмена", on_click=close_dialog),
            ft.ElevatedButton("Обновить", on_click=start_update, bgcolor=ft.Colors.BLUE, color=ft.Colors.WHITE)
        ],
        modal=True
    )
    
    page.dialog = update_dialog
    page.dialog.open = True
    page.update()

def main(page: ft.Page):
    """Главная функция с улучшенной обработкой ошибок и автообновлением"""
    global main_page_ref, notification_system
    main_page_ref = page
    
    log_message("Запуск главной функции...")
    
    try:
        # Настройка страницы
        page.title = "Antic Browser v1.0.0"
        page.theme_mode = ft.ThemeMode.LIGHT
        page.fonts = {"SF Pro": "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap"}
        page.bgcolor = ft.Colors.GREY_50
        
        # Инициализируем систему уведомлений
        notification_system = NotificationSystem(page)
        
        log_message("Настройки страницы установлены")
        
        # Проверяем обновления в фоновом режиме
        def check_updates_background():
            try:
                time.sleep(2)  # Ждем загрузки интерфейса
                update_info = updater.check_for_updates()
                if update_info.get("available"):
                    # Показываем диалог обновления в главном потоке
                    def show_update():
                        show_update_dialog(page, update_info)
                    
                    # Планируем показ диалога
                    page.run_thread(show_update)
            except Exception as e:
                log_message(f"Ошибка проверки обновлений: {str(e)}", "ERROR")
        
        # Запускаем проверку обновлений в отдельном потоке
        threading.Thread(target=check_updates_background, daemon=True).start()
        
        def config_load(profile: str):
            """Загрузка конфигурации с улучшенной обработкой"""
            log_message(f"Загружаем конфигурацию: {profile}")
            try:
                config_file = os.path.join(CONFIG_DIR, profile)
                with open(config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
                
                user_agent = config["user-agent"] if config["user-agent"] else random.choice(USER_AGENTS)
                log_message("Конфигурация загружена, запускаем браузер...")
                
                # Запускаем браузер в отдельном потоке
                def run_browser_thread():
                    asyncio.run(run_browser(
                        user_agent, config["screen_height"], config["screen_width"], 
                        config["timezone"], config["lang"], config["proxy"], 
                        config["cookies"], config["webgl"], config["vendor"], 
                        config["cpu"], config["ram"], config["is_touch"], profile
                    ))
                
                threading.Thread(target=run_browser_thread, daemon=True).start()
                
            except Exception as e:
                log_message(f"Ошибка загрузки профиля: {str(e)}", "ERROR")
                show_snackbar(page, f"Ошибка загрузки профиля: {str(e)}", ft.Colors.RED)

        def delete_profile(profile: str):
            """Удаление профиля с улучшенной обработкой"""
            log_message(f"Удаляем профиль: {profile}")
            try:
                config_file = os.path.join(CONFIG_DIR, profile)
                os.remove(config_file)
                page.controls.clear()
                page.controls = get_config_content()
                page.update()
                log_message("Профиль удален")
                show_snackbar(page, "Профиль успешно удалён!", ft.Colors.GREEN)
            except Exception as e:
                log_message(f"Ошибка удаления профиля: {str(e)}", "ERROR")
                show_snackbar(page, f"Ошибка удаления профиля: {str(e)}", ft.Colors.RED)

        def get_config_content():
            """Получение содержимого конфигураций с улучшенной обработкой"""
            log_message("Создаем список конфигураций...")
            configs = []
            
            try:
                for cfg in os.listdir(CONFIG_DIR):
                    if cfg.endswith('.json'):
                        try:
                            config_file = os.path.join(CONFIG_DIR, cfg)
                            with open(config_file, "r", encoding="utf-8") as f:
                                config = json.load(f)
                            
                            config_row = ft.Container(
                                content=ft.Row([
                                    ft.Column([
                                        ft.Text(cfg.rsplit(".", 1)[0], size=16, weight=ft.FontWeight.W_600, color=ft.Colors.BLACK87),
                                        ft.Text(f"Язык: {config.get('lang', 'N/A')} | Часовой пояс: {config.get('timezone', 'N/A')}", 
                                                size=12, color=ft.Colors.GREY_600)
                                    ], expand=True),
                                    ft.Row([
                                        ft.ElevatedButton(
                                            "Запустить", 
                                            bgcolor=ft.Colors.GREEN, 
                                            color=ft.Colors.WHITE,
                                            style=ft.ButtonStyle(
                                                padding=ft.padding.all(12),
                                                text_style=ft.TextStyle(size=13, weight=ft.FontWeight.W_500),
                                                shape=ft.RoundedRectangleBorder(radius=8)
                                            ),
                                            on_click=lambda e, cfg=cfg: config_load(cfg)
                                        ),
                                        ft.IconButton(
                                            icon=ft.Icons.DELETE, 
                                            icon_color=ft.Colors.RED, 
                                            icon_size=20,
                                            on_click=lambda e, cfg=cfg: delete_profile(cfg)
                                        )
                                    ], spacing=10)
                                ]),
                                padding=18,
                                border_radius=12,
                                bgcolor=ft.Colors.WHITE,
                                border=ft.border.all(1, ft.Colors.GREY_200),
                                shadow=ft.BoxShadow(blur_radius=4, color=ft.Colors.BLACK12)
                            )
                            
                            configs.append(config_row)
                            log_message(f"Конфигурация добавлена: {cfg}")
                        except Exception as e:
                            log_message(f"Ошибка чтения конфигурации {cfg}: {str(e)}", "ERROR")
                            continue
            except Exception as e:
                log_message(f"Ошибка чтения директории конфигураций: {str(e)}", "ERROR")
            
            if not configs:
                configs.append(ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.FOLDER_OPEN, size=48, color=ft.Colors.GREY_400),
                        ft.Text("Профили не найдены", size=16, color=ft.Colors.GREY_600, weight=ft.FontWeight.W_500),
                        ft.Text("Создайте первый профиль, нажав кнопку +", size=14, color=ft.Colors.GREY_500)
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=12),
                    padding=40,
                    border_radius=12,
                    bgcolor=ft.Colors.WHITE,
                    shadow=ft.BoxShadow(blur_radius=4, color=ft.Colors.BLACK12)
                ))
            
            log_message(f"Создано {len(configs)} элементов конфигурации")
            
            main_content = ft.Container(
                content=ft.Column([
                    ft.Container(
                        content=ft.Row([
                            ft.Text("🖥️ Профили браузера", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.BLACK87),
                            ft.ElevatedButton(
                                "Создать профиль", 
                                bgcolor=ft.Colors.BLUE, 
                                color=ft.Colors.WHITE,
                                style=ft.ButtonStyle(
                                    padding=ft.padding.all(15),
                                    text_style=ft.TextStyle(size=14, weight=ft.FontWeight.W_500),
                                    shape=ft.RoundedRectangleBorder(radius=10)
                                ),
                                on_click=open_config_page,
                                height=50
                            )
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        margin=ft.margin.only(bottom=25)
                    ),
                    ft.Column(configs, spacing=15, scroll=ft.ScrollMode.AUTO)
                ], spacing=0, scroll=ft.ScrollMode.AUTO),
                padding=20,
                gradient=ft.LinearGradient(
                    begin=ft.alignment.top_center,
                    end=ft.alignment.bottom_center,
                    colors=[ft.Colors.BLUE_50, ft.Colors.WHITE]
                ),
                expand=True
            )
            
            return [main_content]

        def save_config(config_fields):
            """Сохранение конфигурации с улучшенной обработкой"""
            log_message("Сохраняем конфигурацию...")
            try:
                profile_name = config_fields['profile_name'].value
                user_agent_value = config_fields['user_agent'].value if config_fields['user_agent'].value else random.choice(USER_AGENTS)
                screen_value = config_fields['screen'].value if config_fields['screen'].value else "1920×1080"
                timezone_value = config_fields['timezone'].value if config_fields['timezone'].value else "Europe/Moscow"
                language_value = config_fields['language'].value if config_fields['language'].value else "ru-RU"
                proxy_value = config_fields['proxy'].value if config_fields['proxy'].value else False
                cookies_value = config_fields['cookies'].value if config_fields['cookies'].value else False
                webgl_value = config_fields['webgl'].value
                vendor_value = config_fields['vendor'].value if config_fields['vendor'].value else "Google Inc."
                cpu_threads_value = int(config_fields['cpu_threads'].value) if config_fields['cpu_threads'].value else 8
                ram_value = int(config_fields['ram'].value) if config_fields['ram'].value else 8
                is_touch_value = config_fields['is_touch'].value
                
                log_message(f"Сохраняем профиль: {profile_name}")
                
                config_file = os.path.join(CONFIG_DIR, f"{profile_name}.json")
                with open(config_file, "w", encoding="utf-8") as f:
                    json.dump({
                        "user-agent": user_agent_value,
                        "screen_height": int(screen_value.split("×")[1]),
                        "screen_width": int(screen_value.split("×")[0]),
                        "timezone": timezone_value,
                        "lang": language_value,
                        "proxy": proxy_value,
                        "cookies": cookies_value,
                        "webgl": webgl_value,
                        "vendor": vendor_value,
                        "cpu": cpu_threads_value,
                        "ram": ram_value,
                        "is_touch": is_touch_value
                    }, f, indent=4)
                
                log_message("Конфигурация сохранена")
                page.controls.clear()
                page.controls = get_config_content()
                page.update()
                show_snackbar(page, f"Профиль {profile_name} успешно сохранён!", ft.Colors.GREEN)
            except Exception as ex:
                log_message(f"Ошибка сохранения профиля: {str(ex)}", "ERROR")
                show_snackbar(page, f"Ошибка сохранения профиля: {str(ex)}", ft.Colors.RED)

        def open_config_page(e):
            """Открытие страницы создания конфигурации с улучшенной обработкой"""
            log_message("Открываем страницу создания конфигурации...")
            
            try:
                # Определяем номер профиля
                n = 1
                while True:
                    config_file = os.path.join(CONFIG_DIR, f"Profile {n}.json")
                    if not os.path.isfile(config_file):
                        break
                    else:
                        n += 1
                
                log_message(f"Создаем форму для профиля: Profile {n}")
                
                # Создаем все поля
                profile_name_field = ft.TextField(label="Имя профиля", value=f"Profile {n}")
                user_agent_field = ft.TextField(label="User Agent", value=random.choice(USER_AGENTS))
                screen_dropdown = ft.Dropdown(label="Экран", value="1920×1080", options=[ft.dropdown.Option(screen) for screen in SCREENS])
                timezone_dropdown = ft.Dropdown(label="Часовой пояс", value="Europe/Moscow", options=[ft.dropdown.Option(timezone) for timezone in TIMEZONES])
                language_dropdown = ft.Dropdown(label="Язык", value="ru-RU", options=[ft.dropdown.Option(lang) for lang in LANGUAGES])
                proxy_dropdown = ft.Dropdown(label="Прокси", options=[ft.dropdown.Option(proxy) for proxy in get_proxy()])
                cookies_field = ft.TextField(label="Путь к куки")
                webgl_switch = ft.Switch(label="WebGL", value=True)
                vendor_field = ft.TextField(label="Производитель", value="Google Inc.")
                cpu_threads_field = ft.TextField(label="Логические процессоры", value="8", keyboard_type=ft.KeyboardType.NUMBER)
                ram_field = ft.TextField(label="Оперативная память", value="8", keyboard_type=ft.KeyboardType.NUMBER)
                is_touch_switch = ft.Switch(label="Касания", value=False)
                
                # Добавляем кнопку обновления User Agent рядом с полем
                def refresh_user_agent(e):
                    """Обновляет список USER_AGENTS и подставляет случайный UA в поле"""
                    orig_icon = e.control.icon
                    e.control.disabled = True
                    e.control.icon = ft.icons.HOLO
                    page.update()
                    
                    def do_refresh():
                        global USER_AGENTS
                        try:
                            # Пытаемся обновить список
                            resp = requests.get("https://raw.githubusercontent.com/microlinkhq/top-user-agents/refs/heads/master/src/index.json", timeout=10)
                            if resp.status_code == 200:
                                try:
                                    data = resp.json()
                                    if isinstance(data, list) and data:
                                        USER_AGENTS = data
                                except Exception:
                                    pass
                            # Устанавливаем случайный UA из списка
                            if USER_AGENTS:
                                user_agent_field.value = random.choice(USER_AGENTS)
                                show_snackbar(page, "User Agent обновлён", ft.Colors.GREEN)
                            else:
                                show_snackbar(page, "Не удалось получить список User Agents", ft.Colors.ORANGE)
                        except Exception as ex:
                            log_message(f"Ошибка обновления UA: {str(ex)}", "ERROR")
                            show_snackbar(page, f"Ошибка обновления UA: {str(ex)}", ft.Colors.RED)
                        finally:
                            e.control.disabled = False
                            e.control.icon = orig_icon
                            page.update()
                    
                    threading.Thread(target=do_refresh, daemon=True).start()
                
                ua_refresh_button = ft.IconButton(
                    icon=ft.Icons.REFRESH,
                    icon_color=ft.Colors.BLUE,
                    tooltip="Обновить User Agent",
                    on_click=refresh_user_agent
                )
                
                # Создаем словарь полей
                config_fields = {
                    'profile_name': profile_name_field,
                    'user_agent': user_agent_field,
                    'screen': screen_dropdown,
                    'timezone': timezone_dropdown,
                    'language': language_dropdown,
                    'proxy': proxy_dropdown,
                    'cookies': cookies_field,
                    'webgl': webgl_switch,
                    'vendor': vendor_field,
                    'cpu_threads': cpu_threads_field,
                    'ram': ram_field,
                    'is_touch': is_touch_switch
                }
                
                # Создаем форму
                main_content = ft.Column([
                    # Заголовок
                    ft.Text("Новый конфиг", size=24, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
                    ft.Container(height=30),
                    
                    # Имя профиля и кнопка сохранить
                    ft.Row([
                        profile_name_field,
                        ft.ElevatedButton(
                            "✓ Сохранить",
                            bgcolor=ft.Colors.GREEN,
                            color=ft.Colors.WHITE,
                            on_click=lambda e: save_config(config_fields)
                        )
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    
                    ft.Container(height=20),
                    
                    # User Agent с кнопкой обновления
                    ft.Row([user_agent_field, ua_refresh_button], spacing=8),
                    
                    ft.Container(height=15),
                    
                    # Экран, часовой пояс, язык
                    ft.Row([screen_dropdown, timezone_dropdown, language_dropdown], spacing=15),
                    
                    ft.Container(height=15),
                    
                    # Прокси и cookies
                    ft.Row([proxy_dropdown, cookies_field], spacing=15),
                    
                    ft.Container(height=15),
                    
                    # Дополнительные настройки
                    ft.Row([vendor_field, cpu_threads_field, ram_field], spacing=15),
                    
                    ft.Container(height=15),
                    
                    # Переключатели
                    ft.Row([webgl_switch, is_touch_switch], spacing=30)
                    
                ], spacing=0, scroll=ft.ScrollMode.AUTO, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
                
                # Обновляем страницу
                page.controls.clear()
                page.controls = [ft.Container(content=main_content, padding=20, expand=True)]
                page.update()
                
            except Exception as ex:
                log_message(f"Ошибка открытия страницы конфигурации: {str(ex)}", "ERROR")
                show_snackbar(page, f"Ошибка: {str(ex)}", ft.Colors.RED)

        def update_content(e):
            """Обновление содержимого с улучшенной обработкой"""
            global current_page
            try:
                log_message(f"Переключение на вкладку: {e.control.selected_index}")
                if e.control.selected_index == 0:
                    current_page = "profiles"
                    log_message("Показываем профили")
                    page.appbar = ft.AppBar(
                        title=ft.Text("Antic Browser", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                        bgcolor=ft.Colors.BLUE,
                        actions=[
                            ft.IconButton(
                                ft.Icons.ADD_CIRCLE_OUTLINE, 
                                icon_color=ft.Colors.WHITE,
                                icon_size=24,
                                on_click=open_config_page
                            )
                        ]
                    )
                    page.controls.clear()
                    page.controls = get_config_content()
                    page.update()
                elif e.control.selected_index == 1:
                    current_page = "proxies"
                    log_message("Показываем прокси")
                    page.appbar = ft.AppBar(
                        title=ft.Text("Antic Browser", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                        bgcolor=ft.Colors.BLUE
                    )
                    page.controls.clear()
                    page.controls = get_proxies_content(page)
                    page.update()
            except Exception as ex:
                log_message(f"Ошибка переключения вкладки: {str(ex)}", "ERROR")
                show_snackbar(page, f"Ошибка переключения: {str(ex)}", ft.Colors.RED)

        # Настройка интерфейса
        log_message("Настраиваем интерфейс...")
        page.appbar = ft.AppBar(
            title=ft.Text("Antic Browser", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
            bgcolor=ft.Colors.BLUE,
            actions=[
                ft.IconButton(
                    ft.Icons.ADD_CIRCLE_OUTLINE, 
                    icon_color=ft.Colors.WHITE,
                    icon_size=24,
                    on_click=open_config_page
                )
            ]
        )
        
        page.navigation_bar = ft.NavigationBar(
            on_change=update_content,
            destinations=[
                ft.NavigationBarDestination(icon=ft.Icons.TUNE, label="Конфиги"),
                ft.NavigationBarDestination(icon=ft.Icons.VPN_KEY, label="Прокси")
            ],
            selected_index=0,
            bgcolor=ft.Colors.WHITE,
            indicator_color=ft.Colors.BLUE,
            height=65
        )
        
        log_message("Интерфейс настроен")
        
        # Добавляем начальное содержимое
        log_message("Добавляем начальное содержимое...")
        page.add(*get_config_content())
        log_message("Начальное содержимое добавлено")
        
        # Показываем приветственное уведомление
        if notification_system:
            notification_system.show_notification(
                "Добро пожаловать!", 
                "Antic Browser v1.0.0 успешно запущен", 
                "success"
            )
        
    except Exception as e:
        log_message(f"Критическая ошибка в main: {str(e)}", "ERROR")
        # Показываем базовый интерфейс с ошибкой
        page.add(ft.Container(
            content=ft.Text(f"Критическая ошибка: {str(e)}", color=ft.Colors.RED),
            padding=20
        ))

def initialize_directories():
    """Инициализация директорий и файлов"""
    try:
        # Создаем необходимые директории
        os.makedirs(CONFIG_DIR, exist_ok=True)
        os.makedirs(COOKIES_DIR, exist_ok=True)
        log_message("Директории созданы")
        
        # Создаем файлы если их нет
        if not os.path.isfile(PROXIES_FILE):
            with open(PROXIES_FILE, "w", encoding="utf-8") as f:
                json.dump([], f)
            log_message("Файл прокси создан")
        
        if not os.path.isfile(PROXY_CACHE_PATH):
            with open(PROXY_CACHE_PATH, "w", encoding="utf-8") as f:
                json.dump({}, f)
            log_message("Файл кэша прокси создан")
        
        # Загружаем базы данных GeoIP
        if not os.path.isfile(COUNTRY_DATABASE_PATH):
            try:
                log_message("Загружаем базу стран...")
                response = requests.get("https://git.io/GeoLite2-Country.mmdb", timeout=30)
                response.raise_for_status()
                with open(COUNTRY_DATABASE_PATH, "wb") as file:
                    file.write(response.content)
                log_message("База стран загружена")
            except Exception as e:
                log_message(f"Не удалось загрузить базу стран: {str(e)}", "ERROR")
                
        if not os.path.isfile(CITY_DATABASE_PATH):
            try:
                log_message("Загружаем базу городов...")
                response = requests.get("https://git.io/GeoLite2-City.mmdb", timeout=30)
                response.raise_for_status()
                with open(CITY_DATABASE_PATH, "wb") as file:
                    file.write(response.content)
                log_message("База городов загружена")
            except Exception as e:
                log_message(f"Не удалось загрузить базу городов: {str(e)}", "ERROR")
        
        return True
    except Exception as e:
        log_message(f"Ошибка инициализации: {str(e)}", "ERROR")
        return False

if __name__ == "__main__":
    try:
        log_message("=" * 60)
        log_message("🚀 ЗАПУСК УЛУЧШЕННОЙ ВЕРСИИ ANTIC BROWSER V1.0.0")
        log_message("=" * 60)
        log_message("✅ ДОБАВЛЕНО: Система автообновления")
        log_message("✅ ИСПРАВЛЕНО: Проблемы с правами администратора")
        log_message("✅ ИСПРАВЛЕНО: Зависание интерфейса")
        log_message("✅ ИСПРАВЛЕНО: Ссылка на API ключ SX.ORG")
        log_message("✅ ДОБАВЛЕНО: Система уведомлений")
        log_message("✅ УЛУЧШЕНО: Обработка ошибок и логирование")
        log_message("=" * 60)
        
        # Инициализируем все необходимое
        if not initialize_directories():
            log_message("Критическая ошибка инициализации!", "ERROR")
            sys.exit(1)
        
        log_message("🚀 ЗАПУСКАЕМ УЛУЧШЕННОЕ ПРИЛОЖЕНИЕ")
        
        # Запускаем приложение
        ft.app(main)
        
    except Exception as ex:
        log_message("=" * 60)
        log_message(f"❌ КРИТИЧЕСКАЯ ОШИБКА ПРИ ЗАПУСКЕ: {ex}", "ERROR")
        log_message("=" * 60)
        import traceback
        traceback.print_exc()
        input("Нажмите Enter для выхода...")