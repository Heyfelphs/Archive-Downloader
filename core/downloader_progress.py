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
    
    try:
        # Garante que a base termina com barra
        if not base_url.endswith("/"):
            base_url = base_url + "/"
        link = f"{base_url}{index}"
        model_name = link.split("/")[3]

        file_url, media_type = get_media_info(link)
        if not file_url or model_name not in file_url:
            # File not available at this index
            download_stats["skipped"] += 1
            if progress_callback:
                progress_callback({
                    "type": "file_skipped",
                    "index": index,
                    "reason": "Arquivo não disponível"
                })
            return

        filename = prepare_filename(file_url, index, media_type)
        
        # Emit progress - file being downloaded
        if progress_callback:
            progress_callback({
                "type": "file_start",
                "filename": filename,
                "index": index
            })
        
        path = join(target_dir, filename)

        with open(path, "wb") as f:
            f.write(download_binary(file_url))
        
        # Emit progress - file completed
        download_stats["success"] += 1
        if progress_callback:
            progress_callback({
                "type": "file_complete",
                "filename": filename,
                "index": index,
                "success": download_stats["success"],
                "failed": download_stats["failed"]
            })
            
    except Exception as e:
        download_stats["failed"] += 1
        download_stats["failed_indices"].append(index)
        if progress_callback:
            progress_callback({
                "type": "file_error",
                "filename": f"Arquivo {index}",
                "index": index,
                "error": str(e),
                "success": download_stats["success"],
                "failed": download_stats["failed"]
            })


def download_orchestrator_with_progress(url: str, workers: int, progress_callback=None, target_dir=None):
    # Contador total de arquivos baixados
    download_count = 0

    def counting_download_worker_with_progress(base_url, target_dir, idx, progress_callback):
        nonlocal download_count
        download_count += 1
        return download_worker_with_progress(base_url, target_dir, idx, progress_callback)

    """Download orchestrator with progress tracking."""
    global download_stats
    
    # Reset stats at start
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
        # Baixar tudo em paralelo (6 threads)
        with ThreadPool(6) as pool:
            pool.map(
                lambda idx: counting_download_worker_with_progress(url, target_dir, idx, progress_callback),
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
                "failed_indices": download_stats["failed_indices"],
                "arquivos_baixados": download_count
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

