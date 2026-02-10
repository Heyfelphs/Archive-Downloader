import threading
import queue
import os
# core/downloader_progress.py

from multiprocessing.pool import ThreadPool
from itertools import repeat
from utils.filesystem import recreate_dir
from core.fapello_client import get_total_files, get_media_info
from core.worker import download_worker, prepare_filename
from os.path import join
from utils.network import download_binary
from config import (
    DOWNLOADING_STATUS,
    COMPLETED_STATUS,
    ERROR_STATUS,
)


# Global counters for tracking
download_stats = {
    "success": 0,
    "failed": 0,
    "skipped": 0,
    "failed_indices": []
}


def download_worker_with_progress(base_url: str, target_dir: str, index: int, progress_callback=None):
    """Download worker with progress callback."""
    global download_stats
    # Garante que a base termina com barra
    if not base_url.endswith("/"):
        base_url = base_url + "/"
    link = f"{base_url}{index}"
    model_name = link.split("/")[3]

    # Importa get_media_info correto
    if "picazor.com" in base_url:
        from core.picazor_client import PicazorClient
        client = PicazorClient()
        media_list = client.get_media_info(link)
        # Corrige URLs relativas para absolutas
        for i in range(len(media_list)):
            url, media_type = media_list[i]
            if url and url.startswith("/"):
                media_list[i] = ("https://picazor.com" + url, media_type)
    else:
        from core.fapello_client import get_media_info
        media_list = []
        file_url, media_type = get_media_info(link)
        if file_url:
            media_list.append((file_url, media_type))

    if not media_list:
        download_stats["skipped"] += 1
        if progress_callback:
            progress_callback({
                "type": "file_skipped",
                "index": index,
                "reason": "Arquivo não disponível"
            })
        return

    for idx, (file_url, media_type) in enumerate(media_list):
        filename = prepare_filename(file_url, f"{index}_{idx+1}", media_type)
        # Emit progress - file being downloaded
        if progress_callback:
            progress_callback({
                "type": "file_start",
                "filename": filename,
                "index": index
            })
        # Baixa arquivo
        path = join(target_dir, filename)
        try:
            with open(path, "wb") as f:
                f.write(download_binary(file_url))
            download_stats["success"] += 1
            if progress_callback:
                progress_callback({
                    "type": "file_complete",
                    "filename": filename,
                    "index": index,
                    "success": download_stats["success"]
                })
        except Exception as e:
            download_stats["failed"] += 1
            download_stats["failed_indices"].append(index)
            if progress_callback:
                progress_callback({
                    "type": "file_error",
                    "filename": filename,
                    "error": str(e),
                    "success": download_stats["success"],
                    "failed": download_stats["failed"]
                })


def download_orchestrator_with_progress(url, workers=6, progress_callback=None, target_dir=None):
    """Download orchestrator with progress tracking."""
    global download_stats
    download_stats = {
        "success": 0,
        "failed": 0,
        "skipped": 0,
        "failed_indices": []
    }

    model_name = url.split("/")[3]
    if target_dir is None:
        target_dir = join("catalog", "models", model_name)
    target_dir = os.fspath(target_dir)

    try:
        if progress_callback:
            progress_callback({
                "type": "status",
                "status": DOWNLOADING_STATUS
            })
        recreate_dir(target_dir)

        total = get_total_files(url)
        indices = list(range(1, total + 1))
        # Baixar tudo em paralelo (workers threads)
        with ThreadPool(workers) as pool:
            pool.map(
                lambda idx: download_worker_with_progress(url, target_dir, idx, progress_callback),
                indices
            )

        # Tentar baixar páginas extras para cada página pulada (apenas vídeos, pois imagens já são sequenciais)
        extra_attempts = 0
        max_extra = 20  # Limite de tentativas extras para evitar loop infinito
        while download_stats["skipped"] > 0 and extra_attempts < max_extra:
            skipped_now = download_stats["skipped"]
            download_stats["skipped"] = 0
            indices_extras = [total + i + 1 for i in range(skipped_now)]
            if not indices_extras:
                break
            # Checar tipo dos extras
            extra_video_indices = []
            extra_image_indices = []
            for idx in indices_extras:
                base_url = url if url.endswith("/") else url + "/"
                link = f"{base_url}{idx}"
                file_url, media_type = get_media_info(link)
                if not file_url:
                    continue
                if media_type == "video":
                    extra_video_indices.append(idx)
                else:
                    extra_image_indices.append(idx)
            # Imagens extras sequencial
            for idx in extra_image_indices:
                download_worker_with_progress(url, target_dir, idx, progress_callback)
            # Vídeos extras paralelo (máximo 3 simultâneos)
            if extra_video_indices:
                with ThreadPool(3) as pool:
                    pool.starmap(
                        download_worker_with_progress,
                        zip(
                            repeat(url),
                            repeat(target_dir),
                            extra_video_indices,
                            repeat(progress_callback)
                        )
                    )
            total += len(indices_extras)
            extra_attempts += 1

        # Emit final summary mantendo o valor inicial
        if progress_callback:
            progress_callback({
                "type": "summary",
                "total_expected": get_total_files(url),
                "success": download_stats["success"],
                "failed": download_stats["failed"],
                "skipped": download_stats["skipped"],
                "failed_indices": download_stats["failed_indices"]
            })

        if progress_callback:
            progress_callback({
                "type": "status",
                "status": COMPLETED_STATUS
            })

    except Exception as e:
        if progress_callback:
            progress_callback({
                "type": "status",
                "status": f"{ERROR_STATUS}{e}"
            })

