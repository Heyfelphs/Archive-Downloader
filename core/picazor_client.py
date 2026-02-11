# core/picazor_client.py

from bs4 import BeautifulSoup
from re import compile
from concurrent.futures import ThreadPoolExecutor, as_completed
import cloudscraper
import threading
import time


class PicazorClient:
    def _fetch_url_with_retries(self, url: str, scraper=None):
        """
        Tenta buscar uma URL com retries exponenciais.
        Retorna (response, success) onde success indica se a requisição teve sucesso.
        """
        if scraper is None:
            scraper = self.scraper
        retries = 0
        max_retries = 3
        while retries < max_retries:
            try:
                response = scraper.get(url, timeout=10)
                return response, True
            except Exception as e:
                retries += 1
                if retries < max_retries:
                    time.sleep(self.delay * (2 ** retries))
                else:
                    time.sleep(self.delay)
        return None, False

    def _get_thread_scraper(self):
        if not hasattr(self._thread_local, "scraper"):
            self._thread_local.scraper = cloudscraper.create_scraper()
        return self._thread_local.scraper

    def get_valid_indices_yield(self, base_url: str):
        """
        Gera índices válidos um a um, útil para feedback progressivo na UI.
        """
        normalized_base_url = base_url.rstrip('/')
        consecutive_404 = 0
        consecutive_failures = 0
        i = 1
        while True:
            url = f"{normalized_base_url}/{i}"
            response, success = self._fetch_url_with_retries(url)
            if not success:
                consecutive_failures += 1
                if consecutive_failures >= 5:
                    return
                i += 1
                time.sleep(self.delay)
                continue
            consecutive_failures = 0
            if response.status_code == 404:
                consecutive_404 += 1
                if consecutive_404 >= 10:
                    return
                i += 1
                time.sleep(self.delay)
                continue
            else:
                consecutive_404 = 0
            if response.status_code != 200:
                i += 1
                time.sleep(self.delay)
                continue
            try:
                soup = BeautifulSoup(response.text, "html.parser")
                if not self._has_media(soup):
                    i += 1
                    time.sleep(self.delay)
                    continue
            except Exception as e:
                print(f"[Picazor] Error parsing response at index {i}: {e}")
                i += 1
                time.sleep(self.delay)
                continue
            yield i
            i += 1
            time.sleep(self.delay)

    def __init__(self, delay: float = 1.0):
        """
        :param delay: tempo entre requisições
        """
        self.scraper = cloudscraper.create_scraper()
        self.delay = delay
        self._thread_local = threading.local()

    # ---------------------------------------------------------
    # Descobre quantos posts realmente existem
    # ---------------------------------------------------------
    def get_valid_indices(self, base_url: str):
        found = []
        for i in self.get_valid_indices_yield(base_url):
            found.append(i)
            print(f"[Picazor] Found valid index: {i}")
        print(f"[Picazor] Total files found: {len(found)}")
        return found

    def get_total_files(self, base_url: str) -> int:
        return len(self.get_valid_indices(base_url))

    # ---------------------------------------------------------
    # Retorna (media_url, media_type)
    # ---------------------------------------------------------
    def get_media_info(self, url: str):
        response, success = self._fetch_url_with_retries(url)
        if not success or response is None:
            print(f"[Picazor] Error requesting {url}: failed after retries")
            return []
        if response.status_code != 200:
            return []
        try:
            soup = BeautifulSoup(response.text, "html.parser")
        except Exception as e:
            print(f"[Picazor] Error parsing response at url {url}: {e}")
            return []
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

    def _check_index(self, normalized_base_url: str, index: int):
        url = f"{normalized_base_url}/{index}"
        scraper = self._get_thread_scraper()
        response, success = self._fetch_url_with_retries(url, scraper=scraper)
        if not success or response is None:
            return index, "failure"
        if response.status_code == 404:
            return index, "not_found"
        if response.status_code != 200:
            return index, "skip"
        try:
            soup = BeautifulSoup(response.text, "html.parser")
            if not self._has_media(soup):
                return index, "no_media"
        except Exception:
            return index, "parse_error"
        return index, "valid"

    def get_valid_indices_multithread(self, base_url: str, num_threads: int = 6, batch_size: int = None, progress_callback=None):
        normalized_base_url = base_url.rstrip('/')
        found = []
        consecutive_404 = 0
        consecutive_failures = 0

        if batch_size is None:
            batch_size = max(num_threads * 5, 20)

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            i = 1
            while True:
                indices = list(range(i, i + batch_size))
                results = {}
                future_to_idx = {executor.submit(self._check_index, normalized_base_url, idx): idx for idx in indices}
                for future in as_completed(future_to_idx):
                    idx = future_to_idx[future]
                    try:
                        _, status = future.result()
                    except Exception:
                        status = "failure"
                    results[idx] = status

                for idx in indices:
                    status = results.get(idx, "failure")

                    if status == "failure":
                        consecutive_failures += 1
                        if consecutive_failures >= 5:
                            return found
                    else:
                        consecutive_failures = 0

                    if status == "not_found":
                        consecutive_404 += 1
                        if consecutive_404 >= 10:
                            return found
                    else:
                        consecutive_404 = 0

                    if status == "valid":
                        found.append(idx)
                        if progress_callback:
                            progress_callback(len(found))

                i += batch_size
                if self.delay:
                    time.sleep(self.delay)

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
