# core/worker.py

from os.path import join
from utils.network import download_binary
from core.fapello_client import get_media_info


def prepare_filename(file_url: str, index: int, media_type: str) -> str:
    base = file_url.split("/")[-3]
    ext = ".mp4" if media_type == "video" else ".jpg"
    return f"{base}_{index}{ext}"


def download_worker(base_url: str, target_dir: str, index: int):
    # Garante que a base termina com barra
    if not base_url.endswith("/"):
        base_url = base_url + "/"
    link = f"{base_url}{index}"
    model_name = link.split("/")[3]

    file_url, media_type = get_media_info(link)
    if not file_url or model_name not in file_url:
        return

    filename = prepare_filename(file_url, index, media_type)
    path = join(target_dir, filename)

    with open(path, "wb") as f:
        f.write(download_binary(file_url))
