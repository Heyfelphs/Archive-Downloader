from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from multiprocessing.pool import ThreadPool
from os.path import join
from typing import Callable, Iterable, Optional
from urllib.parse import urlparse
import os
import threading

from config import (
    CANCELLED_STATUS,
    COMPLETED_STATUS,
    DOWNLOADING_STATUS,
    ERROR_STATUS,
    PICAZOR_CHECK_BATCH_DEFAULT,
    FIXED_PICAZOR_THREADS,
    FIXED_PICAZOR_DELAY,
    SiteType,
    detect_site_type,
    get_site_label,
    should_continue_worker,
    wait_if_paused,
)

from core.fapello_client import get_media_info, get_total_files
from core.fapfolder_client import FapfolderClient
from core.leakgallery_client import LeakgalleryClient
from core.picazor_client import PicazorClient
from core.worker import prepare_filename
from utils.network import download_binary_to_file

ProgressCallback = Callable[[dict], None]

# Thread-local cache para clients
_THREAD_LOCAL_CLIENTS = threading.local()


@dataclass
class DownloadStats:
    success: int = 0
    failed: int = 0
    skipped: int = 0
    failed_indices: list[int] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def increment_success(self):
        with self._lock:
            self.success += 1

    def increment_failed(self, index: int):
        with self._lock:
            self.failed += 1
            self.failed_indices.append(index)

    def increment_skipped(self):
        with self._lock:
            self.skipped += 1

    def get_stats(self):
        with self._lock:
            return {
                "success": self.success,
                "failed": self.failed,
                "skipped": self.skipped,
                "failed_indices": self.failed_indices.copy(),
            }


def _get_picazor_client(delay: float = FIXED_PICAZOR_DELAY) -> PicazorClient:
    """Obtém client Picazor do cache thread-local"""
    if not hasattr(_THREAD_LOCAL_CLIENTS, "picazor"):
        _THREAD_LOCAL_CLIENTS.picazor = PicazorClient(delay)
    return _THREAD_LOCAL_CLIENTS.picazor


def _get_leakgallery_client(delay: float = 0.0) -> LeakgalleryClient:
    """Obtém client Leakgallery do cache thread-local"""
    if not hasattr(_THREAD_LOCAL_CLIENTS, "leakgallery"):
        _THREAD_LOCAL_CLIENTS.leakgallery = LeakgalleryClient(delay)
    return _THREAD_LOCAL_CLIENTS.leakgallery


def _get_fapfolder_client(cookie: str | None = None, delay: float = 0.0) -> FapfolderClient:
    """Obtém client Fapfolder do cache thread-local"""
    cache_key = f"fapfolder_{cookie or 'no_cookie'}"
    if not hasattr(_THREAD_LOCAL_CLIENTS, cache_key):
        setattr(_THREAD_LOCAL_CLIENTS, cache_key, FapfolderClient(cookie=cookie, delay=delay))
    return getattr(_THREAD_LOCAL_CLIENTS, cache_key)


def _extract_model_name(url: str) -> str:
    parts = [p for p in url.split("/") if p]
    return parts[-1] if parts else ""


def _extension_from_url(file_url: str, media_type: str) -> str:
    path = urlparse(file_url).path
    _, ext = os.path.splitext(path)
    if ext:
        return ext
    return ".mp4" if media_type == "video" else ".jpg"


