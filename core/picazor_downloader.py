# core/picazor_downloader.py

from os.path import join
from utils.filesystem import recreate_dir
from core.picazor_client import PicazorClient
from utils.network import download_binary
import os


def picazor_download_orchestrator(url: str, target_dir: str, workers: int = 6, progress_callback=None):
    client = PicazorClient()
    model_name = url.split("/")[-1]
    if not target_dir:
        target_dir = join("catalog", "models", model_name)
    target_dir = os.fspath(target_dir)
    recreate_dir(target_dir)

    post_urls = client.generate_post_urls(url)
    total = len(post_urls)

    for idx, post_url in enumerate(post_urls, 1):
        media_list = client.get_media_info(post_url)
        for m_idx, (file_url, media_type) in enumerate(media_list):
            # Corrige URLs relativas para absolutas
            if file_url and file_url.startswith("/"):
                file_url = "https://picazor.com" + file_url
            ext = ".mp4" if media_type == "video" else ".jpg"
            filename = f"{model_name}_{idx}_{m_idx+1}{ext}"
            path = join(target_dir, filename)
            try:
                with open(path, "wb") as f:
                    f.write(download_binary(file_url))
                if progress_callback:
                    progress_callback({
                        "type": "file_complete",
                        "filename": filename,
                        "index": idx,
                        "success": idx
                    })
            except Exception as e:
                if progress_callback:
                    progress_callback({
                        "type": "file_error",
                        "filename": filename,
                        "error": str(e),
                        "index": idx
                    })
    if progress_callback:
        progress_callback({
            "type": "status",
            "status": "Completed"
        })
