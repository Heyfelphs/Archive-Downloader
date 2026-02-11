# core/picazor_downloader.py

from config import (
    PICAZOR_CHECK_THREADS_DEFAULT,
    PICAZOR_CHECK_BATCH_DEFAULT,
    PICAZOR_CHECK_DELAY_DEFAULT,
)
from core.services.download_service import download_orchestrator_with_progress


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
    worker=None,  # Referência ao worker para verificar pausa/stop
):
    if workers is None:
        workers = PICAZOR_CHECK_THREADS_DEFAULT
    if link_check_batch is None:
        link_check_batch = PICAZOR_CHECK_BATCH_DEFAULT
    if link_check_delay is None:
        link_check_delay = PICAZOR_CHECK_DELAY_DEFAULT

    return download_orchestrator_with_progress(
        url,
        workers=workers,
        progress_callback=progress_callback,
        target_dir=target_dir,
        download_images=download_images,
        download_videos=download_videos,
        worker=worker,
        valid_indices=valid_indices,
        link_check_batch=link_check_batch,
        link_check_delay=link_check_delay,
    )
