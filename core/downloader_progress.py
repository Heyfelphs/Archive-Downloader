"""Backward-compatible wrapper for the download service."""

from core.services.download_service import (
    download_orchestrator_with_progress,
    download_worker_with_progress,
)

__all__ = [
    "download_orchestrator_with_progress",
    "download_worker_with_progress",
]
