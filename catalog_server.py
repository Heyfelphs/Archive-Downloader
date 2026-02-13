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
from typing import Optional, Tuple, Dict, List, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta


DEFAULT_PORT = 8008
PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_UI_DIR = PROJECT_ROOT / "ui" / "catalog"
APPDATA_DIR = os.getenv("APPDATA")
if APPDATA_DIR:
    DEFAULT_MODELS_DIR = Path(APPDATA_DIR) / "Hey_Felphs Archive-Downloader"
else:
    DEFAULT_MODELS_DIR = Path.home() / "Hey_Felphs Archive-Downloader"

# Configurações de cache otimizadas
CACHE_TTL = 1800  # 30 minutos
CACHE_CLEANUP_INTERVAL = 300  # 5 minutos
MAX_CACHE_SIZE = 1000  # Máximo de entradas no cache
SCAN_CHUNK_SIZE = 500  # Processar arquivos em chunks durante scan

# Caches globais com estrutura melhorada
@dataclass
class CacheEntry:
    """Entrada de cache com timestamp"""
    data: Any
    timestamp: float
    
    def is_expired(self, ttl: int = CACHE_TTL) -> bool:
        return time.time() - self.timestamp > ttl

class CacheManager:
    """Gerenciador de cache thread-safe com limpeza automática"""
    def __init__(self, max_size: int = MAX_CACHE_SIZE, ttl: int = CACHE_TTL):
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
        self.max_size = max_size
        self.ttl = ttl
        self._last_cleanup = time.time()
    
    def get(self, key: str) -> Optional[Any]:
        """Obtém valor do cache se válido"""
        with self._lock:
            self._maybe_cleanup()
            entry = self._cache.get(key)
            if entry and not entry.is_expired(self.ttl):
                return entry.data
            elif entry:
                del self._cache[key]
            return None
    
    def set(self, key: str, value: Any) -> None:
        """Define valor no cache"""
        with self._lock:
            if len(self._cache) >= self.max_size:
                self._evict_oldest()
            self._cache[key] = CacheEntry(data=value, timestamp=time.time())
    
    def delete(self, key: str) -> None:
        """Remove entrada do cache"""
        with self._lock:
            self._cache.pop(key, None)
    
    def clear(self) -> None:
        """Limpa todo o cache"""
        with self._lock:
            self._cache.clear()
    
    def _maybe_cleanup(self) -> None:
        """Limpa entradas expiradas periodicamente"""
        now = time.time()
        if now - self._last_cleanup > CACHE_CLEANUP_INTERVAL:
            expired_keys = [k for k, v in self._cache.items() if v.is_expired(self.ttl)]
            for key in expired_keys:
                del self._cache[key]
            self._last_cleanup = now
    
    def _evict_oldest(self) -> None:
        """Remove a entrada mais antiga do cache"""
        if not self._cache:
            return
        oldest_key = min(self._cache.items(), key=lambda x: x[1].timestamp)[0]
        del self._cache[oldest_key]
    
    def get_stats(self) -> Dict[str, int]:
        """Retorna estatísticas do cache"""
        with self._lock:
            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "ttl": self.ttl
            }

# Instâncias de cache
models_cache = CacheManager(max_size=500, ttl=CACHE_TTL)
model_info_cache = CacheManager(max_size=2000, ttl=CACHE_TTL)
media_list_cache = CacheManager(max_size=1000, ttl=CACHE_TTL)

