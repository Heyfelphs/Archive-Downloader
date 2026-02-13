from __future__ import annotations

from dataclasses import dataclass
from math import ceil
import time
from typing import Iterable
from urllib.parse import urljoin

from utils.network import http_get


@dataclass(frozen=True)
class LeakgalleryMedia:
    media_id: int
    url: str
    media_type: str


class LeakgalleryClient:
    BASE_API = "https://api.leakgallery.com"
    CDN_BASE = "https://cdn.leakgallery.com/"
    DEFAULT_PAGE_SIZE = 12

    def __init__(self, delay: float = 0.0):
        self.delay = delay

    def _profile_url(self, model: str, page: int, media_type: str, sort: str) -> str:
        base = f"{self.BASE_API}/profile/{model}"
        if page > 1:
            base = f"{base}/{page}"
        return f"{base}?type={media_type}&sort={sort}"

    def _media_url(self, media_id: int) -> str:
        return f"{self.BASE_API}/media/{media_id}"

    def get_profile_page(self, model: str, page: int = 1, media_type: str = "All", sort: str = "MostRecent") -> dict:
        url = self._profile_url(model, page, media_type, sort)
        response = http_get(url)
        response.raise_for_status()
        return response.json()

    def get_total_files(self, model: str, media_type: str = "All", sort: str = "MostRecent") -> int:
        data = self.get_profile_page(model, 1, media_type, sort)
        media_count = data.get("mediaCount")
        if isinstance(media_count, int) and media_count >= 0:
            return media_count
        medias = data.get("medias") or []
        return len(medias)

    def iter_media_entries(
        self,
        model: str,
        media_type: str = "All",
        sort: str = "MostRecent",
        max_pages: int | None = None,
    ) -> Iterable[LeakgalleryMedia]:
        page = 1
        total_pages = None
        seen_ids = set()
        while True:
            data = self.get_profile_page(model, page, media_type, sort)
            medias = data.get("medias") or []
            if page == 1:
                media_count = data.get("mediaCount")
                if isinstance(media_count, int) and media_count > 0:
                    total_pages = ceil(media_count / self.DEFAULT_PAGE_SIZE)
            if not medias:
                break
            for item in medias:
                media_id = item.get("id")
                file_path = item.get("file_path")
                if not media_id or not file_path:
                    continue
                if media_id in seen_ids:
                    continue
                seen_ids.add(media_id)
                url = file_path
                if not url.startswith("http"):
                    url = urljoin(self.CDN_BASE, file_path.lstrip("/"))
                media_kind = "video" if item.get("is_video") else "image"
                yield LeakgalleryMedia(media_id=media_id, url=url, media_type=media_kind)
            if max_pages is not None and page >= max_pages:
                break
            if total_pages is not None and page >= total_pages:
                break
            page += 1
            if self.delay:
                time.sleep(self.delay)

    def get_media_ids(
        self,
        model: str,
        media_type: str = "All",
        sort: str = "MostRecent",
        max_pages: int | None = None,
        progress_callback=None,
    ) -> list[int]:
        ids: list[int] = []
        for entry in self.iter_media_entries(model, media_type, sort, max_pages):
            ids.append(entry.media_id)
            if progress_callback:
                progress_callback(len(ids))
        return ids

    def get_media_by_id(self, media_id: int) -> LeakgalleryMedia | None:
        response = http_get(self._media_url(media_id))
        if response.status_code != 200:
            return None
        data = response.json()
        file_path = data.get("file_path")
        if not file_path:
            return None
        url = file_path
        if not url.startswith("http"):
            url = urljoin(self.CDN_BASE, file_path.lstrip("/"))
        media_kind = "video" if data.get("is_video") else "image"
        return LeakgalleryMedia(media_id=media_id, url=url, media_type=media_kind)
