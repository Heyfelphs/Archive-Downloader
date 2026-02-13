import argparse
import functools
import http.server
import json
import os
import random
import shutil
import socketserver
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse


DEFAULT_PORT = 8008
PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_UI_DIR = PROJECT_ROOT / "ui" / "catalog"
APPDATA_DIR = os.getenv("APPDATA")
if APPDATA_DIR:
    DEFAULT_MODELS_DIR = Path(APPDATA_DIR) / "Hey_Felphs Archive-Downloader"
else:
    DEFAULT_MODELS_DIR = Path.home() / "Hey_Felphs Archive-Downloader"

CACHE_TTL = 300  # 5 minutes
models_cache = {}


class CatalogRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, directory: str | None = None, models_dir: Path | None = None, **kwargs):
        self.models_dir = models_dir
        super().__init__(*args, directory=directory, **kwargs)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/sites":
            self._handle_sites()
            return
        if parsed.path == "/api/models":
            self._handle_models(parsed.query)
            return
        if parsed.path == "/api/model":
            self._handle_model(parsed.query)
            return
        if parsed.path.startswith("/media/"):
            self._handle_media(parsed.path)
            return
        super().do_GET()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/delete_model":
            self._handle_delete_model()
            return
        if parsed.path == "/api/delete_file":
            self._handle_delete_file()
            return
        self.send_error(404, "Not found")

    def _handle_sites(self) -> None:
        sites = []
        if self.models_dir and self.models_dir.exists():
            for site_dir in sorted(self.models_dir.iterdir()):
                if not site_dir.is_dir():
                    continue
                model_count = sum(1 for d in site_dir.iterdir() if d.is_dir())
                sites.append({"name": site_dir.name, "models": model_count})

        payload = json.dumps({"sites": sites}, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _handle_models(self, query: str) -> None:
        params = parse_qs(query)
        site = (params.get("site") or [""])[0].strip()
        safe_site = self._safe_site_name(site)
        if not safe_site:
            self._send_json({"models": [], "error": "invalid_site"}, status=400)
            return

        cache_key = f"models_{safe_site}"
        now = time.time()
        if cache_key in models_cache:
            cached_data, cached_time = models_cache[cache_key]
            if now - cached_time < CACHE_TTL:
                self._send_json({"site": safe_site, "models": cached_data})
                return

        models = []
        if self.models_dir and self.models_dir.exists():
            site_dir = self.models_dir / safe_site
            if site_dir.exists() and site_dir.is_dir():
                for model_dir in sorted(site_dir.iterdir()):
                    if not model_dir.is_dir():
                        continue
                    thumb, img_count, vid_count = self._get_model_info(model_dir)
                    models.append({
                        "name": model_dir.name,
                        "thumb": thumb,
                        "image_count": img_count,
                        "video_count": vid_count,
                    })

        models_cache[cache_key] = (models, now)
        self._send_json({"site": safe_site, "models": models})

    def _handle_model(self, query: str) -> None:
        params = parse_qs(query)
        site = (params.get("site") or [""])[0].strip()
        model = (params.get("model") or [""])[0].strip()
        safe_site = self._safe_site_name(site)
        safe_model = self._safe_site_name(model)
        if not safe_site or not safe_model:
            self._send_json({"error": "invalid_params"}, status=400)
            return

        if not self.models_dir:
            self._send_json({"error": "models_dir_missing"}, status=404)
            return

        model_dir = self.models_dir / safe_site / safe_model
        if not model_dir.exists() or not model_dir.is_dir():
            self._send_json({"error": "model_not_found"}, status=404)
            return

        images, videos = self._list_media_files(model_dir)
        self._send_json({
            "site": safe_site,
            "model": safe_model,
            "images": images,
            "videos": videos,
        })

    def _handle_media(self, path: str) -> None:
        parts = path.split("/")
        if len(parts) < 5:
            self.send_error(404, "File not found")
            return

        _, _, site, model, filename = parts[0:5]
        safe_site = self._safe_site_name(site)
        safe_model = self._safe_site_name(model)
        safe_file = Path(filename).name
        if not safe_site or not safe_model or not safe_file:
            self.send_error(404, "File not found")
            return

        if not self.models_dir:
            self.send_error(404, "File not found")
            return

        file_path = self.models_dir / safe_site / safe_model / safe_file
        if not file_path.exists() or not file_path.is_file():
            self.send_error(404, "File not found")
            return

        self._send_file(file_path)

    def _handle_delete_model(self) -> None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length > 0 else b"{}"
            payload = json.loads(raw.decode("utf-8"))
        except Exception:
            self._send_json({"error": "invalid_json"}, status=400)
            return

        site = str(payload.get("site", "")).strip()
        model = str(payload.get("model", "")).strip()
        safe_site = self._safe_site_name(site)
        safe_model = self._safe_site_name(model)
        if not safe_site or not safe_model:
            self._send_json({"error": "invalid_params"}, status=400)
            return

        if not self.models_dir:
            self._send_json({"error": "models_dir_missing"}, status=404)
            return

        model_dir = self.models_dir / safe_site / safe_model
        if not model_dir.exists() or not model_dir.is_dir():
            self._send_json({"error": "model_not_found"}, status=404)
            return

        try:
            shutil.rmtree(model_dir)
        except Exception:
            self._send_json({"error": "delete_failed"}, status=500)
            return

        cache_key = f"models_{safe_site}"
        if cache_key in models_cache:
            models_cache.pop(cache_key, None)

        self._send_json({"status": "deleted"})

    def _handle_delete_file(self) -> None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length > 0 else b"{}"
            payload = json.loads(raw.decode("utf-8"))
        except Exception:
            self._send_json({"error": "invalid_json"}, status=400)
            return

        site = str(payload.get("site", "")).strip()
        model = str(payload.get("model", "")).strip()
        filename = str(payload.get("file", "")).strip()
        safe_site = self._safe_site_name(site)
        safe_model = self._safe_site_name(model)
        safe_file = Path(filename).name
        if not safe_site or not safe_model or not safe_file:
            self._send_json({"error": "invalid_params"}, status=400)
            return

        if not self.models_dir:
            self._send_json({"error": "models_dir_missing"}, status=404)
            return

        file_path = self.models_dir / safe_site / safe_model / safe_file
        if not file_path.exists() or not file_path.is_file():
            self._send_json({"error": "file_not_found"}, status=404)
            return

        try:
            file_path.unlink()
        except Exception:
            self._send_json({"error": "delete_failed"}, status=500)
            return

        cache_key = f"models_{safe_site}"
        if cache_key in models_cache:
            models_cache.pop(cache_key, None)

        self._send_json({"status": "deleted"})

    def _send_json(self, data: dict, status: int = 200) -> None:
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _send_file(self, file_path: Path) -> None:
        try:
            with file_path.open("rb") as handle:
                fs = file_path.stat()
                self.send_response(200)
                self.send_header("Content-Length", str(fs.st_size))
                self.send_header("Content-Type", "application/octet-stream")
                self.end_headers()
                self.wfile.write(handle.read())
        except Exception:
            self.send_error(404, "File not found")

    @staticmethod
    def _safe_site_name(site: str) -> str | None:
        if not site or site in {".", ".."}:
            return None
        if "/" in site or "\\" in site:
            return None
        if os.path.sep in site or (os.path.altsep and os.path.altsep in site):
            return None
        if Path(site).name != site:
            return None
        return site

    @staticmethod
    def _get_model_info(model_dir: Path) -> tuple[str | None, int, int]:
        image_exts = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
        video_exts = {".mp4", ".webm", ".mov", ".mkv"}
        images: list[str] = []
        videos: list[str] = []
        try:
            for item in model_dir.iterdir():
                if not item.is_file():
                    continue
                ext = item.suffix.lower()
                if ext in image_exts:
                    images.append(item.name)
                elif ext in video_exts:
                    videos.append(item.name)
        except Exception:
            return None, 0, 0
        
        thumb = random.choice(images) if images else None
        return thumb, len(images), len(videos)

    @staticmethod
    def _list_media_files(model_dir: Path) -> tuple[list[str], list[str]]:
        image_exts = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
        video_exts = {".mp4", ".webm", ".mov", ".mkv"}
        images: list[str] = []
        videos: list[str] = []
        try:
            for item in sorted(model_dir.iterdir()):
                if not item.is_file():
                    continue
                ext = item.suffix.lower()
                if ext in image_exts:
                    images.append(item.name)
                elif ext in video_exts:
                    videos.append(item.name)
        except Exception:
            return [], []
        return images, videos


def run_server(port: int, directory: Path, models_dir: Path) -> None:
    handler = functools.partial(
        CatalogRequestHandler,
        directory=str(directory),
        models_dir=models_dir,
    )
    with socketserver.ThreadingTCPServer(("", port), handler) as httpd:
        print(f"Catalog server running on http://localhost:{port}")
        httpd.serve_forever()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Serve the catalog UI as a standalone site")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Port to bind the server")
    parser.add_argument(
        "--dir",
        type=Path,
        default=DEFAULT_UI_DIR,
        help="Directory to serve",
    )
    parser.add_argument(
        "--models-dir",
        type=Path,
        default=DEFAULT_MODELS_DIR,
        help="Directory with downloaded models grouped by site",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    directory = args.dir.resolve()
    models_dir = args.models_dir.resolve()
    if not directory.exists() or not directory.is_dir():
        raise SystemExit(f"Catalog directory not found: {directory}")
    run_server(args.port, directory, models_dir)


if __name__ == "__main__":
    main()
