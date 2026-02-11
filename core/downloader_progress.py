import os
import time
# core/downloader_progress.py

from multiprocessing.pool import ThreadPool
from utils.filesystem import recreate_dir
from core.fapello_client import get_total_files, get_media_info
from core.worker import prepare_filename
from os.path import join
from utils.network import download_binary
from config import (
    DOWNLOADING_STATUS,
    COMPLETED_STATUS,
    ERROR_STATUS,
    CANCELLED_STATUS,
)


# Global counters for tracking
download_stats = {
    "success": 0,
    "failed": 0,
    "skipped": 0,
    "failed_indices": []
}


def download_worker_with_progress(
    base_url: str,
    target_dir: str,
    index: int,
    progress_callback=None,
    download_images: bool = True,
    download_videos: bool = True,
    worker=None,  # Referência ao worker para verificar pausa/stop
):
    """Download worker with progress callback."""
    global download_stats
    
    # Verificar se há solicitação de stop
    if worker and worker.stop_requested:
        return
    
    # Aguardar se estiver em pausa
    while worker and worker.is_paused:
        time.sleep(0.1)
    
    # Garante que a base termina com barra
    if not base_url.endswith("/"):
        base_url = base_url + "/"
    link = f"{base_url}{index}"
    model_name = link.split("/")[3]

    def should_download(media_type: str) -> bool:
        if media_type == "video":
            return download_videos
        return download_images

    # Importa get_media_info correto
    if "picazor.com" in base_url:
        from core.picazor_client import PicazorClient
        client = PicazorClient()
        media_list = client.get_media_info(link)
        # Corrige URLs relativas para absolutas (robusto para qualquer domínio picazor)
        for i in range(len(media_list)):
            url, media_type = media_list[i]
            if url and url.startswith("/"):
                # Usa o domínio da base
                from urllib.parse import urlparse
                parsed = urlparse(base_url)
                base_domain = f"{parsed.scheme}://{parsed.netloc}"
                media_list[i] = (base_domain + url, media_type)
    else:
        media_list = []
        file_url, media_type = get_media_info(link)
        if file_url:
            media_list.append((file_url, media_type))

    media_list = [item for item in media_list if should_download(item[1])]

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
            if not file_url.startswith("http"):
                raise ValueError(f"URL inválida para download: {file_url}")
            with open(path, "wb") as f:
                f.write(download_binary(file_url))
            print(f"[DOWNLOAD] Página baixada: {link}")
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
                    "file_url": file_url,
                    "success": download_stats["success"],
                    "failed": download_stats["failed"]
                })


def download_orchestrator_with_progress(
    url,
    workers=6,
    progress_callback=None,
    target_dir=None,
    download_images: bool = True,
    download_videos: bool = True,
    worker=None,  # Referência ao worker para verificar pausa/stop
):
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

    # Define worker_wrapper once for reuse
    def worker_wrapper(idx):
        if worker and worker.stop_requested:
            return None
        while worker and worker.is_paused:
            time.sleep(0.1)
        if worker and worker.stop_requested:
            return None
        download_worker_with_progress(
            url,
            target_dir,
            idx,
            progress_callback,
            download_images=download_images,
            download_videos=download_videos,
            worker=worker,
        )
        return idx

    try:
        if progress_callback:
            progress_callback({
                "type": "status",
                "status": DOWNLOADING_STATUS
            })
        recreate_dir(target_dir)

        pool = ThreadPool(workers)
        was_cancelled = False
        try:
            if "picazor.com" in url:
                from core.picazor_client import PicazorClient
                client = PicazorClient()
                valid_indices = client.get_valid_indices(url)
                if not valid_indices:
                    valid_indices = list(range(1, client.get_total_files(url) + 1))
                total_expected = len(valid_indices)
                
                # Process with imap_unordered for better concurrency
                chunk_size = max(1, workers * 2)
                for result in pool.imap_unordered(worker_wrapper, valid_indices, chunksize=chunk_size):
                    if worker and worker.stop_requested:
                        pool.terminate()
                        pool.join()
                        was_cancelled = True
                        raise KeyboardInterrupt("Download stopped by user")
                
                # Continuar tentando além do maior índice encontrado até 10 skips consecutivos
                if not (worker and worker.stop_requested):
                    consecutive_skips = 0
                    idx = max(valid_indices) + 1 if valid_indices else 1
                    max_idx = idx + 1000
                    
                    while consecutive_skips < 10 and idx < max_idx:
                        if worker and worker.stop_requested:
                            pool.terminate()
                            pool.join()
                            was_cancelled = True
                            raise KeyboardInterrupt("Download stopped by user")
                        
                        # Process in small chunks
                        chunk = list(range(idx, min(idx + workers * 2, max_idx)))
                        prev_skipped = download_stats["skipped"]
                        
                        for result in pool.imap_unordered(worker_wrapper, chunk, chunksize=max(1, workers)):
                            if worker and worker.stop_requested:
                                pool.terminate()
                                pool.join()
                                was_cancelled = True
                                raise KeyboardInterrupt("Download stopped by user")
                        
                        new_skips = download_stats["skipped"] - prev_skipped
                        if new_skips == len(chunk):
                            consecutive_skips += new_skips
                        else:
                            consecutive_skips = 0
                        idx += len(chunk)
            else:
                total_expected = get_total_files(url)
                indices = list(range(1, total_expected + 1))
                
                # Process with imap_unordered for better concurrency
                chunk_size = max(1, workers * 2)
                for result in pool.imap_unordered(worker_wrapper, indices, chunksize=chunk_size):
                    if worker and worker.stop_requested:
                        pool.terminate()
                        pool.join()
                        was_cancelled = True
                        raise KeyboardInterrupt("Download stopped by user")
        finally:
            pool.close()
            pool.join()

        # Emit final summary mantendo o valor inicial
        if progress_callback:
            progress_callback({
                "type": "summary",
                "total_expected": total_expected,
                "success": download_stats["success"],
                "failed": download_stats["failed"],
                "skipped": download_stats["skipped"],
                "failed_indices": download_stats["failed_indices"]
            })

        if was_cancelled:
            if progress_callback:
                progress_callback({
                    "type": "status",
                    "status": CANCELLED_STATUS
                })
            return

        if progress_callback:
            progress_callback({
                "type": "status",
                "status": COMPLETED_STATUS
            })

    except KeyboardInterrupt:
        if progress_callback:
            progress_callback({
                "type": "status",
                "status": CANCELLED_STATUS
            })
    except Exception as e:
        if progress_callback:
            progress_callback({
                "type": "status",
                "status": f"{ERROR_STATUS}{e}"
            })
