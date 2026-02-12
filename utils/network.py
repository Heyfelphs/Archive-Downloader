# utils/network.py

import os
from requests import Session
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import cloudscraper

from config import HEADERS_FOR_REQUESTS

DEFAULT_TIMEOUT = (10, 60)
_SESSION = None
_CLOUDSCRAPER = None


def _get_session() -> Session:
    global _SESSION
    if _SESSION is None:
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
        _SESSION = session
    return _SESSION


def _get_cloudscraper():
    global _CLOUDSCRAPER
    if _CLOUDSCRAPER is None:
        _CLOUDSCRAPER = cloudscraper.create_scraper()
        _CLOUDSCRAPER.headers.update(HEADERS_FOR_REQUESTS)
    return _CLOUDSCRAPER


def http_get(url: str):
    session = _get_session()
    return session.get(url, timeout=DEFAULT_TIMEOUT)


def download_binary(
    url: str,
    referer: str | None = None,
    origin: str | None = None,
    use_cloudscraper: bool = False,
) -> bytes:
    session = _get_session()
    headers = {}
    if referer:
        headers["Referer"] = referer
    if origin:
        headers["Origin"] = origin
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
    progress_callback=None,
    chunk_size: int = 256 * 1024,
) -> None:
    session = _get_session()
    headers = {}
    if referer:
        headers["Referer"] = referer
    if origin:
        headers["Origin"] = origin
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
    try:
        with open(temp_path, "wb") as handle:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if not chunk:
                    continue
                handle.write(chunk)
                bytes_downloaded += len(chunk)
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
