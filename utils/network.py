# utils/network.py

from requests import get
from urllib.request import Request, urlopen
from config import HEADERS_FOR_REQUESTS


def http_get(url: str):
    return get(url, headers=HEADERS_FOR_REQUESTS)


def download_binary(url: str) -> bytes:
    request = Request(url, headers=HEADERS_FOR_REQUESTS)
    with urlopen(request) as response:
        return response.read()