def _media_list_for_index(
    base_url: str,
    index: int,
    download_images: bool,
    download_videos: bool,
):
    def should_download(media_type: str) -> bool:
        if media_type == "video":
            return download_videos
        return download_images

    site_type = detect_site_type(base_url)
    
    if site_type == SiteType.PICAZOR:
        client = _get_picazor_client()
        media_list = client.get_media_info(f"{base_url.rstrip('/')}/{index}")
        for i in range(len(media_list)):
            url, media_type = media_list[i]
            if url and url.startswith("/"):
                parsed = urlparse(base_url)
                base_domain = f"{parsed.scheme}://{parsed.netloc}"
                media_list[i] = (base_domain + url, media_type)
    elif site_type == SiteType.LEAKGALLERY:
        client = _get_leakgallery_client()
        media = client.get_media_by_id(index)
        media_list = [(media.url, media.media_type)] if media else []
    elif site_type == SiteType.FAPFOLDER:
        media_list = []
    else:  # FAPELLO or UNKNOWN
        media_list = []
        file_url, media_type = get_media_info(f"{base_url.rstrip('/')}/{index}")
        if file_url:
            media_list.append((file_url, media_type))

    return [item for item in media_list if should_download(item[1])]


def download_worker_with_progress(
    base_url: str,
    target_dir: str,
    index: int,
    stats: DownloadStats,
    progress_callback: Optional[ProgressCallback] = None,
    download_images: bool = True,
    download_videos: bool = True,
    worker=None,
    download_chunk_size: int | None = None,
    media_override: tuple[str, str] | None = None,
    auth_cookie: str | None = None,
):
    if not should_continue_worker(worker):
        return

    if not wait_if_paused(worker):
        return

    if media_override is not None:
        media_list = [media_override]
    else:
        media_list = _media_list_for_index(
            base_url,
            index,
            download_images=download_images,
            download_videos=download_videos,
        )

    if not media_list:
        stats.increment_skipped()
        if progress_callback:
            progress_callback({
                "type": "file_skipped",
                "index": index,
                "reason": "Arquivo nao disponivel",
            })
        return

    model_name = _extract_model_name(base_url)
    site_type = detect_site_type(base_url)
    
    parsed_base = urlparse(base_url)
    origin = None
    if parsed_base.scheme and parsed_base.netloc:
        origin = f"{parsed_base.scheme}://{parsed_base.netloc}"
    
    # Configurar referer baseado no tipo de site
    referer = None
    if site_type in (SiteType.FAPELLO, SiteType.PICAZOR, SiteType.LEAKGALLERY):
        referer = f"{base_url.rstrip('/')}/{index}"
    elif site_type == SiteType.FAPFOLDER:
        referer = base_url
    
    for idx, (file_url, media_type) in enumerate(media_list):
        if not should_continue_worker(worker) or not wait_if_paused(worker):
            return

        # Gerar filename baseado no tipo de site
        ext = ".mp4" if media_type == "video" else ".jpg"
        if site_type in (SiteType.FAPELLO, SiteType.PICAZOR, SiteType.LEAKGALLERY):
            if len(media_list) > 1:
                filename = f"{model_name}_{index}_{idx}{ext}"
            else:
                filename = f"{model_name}_{index}{ext}"
        elif site_type == SiteType.FAPFOLDER:
            ext = _extension_from_url(file_url, media_type)
            filename = f"{model_name}_{index}{ext}"
        else:
            filename = prepare_filename(file_url, f"{index}_{idx+1}", media_type)
        
        if progress_callback:
            progress_callback({
                "type": "file_start",
                "filename": filename,
                "index": index,
            })
        
        path = join(target_dir, filename)
        try:
            if not file_url.startswith("http"):
                raise ValueError(f"URL invalida para download: {file_url}")
            
            # Check if file already exists
            if os.path.exists(path):
                stats.increment_skipped()
                if progress_callback:
                    progress_callback({
                        "type": "file_skipped",
                        "index": index,
                        "reason": "Arquivo ja existe",
                        "filename": filename,
                    })
                continue
            
            use_cloudscraper = site_type == SiteType.PICAZOR
            
            def _file_progress(bytes_downloaded: int, total_bytes: int | None):
                if progress_callback:
                    progress_callback({
                        "type": "file_progress",
                        "filename": filename,
                        "index": index,
                        "bytes_downloaded": bytes_downloaded,
                        "total_bytes": total_bytes,
                    })

            download_binary_to_file(
                file_url,
                path,
                referer=referer,
                origin=origin,
                use_cloudscraper=use_cloudscraper,
                cookie=auth_cookie,
                progress_callback=_file_progress,
                chunk_size=download_chunk_size or 256 * 1024,
            )
            # Check if file is empty (0 bytes) and delete if so
            if os.path.exists(path) and os.path.getsize(path) == 0:
                os.remove(path)
                raise ValueError(f"Arquivo baixado vazio (0 bytes)")
            stats.increment_success()
            if progress_callback:
                progress_callback({
                    "type": "file_complete",
                    "filename": filename,
                    "index": index,
                    "success": stats.success,
                })
        except Exception as exc:
            stats.increment_failed(index)
            if progress_callback:
                progress_callback({
                    "type": "file_error",
                    "filename": filename,
                    "error": str(exc),
                    "file_url": file_url,
                    "success": stats.success,
                    "failed": stats.failed,
                })


