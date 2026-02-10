# core/picazor_client.py

from bs4 import BeautifulSoup
from re import compile
import cloudscraper
import time


class PicazorClient:

    def __init__(self, delay: float = 1.0, max_check: int = 500):
        """
        :param delay: tempo entre requisições
        :param max_check: limite máximo de páginas a testar
        """
        self.scraper = cloudscraper.create_scraper()
        self.delay = delay
        self.max_check = max_check

    # ---------------------------------------------------------
    # Descobre quantos posts realmente existem
    # ---------------------------------------------------------
    def get_valid_indices(self, base_url: str):
        consecutive_404 = 0
        found = []
        for i in range(1, self.max_check + 1):
            url = f"{base_url}/{i}"
            print(f"[Picazor] Checking {url}")
            response = self.scraper.get(url)
            if response.status_code == 404:
                consecutive_404 += 1
                print(f"[Picazor] 404 at index {i} (consecutive: {consecutive_404})")
                if consecutive_404 >= 10:
                    print(f"[Picazor] Stopping: 10 consecutive 404s at index {i}")
                    break
                continue
            else:
                consecutive_404 = 0
            if response.status_code != 200:
                print(f"[Picazor] Stop: status {response.status_code} at index {i}")
                continue
            soup = BeautifulSoup(response.text, "html.parser")
            if not self._has_media(soup):
                print(f"[Picazor] Stop: no media at index {i}")
                continue
            found.append(i)
        print(f"[Picazor] Total files found: {len(found)}")
        return found

    def get_total_files(self, base_url: str) -> int:
        return len(self.get_valid_indices(base_url))

    # ---------------------------------------------------------
    # Retorna (media_url, media_type)
    # ---------------------------------------------------------
    def get_media_info(self, url: str):
        response = self.scraper.get(url)
        if response.status_code != 200:
            return []
        soup = BeautifulSoup(response.text, "html.parser")
        # Prioriza vídeo se existir, senão imagem
        video_src = None
        for video in soup.find_all("video"):
            for source in video.find_all("source"):
                src = source.get("src")
                if src:
                    video_src = src
                    break
            if video_src:
                break
        if video_src:
            return [(video_src, "video")]
        image_src = None
        for image in soup.find_all("img", src=compile(r"uploads")):
            image_src = image.get("src")
            if image_src:
                break
        if image_src:
            return [(image_src, "image")]
        return []

    # ---------------------------------------------------------
    # Verifica se a página contém mídia válida
    # ---------------------------------------------------------
    def _has_media(self, soup: BeautifulSoup) -> bool:
        if soup.find("img", src=compile(r"uploads")):
            return True

        if soup.find("video"):
            return True

        return False

    # ---------------------------------------------------------
    # Gera todas as URLs válidas automaticamente
    # ---------------------------------------------------------
    def generate_post_urls(self, base_url: str):
        total = self.get_total_files(base_url)
        return [f"{base_url}/{i}" for i in range(1, total + 1)]
