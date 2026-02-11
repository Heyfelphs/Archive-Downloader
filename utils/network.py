# utils/network.py

from requests import Session
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import HEADERS_FOR_REQUESTS

DEFAULT_TIMEOUT = (5, 30)
_SESSION = None


def _get_session() -> Session:
    global _SESSION
    if _SESSION is None:
        session = Session()
        session.headers.update(HEADERS_FOR_REQUESTS)
        retries = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET",),
        )
        adapter = HTTPAdapter(max_retries=retries)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        _SESSION = session
    return _SESSION


def http_get(url: str):
    session = _get_session()
    return session.get(url, timeout=DEFAULT_TIMEOUT)


def download_binary(url: str) -> bytes:
    session = _get_session()
    response = session.get(url, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    return response.content
