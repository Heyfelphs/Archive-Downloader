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


def download_orchestrator_with_progress(url: str, workers: int, progress_callback=None):
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
    target_dir = join("catalog", "models", model_name)

    try:
        if progress_callback:
            progress_callback({
                "type": "status",
                "status": DOWNLOADING_STATUS
            })
        
        recreate_dir(target_dir)

        total = get_total_files(url)

        with ThreadPool(workers) as pool:
            pool.starmap(
                download_worker_with_progress,
                zip(
                    repeat(url), 
                    repeat(target_dir), 
                    range(total),
                    repeat(progress_callback)
                )
            )

        # Emit final summary
        if progress_callback:
            progress_callback({
                "type": "summary",
                "total_expected": total,
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

