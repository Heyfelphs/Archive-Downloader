from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Iterable

import cloudscraper

from config import HEADERS_FOR_REQUESTS


PHOTO_RE = re.compile(r"https?://fap\.onl/uploads/photos/[^\"'\s>]+\.(?:jpg|jpeg|png|webp)", re.IGNORECASE)
VIDEO_RE = re.compile(r"https?://fap\.onl/uploads/videos/[^\"'\s>]+\.(?:mp4|webm)", re.IGNORECASE)


@dataclass(frozen=True)
class FapfolderMedia:
    url: str
    media_type: str


class FapfolderClient:
    BASE_URL = "https://fapfolder.club"
    LOAD_MORE_URL = f"{BASE_URL}/includes/ajax/data/load.php"

    def __init__(self, cookie: str | None = None, delay: float = 0.0, max_pages: int = 50):
        self.delay = delay
        self.max_pages = max_pages
        self.scraper = cloudscraper.create_scraper()
        self.scraper.headers.update(HEADERS_FOR_REQUESTS)
        if cookie:
            self.scraper.headers.update({"Cookie": cookie})

    def _fetch_html(self, url: str, referer: str | None = None) -> str:
        headers = {}
        if referer:
            headers["Referer"] = referer
        response = self.scraper.get(url, headers=headers or None, timeout=20)
        response.raise_for_status()
        return response.text

    def _extract_group_id(self, html: str) -> str | None:
        match = re.search(r"js_see-more\"[^>]+data-id=\"(\d+)\"", html)
        if match:
            return match.group(1)
        return None

    def _dedupe(self, items: Iterable[str]) -> list[str]:
        seen = set()
        ordered = []
        for item in items:
            if item in seen:
                continue
            seen.add(item)
            ordered.append(item)
        return ordered

    def _extract_media(self, html: str, include_photos: bool, include_videos: bool) -> list[FapfolderMedia]:
        urls: list[str] = []
        if include_photos:
            urls.extend(PHOTO_RE.findall(html))
        if include_videos:
            urls.extend(VIDEO_RE.findall(html))
        urls = self._dedupe(urls)
        medias: list[FapfolderMedia] = []
        for url in urls:
            media_type = "video" if "/uploads/videos/" in url else "image"
            medias.append(FapfolderMedia(url=url, media_type=media_type))
        return medias

    def _load_more(self, data_get: str, group_id: str, offset: int, referer: str) -> dict | None:
        payload = {
            "get": data_get,
            "id": group_id,
            "type": "group",
            "offset": offset,
            "premfeed": 0,
            "time": -1,
        }
        headers = {
            "X-Requested-With": "XMLHttpRequest",
            "Referer": referer,
        }
        response = self.scraper.post(self.LOAD_MORE_URL, data=payload, headers=headers, timeout=20)
        if response.status_code != 200:
            return None
        try:
            return response.json()
        except Exception:
            return None

    def validate_cookie(self, model: str) -> tuple[bool, str]:
        if not model:
            return False, "Modelo vazio"
        url = f"{self.BASE_URL}/groups/{model}/photos"
        html = self._fetch_html(url)
        group_id = self._extract_group_id(html)
        if not group_id:
            return False, "Grupo nao encontrado"
        data = self._load_more("photos", group_id, 1, url)
        if not data:
            return False, "Falha na requisicao"
        if data.get("callback") == "modal('#modal-login')":
            return False, "Login necessario"
        if data.get("data"):
            return True, "OK"
        return False, "Sem dados"

    def _iter_section(self, model: str, section: str, include_photos: bool, include_videos: bool) -> Iterable[FapfolderMedia]:
        url = f"{self.BASE_URL}/groups/{model}/{section}"
        html = self._fetch_html(url)
        for media in self._extract_media(html, include_photos, include_videos):
            yield media

        group_id = self._extract_group_id(html)
        if not group_id:
            return

        offset = 1
        for _ in range(self.max_pages):
            data = self._load_more(section, group_id, offset, url)
            if not data:
                return
            if data.get("callback") == "modal('#modal-login')":
                return
            html_block = data.get("data")
            if not html_block:
                return
            new_items = list(self._extract_media(html_block, include_photos, include_videos))
            if not new_items:
                return
            for media in new_items:
                yield media
            offset += 1
            if self.delay:
                time.sleep(self.delay)

    def iter_media_entries(self, model: str, include_photos: bool = True, include_videos: bool = True) -> Iterable[FapfolderMedia]:
        seen = set()
        if include_photos:
            for media in self._iter_section(model, "photos", True, False):
                if media.url in seen:
                    continue
                seen.add(media.url)
                yield media
        if include_videos:
            for media in self._iter_section(model, "videos", False, True):
                if media.url in seen:
                    continue
                seen.add(media.url)
                yield media

    def get_media_entries(self, model: str, include_photos: bool = True, include_videos: bool = True, progress_callback=None) -> list[FapfolderMedia]:
        entries: list[FapfolderMedia] = []
        for media in self.iter_media_entries(model, include_photos, include_videos):
            entries.append(media)
            if progress_callback:
                progress_callback(len(entries))
        return entries