def download_orchestrator_with_progress(
    url: str,
    workers: int = 6,
    progress_callback: Optional[ProgressCallback] = None,
    target_dir: Optional[str] = None,
    download_images: bool = True,
    download_videos: bool = True,
    worker=None,
    valid_indices: Optional[Iterable[int]] = None,
    link_check_batch: Optional[int] = None,
    link_check_delay: Optional[float] = None,
    max_items: Optional[int] = None,
    download_chunk_size: Optional[int] = None,
    auth_cookie: Optional[str] = None,
):
    stats = DownloadStats()
    model_name = _extract_model_name(url)
    site_type = detect_site_type(url)
    
    if target_dir is None:
        site_label = get_site_label(url)
        target_dir = join("catalog", "models", site_label, model_name)
    target_dir = os.fspath(target_dir)

    if link_check_batch is None:
        link_check_batch = PICAZOR_CHECK_BATCH_DEFAULT
    if link_check_delay is None:
        link_check_delay = FIXED_PICAZOR_DELAY
    if workers is None:
        workers = FIXED_PICAZOR_THREADS

    def worker_wrapper(idx: int | tuple[int, tuple[str, str]]):
        if not should_continue_worker(worker) or not wait_if_paused(worker):
            return None
        
        media_override = None
        index = idx
        if isinstance(idx, tuple) and len(idx) == 2 and isinstance(idx[0], int):
            index = idx[0]
            media_override = idx[1]
        
        download_worker_with_progress(
            url,
            target_dir,
            index,
            stats,
            progress_callback,
            download_images=download_images,
            download_videos=download_videos,
            worker=worker,
            download_chunk_size=download_chunk_size,
            media_override=media_override,
            auth_cookie=auth_cookie,
        )
        return idx

    try:
        if progress_callback:
            progress_callback({"type": "status", "status": DOWNLOADING_STATUS})
        # Create directory if it doesn't exist, but don't delete existing files
        os.makedirs(target_dir, exist_ok=True)

        pool = ThreadPool(workers)
        was_cancelled = False
        
        try:
            if site_type == SiteType.PICAZOR:
                client = _get_picazor_client(delay=link_check_delay)
                if valid_indices is None:
                    valid_indices = client.get_valid_indices_multithread(
                        url,
                        num_threads=workers,
                        batch_size=link_check_batch,
                    )
                valid_indices = list(valid_indices)
                if max_items is not None:
                    valid_indices = valid_indices[:max_items]
                total_expected = len(valid_indices)

                chunk_size = max(1, workers * 2)
                for _ in pool.imap_unordered(worker_wrapper, valid_indices, chunksize=chunk_size):
                    if not should_continue_worker(worker):
                        pool.terminate()
                        pool.join()
                        was_cancelled = True
                        raise KeyboardInterrupt("Download stopped by user")

                # Continue verificando índices adicionais
                if valid_indices and should_continue_worker(worker):
                    consecutive_skips = 0
                    idx = max(valid_indices) + 1 if valid_indices else 1
                    max_idx = idx + 1000
                    
                    while consecutive_skips < 10 and idx < max_idx:
                        if not should_continue_worker(worker):
                            pool.terminate()
                            pool.join()
                            was_cancelled = True
                            raise KeyboardInterrupt("Download stopped by user")
                        
                        chunk = list(range(idx, min(idx + workers * 2, max_idx)))
                        prev_skipped = stats.skipped
                        
                        for _ in pool.imap_unordered(worker_wrapper, chunk, chunksize=max(1, workers)):
                            if not should_continue_worker(worker):
                                pool.terminate()
                                pool.join()
                                was_cancelled = True
                                raise KeyboardInterrupt("Download stopped by user")
                        
                        new_skips = stats.skipped - prev_skipped
                        if new_skips == len(chunk):
                            consecutive_skips += new_skips
                        else:
                            consecutive_skips = 0
                        idx += len(chunk)
                        
            elif site_type == SiteType.LEAKGALLERY:
                if valid_indices is None:
                    client = _get_leakgallery_client()
                    valid_indices = client.get_media_ids(model_name)
                valid_indices = list(valid_indices)
                if max_items is not None:
                    valid_indices = valid_indices[:max_items]
                total_expected = len(valid_indices)
                
                chunk_size = max(1, workers * 2)
                for _ in pool.imap_unordered(worker_wrapper, valid_indices, chunksize=chunk_size):
                    if not should_continue_worker(worker):
                        pool.terminate()
                        pool.join()
                        was_cancelled = True
                        raise KeyboardInterrupt("Download stopped by user")
                        
            elif site_type == SiteType.FAPFOLDER:
                if valid_indices is None:
                    client = _get_fapfolder_client()
                    valid_indices = client.get_media_entries(model_name)
                entries = list(valid_indices)
                if download_images and not download_videos:
                    entries = [e for e in entries if e.media_type == "image"]
                elif download_videos and not download_images:
                    entries = [e for e in entries if e.media_type == "video"]
                if max_items is not None:
                    entries = entries[:max_items]
                total_expected = len(entries)
                indexed_entries = list(enumerate([(e.url, e.media_type) for e in entries], start=1))
                
                chunk_size = max(1, workers * 2)
                for _ in pool.imap_unordered(worker_wrapper, indexed_entries, chunksize=chunk_size):
                    if not should_continue_worker(worker):
                        pool.terminate()
                        pool.join()
                        was_cancelled = True
                        raise KeyboardInterrupt("Download stopped by user")
                        
            else:
                # Fapello e outros sites
                total_expected = get_total_files(url)
                if max_items is not None:
                    total_expected = min(total_expected, max_items)
                indices = list(range(1, total_expected + 1))
                
                chunk_size = max(1, workers * 2)
                for _ in pool.imap_unordered(worker_wrapper, indices, chunksize=chunk_size):
                    if not should_continue_worker(worker):
                        pool.terminate()
                        pool.join()
                        was_cancelled = True
                        raise KeyboardInterrupt("Download stopped by user")
        finally:
            pool.close()
            pool.join()

        if progress_callback:
            progress_callback({
                "type": "summary",
                "total_expected": total_expected,
                "success": stats.success,
                "failed": stats.failed,
                "skipped": stats.skipped,
                "failed_indices": stats.failed_indices,
            })

        if was_cancelled:
            if progress_callback:
                progress_callback({"type": "status", "status": CANCELLED_STATUS})
            return

        if progress_callback:
            progress_callback({"type": "status", "status": COMPLETED_STATUS})
    except KeyboardInterrupt:
        if progress_callback:
            progress_callback({"type": "status", "status": CANCELLED_STATUS})
    except Exception as exc:
        if progress_callback:
            progress_callback({"type": "status", "status": f"{ERROR_STATUS}{exc}"})
