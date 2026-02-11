# core/picazor_downloader.py

from os.path import join
from utils.filesystem import recreate_dir
from core.picazor_client import PicazorClient
from config import (
    PICAZOR_CHECK_THREADS_DEFAULT,
    PICAZOR_CHECK_BATCH_DEFAULT,
    PICAZOR_CHECK_DELAY_DEFAULT,
)
from utils.network import download_binary
import os


def picazor_download_orchestrator(
    url: str,
    target_dir: str,
    workers: int = None,
    progress_callback=None,
    valid_indices=None,
    link_check_batch: int = None,
    link_check_delay: float = None,
    download_images: bool = True,
    download_videos: bool = True,
):
    if workers is None:
        workers = PICAZOR_CHECK_THREADS_DEFAULT
    if link_check_batch is None:
        link_check_batch = PICAZOR_CHECK_BATCH_DEFAULT
    if link_check_delay is None:
        link_check_delay = PICAZOR_CHECK_DELAY_DEFAULT

    client = PicazorClient(delay=link_check_delay)
    base_url = url.rstrip('/')
    model_name = base_url.split("/")[-1]
    if not target_dir:
        target_dir = join("catalog", "models", model_name)
    target_dir = os.fspath(target_dir)
    recreate_dir(target_dir)

    # Se valid_indices for fornecido, use ela para montar as URLs
    if valid_indices is not None:
        post_urls = [f"{base_url}/{i}" for i in valid_indices]
    else:
        # Usa multithread para checagem rápida dos índices válidos
        valid_indices_mt = client.get_valid_indices_multithread(
            base_url,
            num_threads=workers,
            batch_size=link_check_batch,
        )
        post_urls = [f"{base_url}/{i}" for i in valid_indices_mt]
        valid_indices = valid_indices_mt
    def should_download(media_type: str) -> bool:
        if media_type == "video":
            return download_videos
        return download_images

    # Pre-calculate total files to download for accurate progress tracking
    total_files = 0
    media_lists = {}
    for post_url in post_urls:
        media_list = client.get_media_info(post_url)
        filtered_media_list = [item for item in media_list if should_download(item[1])]
        media_lists[post_url] = filtered_media_list
        total_files += len(filtered_media_list)
    
    files_downloaded = 0

    for idx, post_url in enumerate(post_urls, 1):
        media_list = media_lists[post_url]
        # Determina o número real da página
        if valid_indices is not None:
            page_number = valid_indices[idx-1]
        else:
            # Extrai o número da URL
            try:
                page_number = int(post_url.rstrip('/').split('/')[-1])
            except Exception:
                page_number = idx
        for m_idx, (file_url, media_type) in enumerate(media_list):
            files_downloaded += 1
            # Corrige URLs relativas para absolutas
            if file_url and file_url.startswith("/"):
                file_url = "https://picazor.com" + file_url
            ext = ".mp4" if media_type == "video" else ".jpg"
            filename = (
                f"{model_name}_{page_number}_{m_idx}{ext}"
                if len(media_list) > 1
                else f"{model_name}_{page_number}{ext}"
            )
            path = join(target_dir, filename)
            try:
                with open(path, "wb") as f:
                    f.write(download_binary(file_url))
                if progress_callback:
                    progress_callback({
                        "type": "file_complete",
                        "filename": filename,
                        "index": page_number,
                        "success": files_downloaded,
                        "total": total_files
                    })
            except Exception as e:
                if progress_callback:
                    progress_callback({
                        "type": "file_error",
                        "filename": filename,
                        "error": str(e),
                        "index": page_number,
                        "total": total_files
                    })
    if progress_callback:
        progress_callback({
            "type": "status",
            "status": "Completed"
        })
