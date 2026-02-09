# core/fapello_client.py

from bs4 import BeautifulSoup
from re import search, compile
from utils.network import http_get


def get_total_files(url: str) -> int:
    page = http_get(url)
    soup = BeautifulSoup(page.content, "html.parser")

    match = search(r'(\d+)\s*Media', soup.get_text())
    if match:
        return int(match.group(1))

    pattern = compile(f"{url}\\d+/")
    links = soup.find_all("a", href=pattern)

    max_index = 0
    for link in links:
        value = link.get("href").rstrip("/").split("/")[-1]
        if value.isnumeric():
            max_index = max(max_index, int(value))

    return max_index


def get_media_info(url: str):
    page = http_get(url)
    soup = BeautifulSoup(page.content, "html.parser")

    container = soup.find("div", class_="flex justify-between items-center")
    if not container:
        return None, None

    if "video/mp4" in str(container):
        return container.find("source").get("src"), "video"

    return container.find("img").get("src"), "image"
