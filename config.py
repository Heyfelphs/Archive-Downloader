# Configuração de persistência de UI
import json
import os

CONFIG_STATE_FILE = os.path.join(os.path.dirname(__file__), 'ui_state.json')

def save_ui_state(state: dict):
    try:
        with open(CONFIG_STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Erro ao salvar estado da UI: {e}")

def load_ui_state() -> dict:
    try:
        if os.path.exists(CONFIG_STATE_FILE):
            with open(CONFIG_STATE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Erro ao carregar estado da UI: {e}")
    return {}
# config.py

APP_NAME = "Fapello.Downloader"
VERSION = "4.1"

APP_NAME_COLOR = "#ffbf00"
DEFAULT_THEME = "dark"

GITHUB_URL = "https://github.com/Djdefrag/Fapello.Downloader"
TELEGRAM_URL = "https://linktr.ee/j3ngystudio"
QS_URL = "https://github.com/Djdefrag/QualityScaler"

COMPLETED_STATUS = "Completed"
DOWNLOADING_STATUS = "Downloading"
ERROR_STATUS = "Error"
STOP_STATUS = "Stop"
CANCELLED_STATUS = "Cancelled"

HEADERS_FOR_REQUESTS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/128.0.0.0 Safari/537.36"
    )
}

PICAZOR_CHECK_BATCH_DEFAULT = 30

# Thread and Download Configuration
FIXED_PICAZOR_THREADS = 4
FIXED_PICAZOR_DELAY = 0.1
FIXED_FAPELLO_THREADS = 3
FIXED_DOWNLOAD_CHUNK_SIZE = 256 * 1024  # 256 KB

# Site Detection
from enum import Enum
from typing import NamedTuple

class SiteType(Enum):
    """Enum para tipos de sites suportados"""
    FAPELLO = "fapello"
    PICAZOR = "picazor"
    LEAKGALLERY = "leakgallery"
    FAPFOLDER = "fapfolder"
    UNKNOWN = "unknown"

class SiteConfig(NamedTuple):
    """Configuração de site"""
    site_type: SiteType
    label: str
    domain: str

SITE_CONFIGS = {
    SiteType.PICAZOR: SiteConfig(SiteType.PICAZOR, "Picazor", "picazor.com"),
    SiteType.FAPELLO: SiteConfig(SiteType.FAPELLO, "Fapello", "fapello.com"),
    SiteType.LEAKGALLERY: SiteConfig(SiteType.LEAKGALLERY, "Leakgallery", "leakgallery.com"),
    SiteType.FAPFOLDER: SiteConfig(SiteType.FAPFOLDER, "Fapfolder", "fapfolder.club"),
}

def detect_site_type(url: str) -> SiteType:
    """Detecta o tipo de site de uma URL"""
    url_lower = url.lower()
    for site_type, config in SITE_CONFIGS.items():
        if config.domain in url_lower:
            return site_type
    return SiteType.UNKNOWN

def get_site_label(url: str) -> str:
    """Retorna o label do site baseado na URL"""
    site_type = detect_site_type(url)
    if site_type in SITE_CONFIGS:
        return SITE_CONFIGS[site_type].label
    from urllib.parse import urlparse
    parsed = urlparse(url)
    return parsed.netloc or "Site"

def should_continue_worker(worker) -> bool:
    """Verifica se worker deve continuar (não foi parado)"""
    return not (worker and getattr(worker, "stop_requested", False))

def wait_if_paused(worker) -> bool:
    """Aguarda se worker está pausado, retorna False se foi parado"""
    import time
    while worker and getattr(worker, "is_paused", False):
        if not should_continue_worker(worker):
            return False
        time.sleep(0.1)
    return should_continue_worker(worker)
