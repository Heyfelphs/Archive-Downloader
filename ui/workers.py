from pathlib import Path
import threading

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QIcon, QPixmap, QColor, QPainter, QImage, QFont

from config import (
    PICAZOR_CHECK_BATCH_DEFAULT,
)

FIXED_PICAZOR_THREADS = 4
FIXED_PICAZOR_DELAY = 0.1
FIXED_FAPELLO_THREADS = 3
FIXED_DOWNLOAD_CHUNK_SIZE = 256 * 1024
from core.fapello_client import get_total_files as get_fapello_total_files
from core.services.download_service import download_orchestrator_with_progress


class FetchWorker(QThread):
    """Worker thread para buscar informacoes sem bloquear a UI."""

    finished = Signal(dict)
    error = Signal(str)
    progress = Signal(int)

    def __init__(self, url: str, picazor_threads: int, picazor_batch: int, picazor_delay: float):
        super().__init__()
        self.url = url
        self.picazor_threads = picazor_threads
        self.picazor_batch = picazor_batch
        self.picazor_delay = picazor_delay
        self.stop_requested = False
        self.is_paused = False
        self._pause_event = threading.Event()
        self._pause_event.set()

    def _wait_if_paused(self) -> bool:
        while not self._pause_event.is_set():
            if self.stop_requested:
                return False
            self._pause_event.wait(0.1)
        return not self.stop_requested

    def run(self):
        try:
            if not self.url.strip():
                self.error.emit("URL vazia!")
                return

            if "picazor.com" in self.url:
                print("[FetchWorker] Detected Picazor link. Starting analysis...")
                from core.picazor_client import PicazorClient

                client = PicazorClient(delay=self.picazor_delay)
                if self.stop_requested:
                    self.error.emit("Analise cancelada")
                    return

                def progress_wrapper(count: int):
                    if not self._wait_if_paused():
                        return
                    self.progress.emit(count)

                valid_indices = client.get_valid_indices_multithread(
                    self.url,
                    num_threads=self.picazor_threads,
                    batch_size=self.picazor_batch,
                    progress_callback=progress_wrapper,
                )
                total_files = len(valid_indices)
                print(f"[FetchWorker] Media found: {total_files} files")
            elif "leakgallery.com" in self.url:
                print("[FetchWorker] Detected Leakgallery link. Starting analysis...")
                from core.leakgallery_client import LeakgalleryClient

                client = LeakgalleryClient(delay=self.picazor_delay)
                if self.stop_requested:
                    self.error.emit("Analise cancelada")
                    return

                def progress_wrapper(count: int):
                    if not self._wait_if_paused():
                        return
                    self.progress.emit(count)

                parts = [p for p in self.url.split("/") if p]
                model = parts[-1] if parts else ""
                valid_indices = client.get_media_ids(model, progress_callback=progress_wrapper)
                total_files = len(valid_indices)
                print(f"[FetchWorker] Media found: {total_files} files")
            else:
                valid_indices = None
                total_files = get_fapello_total_files(self.url)

            parts = [p for p in self.url.split("/") if p]
            pasta = parts[-1] if parts else ""

            self.valid_indices = valid_indices

            self.finished.emit({
                "total": total_files,
                "pasta": pasta,
                "valid_indices": valid_indices,
            })
        except Exception as exc:
            if not self.stop_requested:
                self.error.emit(f"Erro ao buscar: {str(exc)}")

    def stop(self):
        self.stop_requested = True
        self._pause_event.set()

    def pause(self):
        self.is_paused = True
        self._pause_event.clear()

    def resume(self):
        self.is_paused = False
        self._pause_event.set()
