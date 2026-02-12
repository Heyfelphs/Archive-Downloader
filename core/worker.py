# core/worker.py

from os.path import join
import os
from utils.network import download_binary_to_file
from core.fapello_client import get_media_info


def prepare_filename(file_url: str, index: int, media_type: str) -> str:
    parts = [p for p in file_url.split("/") if p]
    base = parts[-3] if len(parts) >= 3 else (parts[-1] if parts else "arquivo")
    ext = ".mp4" if media_type == "video" else ".jpg"
    return f"{base}_{index}{ext}"


def download_worker(base_url: str, target_dir: str, index: int):
    # Garante que a base termina com barra
    if not base_url.endswith("/"):
        base_url = base_url + "/"
    link = f"{base_url}{index}"

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
        return

    for idx, (file_url, media_type) in enumerate(media_list):
        filename = prepare_filename(file_url, f"{index}_{idx+1}", media_type)
        path = join(target_dir, filename)
        try:
            if not file_url or not file_url.startswith("http"):
                continue
            if os.path.exists(path):
                continue
            download_binary_to_file(file_url, path)
        except Exception:
            continue
