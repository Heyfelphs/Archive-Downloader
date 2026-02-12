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
