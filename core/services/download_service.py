from __future__ import annotations

from dataclasses import dataclass, field
from multiprocessing.pool import ThreadPool
from os.path import join
from typing import Callable, Iterable, Optional
from urllib.parse import urlparse
import os
import time

from config import (
    CANCELLED_STATUS,
    COMPLETED_STATUS,
    DOWNLOADING_STATUS,
    ERROR_STATUS,
    PICAZOR_CHECK_BATCH_DEFAULT,
    PICAZOR_CHECK_DELAY_DEFAULT,
    PICAZOR_CHECK_THREADS_DEFAULT,
)
from core.fapello_client import get_media_info, get_total_files
from core.picazor_client import PicazorClient
from core.worker import prepare_filename
from utils.filesystem import recreate_dir
from utils.network import download_binary

ProgressCallback = Callable[[dict], None]


@dataclass
class DownloadStats:
    success: int = 0
    failed: int = 0
    skipped: int = 0
    failed_indices: list[int] = field(default_factory=list)


def _wait_if_paused(worker) -> bool:
    while worker and getattr(worker, "is_paused", False):
        if getattr(worker, "stop_requested", False):
            return False
        time.sleep(0.1)
    return not (worker and getattr(worker, "stop_requested", False))


def _extract_model_name(url: str) -> str:
    parts = [p for p in url.split("/") if p]
    return parts[-1] if parts else ""


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

    if "picazor.com" in base_url:
        client = PicazorClient()
        media_list = client.get_media_info(f"{base_url.rstrip('/')}/{index}")
        for i in range(len(media_list)):
            url, media_type = media_list[i]
            if url and url.startswith("/"):
                parsed = urlparse(base_url)
                base_domain = f"{parsed.scheme}://{parsed.netloc}"
                media_list[i] = (base_domain + url, media_type)
    else:
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
):
    if worker and getattr(worker, "stop_requested", False):
        return

    if not _wait_if_paused(worker):
        return

    media_list = _media_list_for_index(
        base_url,
        index,
        download_images=download_images,
        download_videos=download_videos,
    )

    if not media_list:
        stats.skipped += 1
        if progress_callback:
            progress_callback({
                "type": "file_skipped",
                "index": index,
                "reason": "Arquivo nao disponivel",
            })
        return

    model_name = _extract_model_name(base_url)
    for idx, (file_url, media_type) in enumerate(media_list):
        if worker and getattr(worker, "stop_requested", False):
            return
        if not _wait_if_paused(worker):
            return

        if "fapello.com" in base_url or "picazor.com" in base_url:
            ext = ".mp4" if media_type == "video" else ".jpg"
            if len(media_list) > 1:
                filename = f"{model_name}_{index}_{idx}{ext}"
            else:
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
            with open(path, "wb") as handle:
                handle.write(download_binary(file_url))
            stats.success += 1
            if progress_callback:
                progress_callback({
                    "type": "file_complete",
                    "filename": filename,
                    "index": index,
                    "success": stats.success,
                })
        except Exception as exc:
            stats.failed += 1
            stats.failed_indices.append(index)
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
):
    stats = DownloadStats()
    model_name = _extract_model_name(url)
    if target_dir is None:
        target_dir = join("catalog", "models", model_name)
    target_dir = os.fspath(target_dir)

    if link_check_batch is None:
        link_check_batch = PICAZOR_CHECK_BATCH_DEFAULT
    if link_check_delay is None:
        link_check_delay = PICAZOR_CHECK_DELAY_DEFAULT
    if workers is None:
        workers = PICAZOR_CHECK_THREADS_DEFAULT

    def worker_wrapper(idx: int):
        if worker and getattr(worker, "stop_requested", False):
            return None
        if not _wait_if_paused(worker):
            return None
        download_worker_with_progress(
            url,
            target_dir,
            idx,
            stats,
            progress_callback,
            download_images=download_images,
            download_videos=download_videos,
            worker=worker,
        )
        return idx

    try:
        if progress_callback:
            progress_callback({"type": "status", "status": DOWNLOADING_STATUS})
        recreate_dir(target_dir)

        pool = ThreadPool(workers)
        was_cancelled = False
        try:
            if "picazor.com" in url:
                client = PicazorClient(delay=link_check_delay)
                if valid_indices is None:
                    valid_indices = client.get_valid_indices_multithread(
                        url,
                        num_threads=workers,
                        batch_size=link_check_batch,
                    )
                valid_indices = list(valid_indices)
                total_expected = len(valid_indices)

                chunk_size = max(1, workers * 2)
                for _ in pool.imap_unordered(worker_wrapper, valid_indices, chunksize=chunk_size):
                    if worker and getattr(worker, "stop_requested", False):
                        pool.terminate()
                        pool.join()
                        was_cancelled = True
                        raise KeyboardInterrupt("Download stopped by user")

                if not (worker and getattr(worker, "stop_requested", False)):
                    consecutive_skips = 0
                    idx = max(valid_indices) + 1 if valid_indices else 1
                    max_idx = idx + 1000
                    while consecutive_skips < 10 and idx < max_idx:
                        if worker and getattr(worker, "stop_requested", False):
                            pool.terminate()
                            pool.join()
                            was_cancelled = True
                            raise KeyboardInterrupt("Download stopped by user")
                        chunk = list(range(idx, min(idx + workers * 2, max_idx)))
                        prev_skipped = stats.skipped
                        for _ in pool.imap_unordered(worker_wrapper, chunk, chunksize=max(1, workers)):
                            if worker and getattr(worker, "stop_requested", False):
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
            else:
                total_expected = get_total_files(url)
                indices = list(range(1, total_expected + 1))
                chunk_size = max(1, workers * 2)
                for _ in pool.imap_unordered(worker_wrapper, indices, chunksize=chunk_size):
                    if worker and getattr(worker, "stop_requested", False):
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
