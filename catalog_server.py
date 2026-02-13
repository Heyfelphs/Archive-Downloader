import argparse
import functools
import gzip
import hashlib
import http.server
import json
import os
import random
import shutil
import socketserver
import threading
import time
from collections import defaultdict
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

CACHE_TTL = 1800  # 30 minutes
models_cache = {}
model_info_cache = {}  # Cache para _get_model_info
scan_progress = {"current": 0, "total": 0, "is_scanning": False}
scan_results = None
HASH_CACHE_FILE = "duplicates_cache.json"


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
        if parsed.path == "/api/scan_duplicates":
            self._handle_scan_duplicates()
            return
        if parsed.path == "/api/scan_progress":
            self._handle_scan_progress()
            return
        if parsed.path == "/api/clear_cache":
            self._handle_clear_cache()
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
        if parsed.path == "/api/delete_duplicate":
            self._handle_delete_duplicate()
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

        self._send_json({"sites": sites})

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

    def _handle_scan_duplicates(self) -> None:
        """Inicia verificação de duplicatas em thread separada."""
        global scan_progress, scan_results
        
        if not self.models_dir or not self.models_dir.exists():
            self._send_json({"error": "models_dir_missing"}, status=404)
            return
        
        # Se já está executando, retornar erro
        if scan_progress["is_scanning"]:
            self._send_json({"error": "scan_in_progress"}, status=409)
            return
        
        # Iniciar scan em thread separada
        scan_thread = threading.Thread(target=self._run_scan_duplicates, daemon=True)
        scan_thread.start()
        
        # Retornar resposta imediata
        self._send_json({"status": "started", "message": "Scan iniciado"})
    
    def _run_scan_duplicates(self) -> None:
        """Executa o scan de duplicatas (roda em thread separada)."""
        global scan_progress, scan_results
        
        print("[DEBUG] Iniciando scan de duplicatas...")  # Debug
        
        valid_extensions = {
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp',
            '.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.m4v'
        }

        # Carregar cache existente
        hash_cache = self._load_hash_cache()
        cache_hits = 0
        cache_misses = 0

        # Primeiro, contar total de arquivos
        scan_progress["is_scanning"] = True
        scan_progress["current"] = 0
        scan_progress["total"] = 0
        scan_results = None
        
        print("[DEBUG] Contando arquivos totais...")  # Debug
        for root, _, files in os.walk(self.models_dir):
            for filename in files:
                file_extension = os.path.splitext(filename)[1].lower()
                if file_extension in valid_extensions:
                    scan_progress["total"] += 1
        
        print(f"[DEBUG] Total de arquivos a processar: {scan_progress['total']}")  # Debug
        
        # Agora processar os arquivos
        hashes = defaultdict(list)
        new_cache = {}
        files_checked = 0

        for root, _, files in os.walk(self.models_dir):
            for filename in files:
                file_extension = os.path.splitext(filename)[1].lower()
                
                if file_extension in valid_extensions:
                    file_path = os.path.join(root, filename)
                    rel_path = os.path.relpath(file_path, self.models_dir)
                    
                    # Tentar obter hash do cache
                    file_hash = self._get_cached_hash(file_path, rel_path, hash_cache)
                    
                    if file_hash and rel_path in hash_cache:
                        # Cache hit - usar hash existente
                        cache_hits += 1
                        new_cache[rel_path] = hash_cache[rel_path]
                    else:
                        # Cache miss - calcular novo hash
                        file_hash = self._calculate_md5(file_path)
                        cache_misses += 1
                        
                        if file_hash:
                            # Adicionar ao novo cache
                            try:
                                stats = os.stat(file_path)
                                new_cache[rel_path] = {
                                    "hash": file_hash,
                                    "size": stats.st_size,
                                    "mtime": stats.st_mtime
                                }
                            except Exception:
                                pass
                    
                    if file_hash:
                        hashes[file_hash].append(rel_path)
                        files_checked += 1
                        scan_progress["current"] = files_checked
                        
                        # Log a cada 100 arquivos
                        if files_checked % 100 == 0:
                            print(f"[DEBUG] Progresso: {files_checked}/{scan_progress['total']}")

        duplicates = {k: v for k, v in hashes.items() if len(v) > 1}
        
        duplicate_groups = []
        total_size_waste = 0
        
        for file_hash, file_list in duplicates.items():
            # Pegar tamanho do primeiro arquivo
            first_file = self.models_dir / file_list[0]
            if first_file.exists():
                file_size = first_file.stat().st_size
                waste = file_size * (len(file_list) - 1)
                total_size_waste += waste
            else:
                file_size = 0
                waste = 0
            
            duplicate_groups.append({
                "hash": file_hash,
                "count": len(file_list),
                "files": file_list,
                "size": file_size,
                "waste": waste
            })
        
        scan_progress["is_scanning"] = False
        
        print(f"[DEBUG] Scan finalizado. Arquivos: {files_checked}, Grupos duplicados: {len(duplicates)}")  # Debug
        
        # Salvar cache atualizado
        self._save_hash_cache(new_cache)
        
        # Armazenar resultados
        scan_results = {
            "total_files": files_checked,
            "duplicate_groups": len(duplicates),
            "total_waste_bytes": total_size_waste,
            "duplicates": duplicate_groups,
            "cache_stats": {
                "hits": cache_hits,
                "misses": cache_misses,
                "hit_rate": round((cache_hits / (cache_hits + cache_misses) * 100) if (cache_hits + cache_misses) > 0 else 0, 1)
            }
        }

    def _handle_scan_progress(self) -> None:
        """Retorna o progresso atual do scan e resultados se disponível."""
        global scan_progress, scan_results
        
        response = dict(scan_progress)
        
        # Se o scan terminou e temos resultados, incluir nos dados
        if not scan_progress["is_scanning"] and scan_results is not None:
            response["completed"] = True
            response["results"] = scan_results
        else:
            response["completed"] = False
        
        self._send_json(response)
    
    def _handle_clear_cache(self) -> None:
        """Limpa o arquivo de cache de hashes."""
        if not self.models_dir:
            self._send_json({"error": "models_dir_missing"}, status=404)
            return
        
        cache_file = self.models_dir / HASH_CACHE_FILE
        try:
            if cache_file.exists():
                cache_file.unlink()
                self._send_json({"status": "cleared", "message": "Cache limpo com sucesso"})
            else:
                self._send_json({"status": "empty", "message": "Cache já estava vazio"})
        except Exception as e:
            self._send_json({"error": "clear_failed", "message": str(e)}, status=500)
    
    def _handle_delete_duplicate(self) -> None:
        """Deleta um arquivo duplicado pelo caminho relativo."""
        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length > 0 else b"{}"
            payload = json.loads(raw.decode("utf-8"))
        except Exception as e:
            print(f"[DEBUG] Erro ao parsear JSON: {e}")  # Debug
            self._send_json({"error": "invalid_json"}, status=400)
            return

        rel_path = str(payload.get("path", "")).strip()
        print(f"[DEBUG] Tentando deletar: {rel_path}")  # Debug
        if not rel_path:
            self._send_json({"error": "invalid_params"}, status=400)
            return

        if not self.models_dir:
            self._send_json({"error": "models_dir_missing"}, status=404)
            return

        # Construir caminho absoluto e validar
        file_path = self.models_dir / rel_path
        
        # Verificar se o arquivo está dentro do models_dir (segurança)
        try:
            file_path = file_path.resolve()
            if not str(file_path).startswith(str(self.models_dir.resolve())):
                self._send_json({"error": "invalid_path"}, status=400)
                return
        except Exception:
            self._send_json({"error": "invalid_path"}, status=400)
            return

        if not file_path.exists() or not file_path.is_file():
            self._send_json({"error": "file_not_found"}, status=404)
            return

        try:
            file_path.unlink()
            print(f"[DEBUG] Arquivo deletado com sucesso: {file_path}")  # Debug
            
            # Remover do cache de hashes
            hash_cache = self._load_hash_cache()
            if rel_path in hash_cache:
                del hash_cache[rel_path]
                self._save_hash_cache(hash_cache)
            
            self._send_json({"status": "deleted", "path": rel_path})
        except Exception as e:
            print(f"[DEBUG] Erro ao deletar arquivo: {e}")  # Debug
            self._send_json({"error": "delete_failed", "message": str(e)}, status=500)

    def _load_hash_cache(self) -> dict:
        """Carrega o cache de hashes do arquivo JSON."""
        if not self.models_dir:
            return {}
        
        cache_file = self.models_dir / HASH_CACHE_FILE
        if not cache_file.exists():
            return {}
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    
    def _save_hash_cache(self, cache: dict) -> None:
        """Salva o cache de hashes no arquivo JSON."""
        if not self.models_dir:
            return
        
        cache_file = self.models_dir / HASH_CACHE_FILE
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Erro ao salvar cache: {e}")
    
    def _get_cached_hash(self, file_path: str, rel_path: str, cache: dict) -> str | None:
        """Obtém hash do cache se o arquivo não mudou."""
        if rel_path not in cache:
            return None
        
        cached_data = cache[rel_path]
        if not isinstance(cached_data, dict) or "hash" not in cached_data:
            return None
        
        try:
            # Verificar se arquivo ainda existe e não mudou
            stats = os.stat(file_path)
            cached_size = cached_data.get("size")
            cached_mtime = cached_data.get("mtime")
            
            # Se tamanho ou data de modificação mudaram, invalidar cache
            if cached_size != stats.st_size or cached_mtime != stats.st_mtime:
                return None
            
            return cached_data["hash"]
        except Exception:
            return None
    
    @staticmethod
    def _calculate_md5(file_path: str, block_size: int = 65536) -> str | None:
        """Calcula o hash MD5 de um arquivo."""
        md5 = hashlib.md5()
        try:
            with open(file_path, 'rb') as f:
                for block in iter(lambda: f.read(block_size), b''):
                    md5.update(block)
            return md5.hexdigest()
        except Exception:
            return None

    def _send_json(self, data: dict, status: int = 200) -> None:
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        
        # Comprimir se o cliente aceitar e payload for grande (>1KB)
        accept_encoding = self.headers.get('Accept-Encoding', '')
        if 'gzip' in accept_encoding and len(payload) > 1024:
            payload = gzip.compress(payload, compresslevel=6)
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Encoding", "gzip")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "public, max-age=300")  # 5 min cache
        else:
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "public, max-age=300")
        
        self.end_headers()
        self.wfile.write(payload)

    def _send_file(self, file_path: Path) -> None:
        try:
            fs = file_path.stat()
            # Adicionar cache headers para arquivos de mídia
            self.send_response(200)
            self.send_header("Content-Length", str(fs.st_size))
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Cache-Control", "public, max-age=86400")  # 24h cache
            self.end_headers()
            
            # Enviar arquivo em chunks para economizar memória
            with file_path.open("rb") as handle:
                while chunk := handle.read(65536):  # 64KB chunks
                    self.wfile.write(chunk)
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
        global model_info_cache
        # Check cache primeiro
        cache_key = str(model_dir)
        now = time.time()
        if cache_key in model_info_cache:
            cached_data, cached_time = model_info_cache[cache_key]
            if now - cached_time < CACHE_TTL:
                return cached_data
        
        image_exts = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
        video_exts = {".mp4", ".webm", ".mov", ".mkv"}
        images: list[str] = []
        videos: list[str] = []
        try:
            # Usar os.scandir() é mais rápido que iterdir()
            with os.scandir(model_dir) as entries:
                for entry in entries:
                    if not entry.is_file():
                        continue
                    ext = os.path.splitext(entry.name)[1].lower()
                    if ext in image_exts:
                        images.append(entry.name)
                    elif ext in video_exts:
                        videos.append(entry.name)
        except Exception:
            return None, 0, 0
        
        thumb = random.choice(images) if images else None
        result = (thumb, len(images), len(videos))
        model_info_cache[cache_key] = (result, now)
        return result

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