# Estado de scan de duplicatas
scan_progress = {"current": 0, "total": 0, "is_scanning": False}
scan_results = None
scan_lock = threading.Lock()
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
        if parsed.path == "/api/cache_stats":
            self._handle_cache_stats()
            return
        if parsed.path == "/api/search":
            self._handle_search(parsed.query)
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
        """Lista sites disponíveis com cache otimizado"""
        cache_key = "sites_list"
        cached = models_cache.get(cache_key)
        if cached is not None:
            self._send_json({"sites": cached})
            return

        sites = []
        if self.models_dir and self.models_dir.exists():
            # Usar os.scandir() é mais rápido que iterdir()
            with os.scandir(self.models_dir) as entries:
                for entry in entries:
                    if not entry.is_dir():
                        continue
                    # Contar modelos de forma otimizada
                    model_count = sum(1 for d in os.scandir(entry.path) if d.is_dir())
                    sites.append({"name": entry.name, "models": model_count})
        
        sites.sort(key=lambda x: x["name"])
        models_cache.set(cache_key, sites)
        self._send_json({"sites": sites})

    def _handle_models(self, query: str) -> None:
        """Lista modelos de um site com cache otimizado e paginação"""
        params = parse_qs(query)
        site = (params.get("site") or [""])[0].strip()
        safe_site = self._safe_site_name(site)
        if not safe_site:
            self._send_json({"models": [], "error": "invalid_site"}, status=400)
            return

        # Parâmetros de paginação
        try:
            page = int((params.get("page") or ["1"])[0])
            limit = int((params.get("limit") or ["0"])[0])  # 0 = sem limite
        except ValueError:
            page = 1
            limit = 0
        
        if page < 1:
            page = 1
        if limit < 0:
            limit = 0

        cache_key = f"models_{safe_site}"
        cached = models_cache.get(cache_key)
        if cached is not None:
            models = cached
        else:
            models = []
            if self.models_dir and self.models_dir.exists():
                site_dir = self.models_dir / safe_site
                if site_dir.exists() and site_dir.is_dir():
                    # Processar modelos em batch para melhor performance
                    with os.scandir(site_dir) as entries:
                        model_entries = [(e.name, e.path) for e in entries if e.is_dir()]
                    
                    model_entries.sort(key=lambda x: x[0])
                    
                    for model_name, model_path in model_entries:
                        thumb, img_count, vid_count = self._get_model_info_fast(Path(model_path))
                        models.append({
                            "name": model_name,
                            "thumb": thumb,
                            "image_count": img_count,
                            "video_count": vid_count,
                        })

            models_cache.set(cache_key, models)
        
        # Aplicar paginação
        total = len(models)
        if limit > 0:
            start = (page - 1) * limit
            end = start + limit
            models_page = models[start:end]
            total_pages = (total + limit - 1) // limit if limit > 0 else 1
        else:
            models_page = models
            total_pages = 1
        
        response = {
            "site": safe_site,
            "models": models_page,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "total_pages": total_pages
            }
        }
        self._send_json(response)

    def _handle_model(self, query: str) -> None:
        """Obtém detalhes de um modelo com cache de lista de mídia e lazy loading"""
        params = parse_qs(query)
        site = (params.get("site") or [""])[0].strip()
        model = (params.get("model") or [""])[0].strip()
        safe_site = self._safe_site_name(site)
        safe_model = self._safe_site_name(model)
        if not safe_site or not safe_model:
            self._send_json({"error": "invalid_params"}, status=400)
            return

        # Parâmetros de lazy loading
        try:
            images_limit = int((params.get("images_limit") or ["0"])[0])  # 0 = sem limite
            videos_limit = int((params.get("videos_limit") or ["0"])[0])  # 0 = sem limite
        except ValueError:
            images_limit = 0
            videos_limit = 0

        if not self.models_dir:
            self._send_json({"error": "models_dir_missing"}, status=404)
            return

        model_dir = self.models_dir / safe_site / safe_model
        if not model_dir.exists() or not model_dir.is_dir():
            self._send_json({"error": "model_not_found"}, status=404)
            return

        # Cache de lista de mídia
        cache_key = f"media_{safe_site}_{safe_model}"
        cached = media_list_cache.get(cache_key)
        
        if cached is not None:
            images, videos = cached
        else:
            images, videos = self._list_media_files_fast(model_dir)
            media_list_cache.set(cache_key, (images, videos))
        
        # Aplicar lazy loading
        total_images = len(images)
        total_videos = len(videos)
        
        if images_limit > 0:
            images = images[:images_limit]
        if videos_limit > 0:
            videos = videos[:videos_limit]
        
        self._send_json({
            "site": safe_site,
            "model": safe_model,
            "images": images,
            "videos": videos,
            "total_images": total_images,
            "total_videos": total_videos,
        })

    def _handle_media(self, path: str) -> None:
        """Serve arquivos de mídia com cache HTTP"""
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
        """Deleta um modelo e limpa caches relacionados"""
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

        # Limpar caches relacionados
        models_cache.delete(f"models_{safe_site}")
        media_list_cache.delete(f"media_{safe_site}_{safe_model}")
        models_cache.delete("sites_list")

        self._send_json({"status": "deleted"})

    def _handle_search(self, query: str) -> None:
        """Busca modelos por nome em todos os sites ou site específico"""
        params = parse_qs(query)
        search_query = (params.get("q") or [""])[0].strip().lower()
        site_filter = (params.get("site") or [""])[0].strip()
        
        if not search_query:
            self._send_json({"results": [], "error": "query_required"}, status=400)
            return
        
        if not self.models_dir or not self.models_dir.exists():
            self._send_json({"results": []}, status=200)
            return
        
        results = []
        
        # Determinar sites a buscar
        if site_filter:
            safe_site = self._safe_site_name(site_filter)
            if safe_site:
                sites_to_search = [safe_site]
            else:
                sites_to_search = []
        else:
            # Buscar em todos os sites
            with os.scandir(self.models_dir) as entries:
                sites_to_search = [e.name for e in entries if e.is_dir()]
        
        # Buscar modelos que correspondem à query
        for site in sites_to_search:
            site_dir = self.models_dir / site
            if not site_dir.exists() or not site_dir.is_dir():
                continue
            
            with os.scandir(site_dir) as entries:
                for entry in entries:
                    if not entry.is_dir():
                        continue
                    
                    # Verificar se o nome do modelo contém a query
                    if search_query in entry.name.lower():
                        # Obter informações do modelo
                        thumb, img_count, vid_count = self._get_model_info_fast(Path(entry.path))
                        results.append({
                            "site": site,
                            "name": entry.name,
                            "thumb": thumb,
                            "image_count": img_count,
                            "video_count": vid_count,
                        })
        
        # Ordenar resultados por relevância (modelos que começam com a query primeiro)
        results.sort(key=lambda x: (not x["name"].lower().startswith(search_query), x["name"].lower()))
        
        self._send_json({
            "query": search_query,
            "site": site_filter if site_filter else "all",
            "results": results,
            "total": len(results)
        })

    def _handle_delete_file(self) -> None:
        """Deleta um arquivo e limpa caches relacionados"""
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

        # Limpar caches relacionados
        models_cache.delete(f"models_{safe_site}")
        media_list_cache.delete(f"media_{safe_site}_{safe_model}")

        self._send_json({"status": "deleted"})

    def _handle_scan_duplicates(self) -> None:
        """Inicia verificação de duplicatas em thread separada com processamento otimizado"""
        global scan_progress, scan_results
        
        if not self.models_dir or not self.models_dir.exists():
            self._send_json({"error": "models_dir_missing"}, status=404)
            return
        
        # Se já está executando, retornar erro
        with scan_lock:
            if scan_progress["is_scanning"]:
                self._send_json({"error": "scan_in_progress"}, status=409)
                return
        
        # Iniciar scan em thread separada
        scan_thread = threading.Thread(
            target=self._run_scan_duplicates_optimized,
            daemon=True
        )
        scan_thread.start()
        
        # Retornar resposta imediata
        self._send_json({"status": "started", "message": "Scan iniciado com processamento otimizado"})
    
    def _run_scan_duplicates_optimized(self) -> None:
        """Executa scan de duplicatas otimizado com processamento em chunks"""
        global scan_progress, scan_results
        
        print("[INFO] Iniciando scan de duplicatas otimizado...")
        
        if not self.models_dir:
            print("[ERROR] models_dir não está definido")
            return
        
        valid_extensions = {
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp',
            '.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.m4v'
        }

        # Carregar cache existente
        hash_cache = self._load_hash_cache()
        cache_hits = 0
        cache_misses = 0

        with scan_lock:
            scan_progress["is_scanning"] = True
            scan_progress["current"] = 0
            scan_progress["total"] = 0
            scan_results = None
        
        # Coletar lista de arquivos primeiro (mais rápido)
        print("[INFO] Coletando lista de arquivos...")
        files_to_process = []
        
        for root, _, files in os.walk(self.models_dir):
            for filename in files:
                file_extension = os.path.splitext(filename)[1].lower()
                if file_extension in valid_extensions:
                    file_path = os.path.join(root, filename)
                    rel_path = os.path.relpath(file_path, self.models_dir)
                    files_to_process.append((file_path, rel_path))
        
        total_files = len(files_to_process)
        with scan_lock:
            scan_progress["total"] = total_files
        
        print(f"[INFO] Total de arquivos a processar: {total_files}")
        
        # Processar em chunks para melhor performance
        hashes = defaultdict(list)
        new_cache = {}
        files_checked = 0
        chunk_size = SCAN_CHUNK_SIZE
        
        for i in range(0, total_files, chunk_size):
            chunk = files_to_process[i:i + chunk_size]
            
            for file_path, rel_path in chunk:
                # Verificar cache primeiro
                file_hash = self._get_cached_hash(file_path, rel_path, hash_cache)
                
                if file_hash and rel_path in hash_cache:
                    # Cache hit
                    cache_hits += 1
                    new_cache[rel_path] = hash_cache[rel_path]
                else:
                    # Cache miss - calcular hash
                    file_hash = self._calculate_md5_fast(file_path)
                    cache_misses += 1
                    
                    if file_hash:
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
                    
                    with scan_lock:
                        scan_progress["current"] = files_checked
            
            # Log a cada chunk processado
            if (i // chunk_size + 1) % 5 == 0:
                print(f"[INFO] Progresso: {files_checked}/{total_files} arquivos ({(files_checked/total_files*100):.1f}%)")

        # Identificar duplicatas
        duplicates = {k: v for k, v in hashes.items() if len(v) > 1}
        
        duplicate_groups = []
        total_size_waste = 0
        
        for file_hash, file_list in duplicates.items():
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
        
        # Ordenar por desperdício (maior primeiro)
        duplicate_groups.sort(key=lambda x: x["waste"], reverse=True)
        
        with scan_lock:
            scan_progress["is_scanning"] = False
        
        print(f"[INFO] Scan finalizado!")
        print(f"  - Arquivos processados: {files_checked}")
        print(f"  - Grupos duplicados: {len(duplicates)}")
        print(f"  - Espaço desperdiçado: {self._format_bytes(total_size_waste)}")
        print(f"  - Taxa de cache hit: {(cache_hits/(cache_hits+cache_misses)*100):.1f}%" if (cache_hits+cache_misses) > 0 else "N/A")
        
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
        """Retorna o progresso atual do scan"""
        global scan_progress, scan_results
        
        with scan_lock:
            response = dict(scan_progress)
            
            if not scan_progress["is_scanning"] and scan_results is not None:
                response["completed"] = True
                response["results"] = scan_results
                print(f"[DEBUG] Sending completed results: {len(scan_results.get('duplicates', []))} groups")
            else:
                response["completed"] = False
                if scan_progress["is_scanning"]:
                    print(f"[DEBUG] Scanning in progress: {scan_progress['current']}/{scan_progress['total']}")
        
        self._send_json(response)
    
    def _handle_clear_cache(self) -> None:
        """Limpa todos os caches (hash e memória)"""
        if not self.models_dir:
            self._send_json({"error": "models_dir_missing"}, status=404)
            return
        
        # Limpar cache de hash em disco
        cache_file = self.models_dir / HASH_CACHE_FILE
        hash_cleared = False
        
        try:
            if cache_file.exists():
                cache_file.unlink()
                hash_cleared = True
        except Exception as e:
            self._send_json({"error": "clear_failed", "message": str(e)}, status=500)
            return
        
        # Limpar caches em memória
        models_cache.clear()
        model_info_cache.clear()
        media_list_cache.clear()
        
        self._send_json({
            "status": "cleared",
            "hash_cache": "cleared" if hash_cleared else "empty",
            "memory_caches": "cleared",
            "message": "Todos os caches foram limpos com sucesso"
        })
    
    def _handle_cache_stats(self) -> None:
        """Retorna estatísticas dos caches"""
        stats = {
            "models_cache": models_cache.get_stats(),
            "model_info_cache": model_info_cache.get_stats(),
            "media_list_cache": media_list_cache.get_stats(),
        }
        self._send_json(stats)
    
    def _handle_delete_duplicate(self) -> None:
        """Deleta um arquivo duplicado"""
        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length > 0 else b"{}"
            payload = json.loads(raw.decode("utf-8"))
        except Exception as e:
            print(f"[ERROR] Erro ao parsear JSON: {e}")
            self._send_json({"error": "invalid_json"}, status=400)
            return

        rel_path = str(payload.get("path", "")).strip()
        if not rel_path:
            self._send_json({"error": "invalid_params"}, status=400)
            return

        if not self.models_dir:
            self._send_json({"error": "models_dir_missing"}, status=404)
            return

        # Construir e validar caminho
        file_path = self.models_dir / rel_path
        
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
            print(f"[INFO] Arquivo deletado: {rel_path}")
            
            # Remover do cache de hashes
            hash_cache = self._load_hash_cache()
            if rel_path in hash_cache:
                del hash_cache[rel_path]
                self._save_hash_cache(hash_cache)
            
            self._send_json({"status": "deleted", "path": rel_path})
        except Exception as e:
            print(f"[ERROR] Erro ao deletar: {e}")
            self._send_json({"error": "delete_failed", "message": str(e)}, status=500)

    def _load_hash_cache(self) -> dict:
        """Carrega cache de hashes do disco"""
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
        """Salva cache de hashes no disco"""
        if not self.models_dir:
            return
        
        cache_file = self.models_dir / HASH_CACHE_FILE
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[ERROR] Erro ao salvar cache: {e}")
    
    def _get_cached_hash(self, file_path: str, rel_path: str, cache: dict) -> str | None:
        """Obtém hash do cache se válido"""
        if rel_path not in cache:
            return None
        
        cached_data = cache[rel_path]
        if not isinstance(cached_data, dict) or "hash" not in cached_data:
            return None
        
        try:
            stats = os.stat(file_path)
            cached_size = cached_data.get("size")
            cached_mtime = cached_data.get("mtime")
            
            # Validar se arquivo não mudou
            if cached_size != stats.st_size or cached_mtime != stats.st_mtime:
                return None
            
            return cached_data["hash"]
        except Exception:
            return None
    
    @staticmethod
    def _calculate_md5_fast(file_path: str, block_size: int = 131072) -> str | None:
        """Calcula MD5 com buffer otimizado (128KB)"""
        md5 = hashlib.md5()
        try:
            with open(file_path, 'rb') as f:
                for block in iter(lambda: f.read(block_size), b''):
                    md5.update(block)
            return md5.hexdigest()
        except Exception:
            return None

    def _send_json(self, data: dict, status: int = 200) -> None:
        """Envia resposta JSON com compressão gzip se apropriado"""
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        
        # Comprimir se cliente aceitar e payload > 1KB
        accept_encoding = self.headers.get('Accept-Encoding', '')
        if 'gzip' in accept_encoding and len(payload) > 1024:
            payload = gzip.compress(payload, compresslevel=6)
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Encoding", "gzip")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "public, max-age=300")
        else:
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "public, max-age=300")
        
        self.end_headers()
        self.wfile.write(payload)

    def _send_file(self, file_path: Path) -> None:
        """Envia arquivo com cache HTTP e streaming"""
        try:
            fs = file_path.stat()
            self.send_response(200)
            self.send_header("Content-Length", str(fs.st_size))
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Cache-Control", "public, max-age=86400")  # 24h
            self.end_headers()
            
            # Streaming em chunks de 64KB
            with file_path.open("rb") as handle:
                while chunk := handle.read(65536):
                    self.wfile.write(chunk)
        except Exception:
            self.send_error(404, "File not found")

    @staticmethod
    def _safe_site_name(site: str) -> str | None:
        """Valida nome de site/modelo para segurança"""
        if not site or site in {".", ".."}:
            return None
        if "/" in site or "\\" in site:
            return None
        if os.path.sep in site or (os.path.altsep and os.path.altsep in site):
            return None
        if Path(site).name != site:
            return None
        return site

    def _get_model_info_fast(self, model_dir: Path) -> Tuple[Optional[str], int, int]:
        """Obtém informações do modelo com cache otimizado"""
        cache_key = str(model_dir)
        cached = model_info_cache.get(cache_key)
        if cached is not None:
            return cached
        
        image_exts = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
        video_exts = {".mp4", ".webm", ".mov", ".mkv"}
        images: list[str] = []
        videos: list[str] = []
        
        try:
            # os.scandir() é mais rápido que iterdir()
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
        model_info_cache.set(cache_key, result)
        return result

    @staticmethod
    def _list_media_files_fast(model_dir: Path) -> Tuple[List[str], List[str]]:
        """Lista arquivos de mídia com performance otimizada"""
        image_exts = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
        video_exts = {".mp4", ".webm", ".mov", ".mkv"}
        images: list[str] = []
        videos: list[str] = []
        
        try:
            # Usar os.scandir() é mais rápido
            with os.scandir(model_dir) as entries:
                for entry in entries:
                    if not entry.is_file():
                        continue
                    ext = os.path.splitext(entry.name)[1].lower()
                    if ext in image_exts:
                        images.append(entry.name)
                    elif ext in video_exts:
                        videos.append(entry.name)
            
            # Ordenar apenas no final
            images.sort()
            videos.sort()
        except Exception:
            return [], []
        
        return images, videos
    
    @staticmethod
    def _format_bytes(bytes_size: int) -> str:
        """Formata bytes em formato legível"""
        size_float = float(bytes_size)
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_float < 1024.0:
                return f"{size_float:.2f} {unit}"
            size_float /= 1024.0
        return f"{size_float:.2f} PB"


