# core/downloader.py

from multiprocessing.pool import ThreadPool
from itertools import repeat
from os.path import join
from utils.filesystem import recreate_dir
from core.fapello_client import get_total_files
from core.worker import download_worker
from config import (
    DOWNLOADING_STATUS,
    COMPLETED_STATUS,
    ERROR_STATUS,
)


def download_orchestrator(queue, url: str, workers: int):
    model_name = url.split("/")[3]
    target_dir = join("catalog", "models", model_name)

    try:
        queue.put(DOWNLOADING_STATUS)
        recreate_dir(target_dir)

        total = get_total_files(url)

        with ThreadPool(workers) as pool:
            pool.starmap(
                download_worker,
                zip(repeat(url), repeat(target_dir), range(total))
            )

        queue.put(COMPLETED_STATUS)

    except Exception as e:
        queue.put(f"{ERROR_STATUS}{e}")
