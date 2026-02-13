# utils/network.py

import os
import time
from requests import Session
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import cloudscraper
import threading

from config import HEADERS_FOR_REQUESTS

DEFAULT_TIMEOUT = (10, 60)
_THREAD_LOCAL = threading.local()

# Tamanhos de chunk dinâmicos baseados na velocidade de download
MIN_CHUNK_SIZE = 64 * 1024     # 64KB para conexões muito lentas
MAX_CHUNK_SIZE = 2 * 1024 * 1024  # 2MB para conexões rápidas
SPEED_THRESHOLD_FAST = 1 * 1024 * 1024  # > 1MB/s = rápido
SPEED_THRESHOLD_SLOW = 100 * 1024       # < 100KB/s = lento


def _get_session() -> Session:
    if not hasattr(_THREAD_LOCAL, "session"):
        session = Session()
        session.headers.update(HEADERS_FOR_REQUESTS)
        retries = Retry(
            total=6,
            backoff_factor=1.0,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET",),
        )
        adapter = HTTPAdapter(max_retries=retries)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        _THREAD_LOCAL.session = session
    return _THREAD_LOCAL.session


def _get_cloudscraper():
    if not hasattr(_THREAD_LOCAL, "scraper"):
        scraper = cloudscraper.create_scraper()
        scraper.headers.update(HEADERS_FOR_REQUESTS)
        _THREAD_LOCAL.scraper = scraper
    return _THREAD_LOCAL.scraper


def http_get(url: str):
    session = _get_session()
    return session.get(url, timeout=DEFAULT_TIMEOUT)


def download_binary(
    url: str,
    referer: str | None = None,
    origin: str | None = None,
    use_cloudscraper: bool = False,
    cookie: str | None = None,
) -> bytes:
    session = _get_session()
    headers = {}
    if referer:
        headers["Referer"] = referer
    if origin:
        headers["Origin"] = origin
    if cookie:
        headers["Cookie"] = cookie
    if use_cloudscraper:
        scraper = _get_cloudscraper()
        # Per-request headers (e.g. Referer/Origin) override the base headers
        if headers:
            response = scraper.get(url, headers=headers, timeout=DEFAULT_TIMEOUT)
        else:
            response = scraper.get(url, timeout=DEFAULT_TIMEOUT)
    else:
        response = session.get(url, headers=headers or None, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    return response.content


def download_binary_to_file(
    url: str,
    path: str,
    referer: str | None = None,
    origin: str | None = None,
    use_cloudscraper: bool = False,
    cookie: str | None = None,
    progress_callback=None,
    chunk_size: int = 256 * 1024,
) -> None:
    session = _get_session()
    headers = {}
    if referer:
        headers["Referer"] = referer
    if origin:
        headers["Origin"] = origin
    if cookie:
        headers["Cookie"] = cookie
    if use_cloudscraper:
        scraper = _get_cloudscraper()
        response = scraper.get(
            url,
            headers=headers or None,
            timeout=DEFAULT_TIMEOUT,
            stream=True,
        )
    else:
        response = session.get(
            url,
            headers=headers or None,
            timeout=DEFAULT_TIMEOUT,
            stream=True,
        )
    response.raise_for_status()

    content_type = response.headers.get("Content-Type", "")
    if content_type.startswith("text/html"):
        raise ValueError("Resposta HTML inesperada ao baixar arquivo")

    total_length = response.headers.get("Content-Length")
    total_bytes = int(total_length) if total_length and total_length.isdigit() else None
    bytes_downloaded = 0
    temp_path = f"{path}.part"
    
    # Variáveis para chunk dinâmico
    current_chunk_size = chunk_size
    start_time = time.time()
    last_adjustment_time = start_time
    adjustment_interval = 2.0  # Ajusta a cada 2 segundos
    
    try:
        with open(temp_path, "wb") as handle:
            for chunk in response.iter_content(chunk_size=current_chunk_size):
                if not chunk:
                    continue
                handle.write(chunk)
                bytes_downloaded += len(chunk)
                
                # Ajustar chunk_size dinamicamente baseado na velocidade
                current_time = time.time()
                elapsed_since_adjustment = current_time - last_adjustment_time
                
                if elapsed_since_adjustment >= adjustment_interval and bytes_downloaded > 0:
                    elapsed_total = current_time - start_time
                    download_speed = bytes_downloaded / elapsed_total if elapsed_total > 0 else 0
                    
                    # Ajustar chunk size baseado na velocidade
                    if download_speed > SPEED_THRESHOLD_FAST:
                        # Conexão rápida: aumentar chunk para 2MB
                        current_chunk_size = MAX_CHUNK_SIZE
                    elif download_speed < SPEED_THRESHOLD_SLOW:
                        # Conexão lenta: diminuir chunk para 64KB
                        current_chunk_size = MIN_CHUNK_SIZE
                    else:
                        # Velocidade média: usar chunk padrão ou ajustar proporcionalmente
                        # Interpolação linear entre MIN e chunk_size original
                        ratio = (download_speed - SPEED_THRESHOLD_SLOW) / (SPEED_THRESHOLD_FAST - SPEED_THRESHOLD_SLOW)
                        current_chunk_size = int(MIN_CHUNK_SIZE + (chunk_size - MIN_CHUNK_SIZE) * ratio)
                        current_chunk_size = max(MIN_CHUNK_SIZE, min(current_chunk_size, MAX_CHUNK_SIZE))
                    
                    last_adjustment_time = current_time
                
                if progress_callback:
                    progress_callback(bytes_downloaded, total_bytes)
                    
        if total_bytes is not None and bytes_downloaded < total_bytes:
            raise ValueError("Download incompleto (tamanho menor que o esperado)")
        if bytes_downloaded == 0:
            raise ValueError("Download retornou zero bytes")
        os.replace(temp_path, path)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