def run_server(port: int, directory: Path, models_dir: Path) -> None:
    """Inicia o servidor com thread pool"""
    handler = functools.partial(
        CatalogRequestHandler,
        directory=str(directory),
        models_dir=models_dir,
    )
    with socketserver.ThreadingTCPServer(("", port), handler) as httpd:
        httpd.daemon_threads = True  # Threads daemon para melhor cleanup
        print(f"╔═══════════════════════════════════════════════════╗")
        print(f"║  Catalog Server - Otimizado                       ║")
        print(f"╠═══════════════════════════════════════════════════╣")
        print(f"║  URL: http://localhost:{port:<30} ║")
        print(f"║  Models Dir: {str(models_dir)[:36]:<36}║")
        print(f"╚═══════════════════════════════════════════════════╝")
        print(f"\n[INFO] Servidor rodando. Pressione Ctrl+C para parar.\n")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[INFO] Servidor encerrado.")


def parse_args() -> argparse.Namespace:
    """Parse argumentos da linha de comando"""
    parser = argparse.ArgumentParser(
        description="Serve the catalog UI as a standalone site (Optimized)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"Port to bind the server (default: {DEFAULT_PORT})"
    )
    parser.add_argument(
        "--dir",
        type=Path,
        default=DEFAULT_UI_DIR,
        help="Directory to serve"
    )
    parser.add_argument(
        "--models-dir",
        type=Path,
        default=DEFAULT_MODELS_DIR,
        help="Directory with downloaded models grouped by site"
    )
    return parser.parse_args()


def main() -> None:
    """Ponto de entrada principal"""
    args = parse_args()
    directory = args.dir.resolve()
    models_dir = args.models_dir.resolve()
    
    if not directory.exists() or not directory.is_dir():
        raise SystemExit(f"❌ Catalog directory not found: {directory}")
    
    run_server(args.port, directory, models_dir)


if __name__ == "__main__":
    main()