class ThumbnailWorker(QThread):
    """Worker thread para gerar thumbnails de videos sem bloquear a UI."""

    thumbnail_ready = Signal(str, QIcon)

    def __init__(self, file_path: str, thumb_size: int = 220):
        super().__init__()
        self.file_path = file_path
        self.thumb_size = thumb_size

    def run(self):
        try:
            import cv2

            cap = cv2.VideoCapture(self.file_path)
            ret, frame = cap.read()
            cap.release()
            if ret:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                height, width, channel = frame.shape
                bytes_per_line = channel * width
                qimg = QImage(frame.data, width, height, bytes_per_line, QImage.Format_RGB888)
                pix = QPixmap.fromImage(qimg)
            else:
                pix = self._create_video_placeholder()
        except Exception:
            pix = self._create_video_placeholder()

        if pix.isNull():
            pix = self._create_video_placeholder()

        side = min(pix.width(), pix.height())
        x = (pix.width() - side) // 2
        y = (pix.height() - side) // 2
        pix = pix.copy(x, y, side, side)
        pix = pix.scaled(self.thumb_size, self.thumb_size, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        self.thumbnail_ready.emit(self.file_path, QIcon(pix))

    def _create_video_placeholder(self):
        pix = QPixmap(self.thumb_size, self.thumb_size)
        pix.fill(QColor("#1a1a1a"))
        painter = QPainter(pix)
        painter.setPen(QColor("#666666"))
        painter.setFont(QFont("Arial", 10))
        painter.drawText(pix.rect(), Qt.AlignCenter, ">\nVIDEO")
        painter.end()
        return pix


class DownloadWorker(QThread):
    """Worker thread para baixar arquivos sem bloquear a UI."""

    progress_update = Signal(dict)
    finished = Signal()
    error = Signal(str)

    def __init__(
        self,
        url: str,
        download_images: bool,
        download_videos: bool,
        total_files: int,
        target_dir: Path,
        valid_indices=None,
        picazor_threads: int = FIXED_PICAZOR_THREADS,
        picazor_batch: int = PICAZOR_CHECK_BATCH_DEFAULT,
        picazor_delay: float = FIXED_PICAZOR_DELAY,
    ):
        super().__init__()
        self.url = url
        self.download_images = download_images
        self.download_videos = download_videos
        self.total_files = total_files
        self.target_dir = target_dir
        self.valid_indices = valid_indices
        self.picazor_threads = picazor_threads
        self.picazor_batch = picazor_batch
        self.picazor_delay = picazor_delay
        self.processed_count = 0
        self.is_paused = False
        self.stop_requested = False

    def progress_callback(self, data):
        if data["type"] == "file_start":
            self.progress_update.emit({
                "type": "file_start",
                "filename": data["filename"],
                "index": data["index"],
            })
        elif data["type"] == "file_progress":
            self.progress_update.emit({
                "type": "file_progress",
                "filename": data.get("filename", ""),
                "index": data.get("index"),
                "bytes_downloaded": data.get("bytes_downloaded", 0),
                "total_bytes": data.get("total_bytes"),
            })
        elif data["type"] == "file_complete":
            success_count = data.get("success", 0)
            self.processed_count += 1
            progress_percent = int((self.processed_count / self.total_files) * 100) if self.total_files > 0 else 0
            self.progress_update.emit({
                "type": "file_complete",
                "filename": data["filename"],
                "index": data["index"],
                "count": success_count,
                "total": self.total_files,
                "percent": progress_percent,
                "processed": self.processed_count,
            })
        elif data["type"] == "file_skipped":
            self.processed_count += 1
            progress_percent = int((self.processed_count / self.total_files) * 100) if self.total_files > 0 else 0
            self.progress_update.emit({
                "type": "file_skipped",
                "index": data["index"],
                "reason": data["reason"],
                "filename": data.get("filename", ""),
                "percent": progress_percent,
                "processed": self.processed_count,
            })
        elif data["type"] == "file_error":
            self.processed_count += 1
            progress_percent = int((self.processed_count / self.total_files) * 100) if self.total_files > 0 else 0
            self.progress_update.emit({
                "type": "file_error",
                "filename": data["filename"],
                "error": data.get("error", ""),
                "success": data.get("success", 0),
                "failed": data.get("failed", 0),
                "percent": progress_percent,
                "processed": self.processed_count,
            })
        elif data["type"] == "summary":
            self.progress_update.emit({
                "type": "summary",
                "total_expected": data["total_expected"],
                "success": data["success"],
                "failed": data["failed"],
                "skipped": data["skipped"],
                "failed_indices": data["failed_indices"],
            })
        elif data["type"] == "status":
            self.progress_update.emit({
                "type": "status",
                "status": data["status"],
            })

    def run(self):
        try:
            download_orchestrator_with_progress(
                self.url,
                workers=self.picazor_threads if "picazor.com" in self.url else FIXED_FAPELLO_THREADS,
                progress_callback=self.progress_callback,
                target_dir=self.target_dir,
                download_images=self.download_images,
                download_videos=self.download_videos,
                worker=self,
                valid_indices=self.valid_indices,
                link_check_batch=self.picazor_batch,
                link_check_delay=self.picazor_delay,
                download_chunk_size=FIXED_DOWNLOAD_CHUNK_SIZE,
            )
            self.finished.emit()
        except Exception as exc:
            if not self.stop_requested:
                self.error.emit(f"Erro no download: {str(exc)}")

    def pause(self):
        self.is_paused = True

    def resume(self):
        self.is_paused = False

    def stop(self):
        self.stop_requested = True
