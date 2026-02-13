import os
import hashlib
import argparse
import json
import time
from collections import defaultdict

# Cache global para armazenar hashes de arquivos
_hash_cache = {}
_cache_file = ".duplicate_cache.json"
_cache_modified = False
_cache_hits = 0
_cache_misses = 0

def load_cache(cache_path=None):
    """Carrega o cache de hashes do disco."""
    global _hash_cache, _cache_file
    if cache_path:
        _cache_file = cache_path
    
    if os.path.exists(_cache_file):
        try:
            with open(_cache_file, 'r', encoding='utf-8') as f:
                _hash_cache = json.load(f)
            print(f"✓ Cache carregado: {len(_hash_cache)} entradas")
            return len(_hash_cache)
        except Exception as e:
            print(f"⚠ Erro ao carregar cache: {e}")
            _hash_cache = {}
    else:
        _hash_cache = {}
    return 0

def save_cache(cache_path=None):
    """Salva o cache de hashes no disco."""
    global _hash_cache, _cache_file, _cache_modified
    if not _cache_modified:
        return
    
    if cache_path:
        _cache_file = cache_path
    
    try:
        with open(_cache_file, 'w', encoding='utf-8') as f:
            json.dump(_hash_cache, f, indent=2)
        print(f"✓ Cache salvo: {len(_hash_cache)} entradas")
        _cache_modified = False
    except Exception as e:
        print(f"⚠ Erro ao salvar cache: {e}")

def get_cached_hash(file_path):
    """Obtém o hash de um arquivo do cache, se ainda for válido."""
    global _hash_cache
    
    if file_path not in _hash_cache:
        return None
    
    try:
        cached = _hash_cache[file_path]
        current_size = os.path.getsize(file_path)
        current_mtime = os.path.getmtime(file_path)
        
        # Verifica se o arquivo não foi modificado
        if (cached.get('size') == current_size and 
            abs(cached.get('mtime', 0) - current_mtime) < 1):  # Tolerância de 1 segundo
            return cached.get('hash')
    except (OSError, KeyError):
        pass
    
    return None

def update_cache(file_path, file_hash):
    """Atualiza o cache com o hash de um arquivo."""
    global _hash_cache, _cache_modified
    
    try:
        file_size = os.path.getsize(file_path)
        file_mtime = os.path.getmtime(file_path)
        
        _hash_cache[file_path] = {
            'hash': file_hash,
            'size': file_size,
            'mtime': file_mtime,
            'cached_at': time.time()
        }
        _cache_modified = True
    except Exception as e:
        print(f"⚠ Erro ao atualizar cache para {file_path}: {e}")

def calculate_hash(file_path, block_size=65536, quick_hash=False):
    """Calcula o hash SHA-256 de um arquivo, usando cache quando possível.
    
    Args:
        file_path: Caminho do arquivo
        block_size: Tamanho do bloco para leitura
        quick_hash: Se True, faz hash apenas dos primeiros 1MB (mais rápido)
    """
    global _cache_hits, _cache_misses
    
    # Tenta obter do cache primeiro
    cached_hash = get_cached_hash(file_path)
    if cached_hash:
        _cache_hits += 1
        return cached_hash
    
    _cache_misses += 1
    
    # Calcula o hash
    sha256 = hashlib.sha256()
    try:
        bytes_to_read = 1024 * 1024 if quick_hash else None  # 1MB para quick hash
        bytes_read = 0
        
        with open(file_path, 'rb') as f:
            for block in iter(lambda: f.read(block_size), b''):
                sha256.update(block)
                bytes_read += len(block)
                
                if quick_hash and bytes_read >= bytes_to_read:
                    break
        
        file_hash = sha256.hexdigest()
        
        # Atualiza o cache apenas para hashes completos
        if not quick_hash:
            update_cache(file_path, file_hash)
        
        return file_hash
    except Exception as e:
        print(f"Erro ao ler arquivo {file_path}: {e}")
        return None

def files_are_identical(file_path_a, file_path_b, block_size=65536):
    """Compara dois arquivos byte a byte para confirmar igualdade."""
    try:
        if os.path.getsize(file_path_a) != os.path.getsize(file_path_b):
            return False
        with open(file_path_a, 'rb') as fa, open(file_path_b, 'rb') as fb:
            for block_a in iter(lambda: fa.read(block_size), b''):
                block_b = fb.read(block_size)
                if block_a != block_b:
                    return False
        return True
    except Exception as e:
        print(f"Erro ao comparar arquivos '{file_path_a}' e '{file_path_b}': {e}")
        return False

def find_duplicates(folder_path, progress_callback=None, cancel_check=None, duplicate_callback=None, return_stats=False, valid_extensions=None):
    """Encontra arquivos duplicados em uma pasta baseada no hash SHA-256."""
    global _cache_hits, _cache_misses
    
    # Reseta contadores de cache
    _cache_hits = 0
    _cache_misses = 0
    
    # Carrega o cache no início
    cache_loaded = load_cache()
    
    hashes = defaultdict(list)
    size_groups = defaultdict(list)
    
    # Extensões comuns de imagem e vídeo para verificar
    if valid_extensions is None:
        valid_extensions = {
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp',  # Imagens
            '.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.m4v'      # Vídeos
        }

    print(f"Verificando arquivos em: {folder_path}")
    print("Isso pode levar algum tempo dependendo do número e tamanho dos arquivos...")

    files_checked = 0
    files_scanned = 0
    for root, _, files in os.walk(folder_path):
        for filename in files:
            if cancel_check and cancel_check():
                save_cache()
                if return_stats:
                    return {}, files_checked, files_scanned, 0
                return {}, files_checked
            file_extension = os.path.splitext(filename)[1].lower()
            
            if file_extension in valid_extensions:
                file_path = os.path.join(root, filename)
                try:
                    file_size = os.path.getsize(file_path)
                    size_groups[file_size].append(file_path)
                    files_scanned += 1
                    if files_scanned % 200 == 0:
                        print(f"Escaneados {files_scanned} arquivos...")
                except Exception as e:
                    print(f"Erro ao obter tamanho de {file_path}: {e}")

    total_candidates = sum(len(file_list) for file_list in size_groups.values() if len(file_list) > 1)
    print(f"\nEncontrados {total_candidates} arquivos candidatos em {len([g for g in size_groups.values() if len(g) > 1])} grupos de tamanho")
    
    if progress_callback:
        progress_callback({
            "phase": "scan_done",
            "files_scanned": files_scanned,
            "total_candidates": total_candidates
        })

    # Otimização: processar grupos do maior para o menor (economiza mais espaço primeiro)
    sorted_groups = sorted(size_groups.items(), key=lambda x: x[0] * len(x[1]), reverse=True)
    
    for file_size, file_list in sorted_groups:
        if len(file_list) < 2:
            continue
            
        # Para grupos grandes (>10 arquivos), usar hash rápido primeiro
        use_quick_hash = len(file_list) > 10
        quick_hashes = defaultdict(list) if use_quick_hash else None
        
        for file_path in file_list:
            if cancel_check and cancel_check():
                save_cache()
                if return_stats:
                    return {}, files_checked, files_scanned, total_candidates
                return {}, files_checked
            
            # Se grupo grande, fazer hash rápido primeiro
            if use_quick_hash:
                quick_hash = calculate_hash(file_path, quick_hash=True)
                if quick_hash:
                    quick_hashes[quick_hash].append(file_path)
            else:
                file_hash = calculate_hash(file_path)
                if file_hash:
                    hashes[file_hash].append(file_path)
                    files_checked += 1
            
            # Relatório de progresso menos frequente para melhor performance
            if files_checked % 100 == 0:
                cache_percent = round((_cache_hits / (_cache_hits + _cache_misses) * 100)) if (_cache_hits + _cache_misses) > 0 else 0
                print(f"Processados {files_checked}/{total_candidates} arquivos... (Cache: {cache_percent}%)")
            
            if progress_callback and (files_checked % 100 == 0 or files_checked == total_candidates):
                progress_callback({
                    "phase": "hashing",
                    "current": files_checked,
                    "total": total_candidates,
                    "cache_hits": _cache_hits,
                    "cache_misses": _cache_misses
                })
        
        # Se usou hash rápido, agora fazer hash completo apenas dos grupos com colisão
        if use_quick_hash:
            for quick_hash, paths in quick_hashes.items():
                if len(paths) < 2:
                    continue  # Não é duplicata
                
                # Fazer hash completo apenas destes arquivos
                for file_path in paths:
                    if cancel_check and cancel_check():
                        save_cache()
                        if return_stats:
                            return {}, files_checked, files_scanned, total_candidates
                        return {}, files_checked
                    
                    file_hash = calculate_hash(file_path, quick_hash=False)
                    if file_hash:
                        hashes[file_hash].append(file_path)
                        files_checked += 1

    duplicates = {}
    print(f"\nVerificando grupos de hash duplicados...")
    
    for file_hash, file_list in hashes.items():
        if len(file_list) < 2:
            continue
        
        # Otimização: apenas verificar byte-a-byte se houver mais de 2 arquivos com mesmo hash
        # (colisões SHA-256 são extremamente raras)
        if len(file_list) == 2:
            # Com apenas 2 arquivos, assumir que são duplicatas (hash SHA-256 é confiável)
            duplicates[file_hash] = file_list
            if duplicate_callback:
                duplicate_callback(file_hash, file_list)
        else:
            # Com 3+ arquivos, fazer verificação binária para ter certeza
            verified_groups = []
            for file_path in file_list:
                placed = False
                for group in verified_groups:
                    if files_are_identical(file_path, group[0]):
                        group.append(file_path)
                        placed = True
                        break
                if not placed:
                    verified_groups.append([file_path])

            if len(verified_groups) == 1 and len(verified_groups[0]) > 1:
                duplicates[file_hash] = verified_groups[0]
                if duplicate_callback:
                    duplicate_callback(file_hash, verified_groups[0])
            else:
                for index, group in enumerate(verified_groups, start=1):
                    if len(group) > 1:
                        group_key = f"{file_hash}-{index}"
                        duplicates[group_key] = group
                        if duplicate_callback:
                            duplicate_callback(group_key, group)
    
    # Salva o cache antes de retornar
    save_cache()
    
    if return_stats:
        return duplicates, files_checked, files_scanned, total_candidates
    return duplicates, files_checked

def clear_cache(cache_path=None):
    """Limpa o cache de hashes."""
    global _hash_cache, _cache_file
    if cache_path:
        _cache_file = cache_path
    
    _hash_cache = {}
    if os.path.exists(_cache_file):
        try:
            os.remove(_cache_file)
            print("✓ Cache limpo com sucesso")
        except Exception as e:
            print(f"⚠ Erro ao limpar cache: {e}")

def get_cache_stats():
    """Retorna estatísticas do cache atual."""
    return {
        "entries": len(_hash_cache),
        "hits": _cache_hits,
        "misses": _cache_misses,
        "hit_rate": round((_cache_hits / (_cache_hits + _cache_misses) * 100)) if (_cache_hits + _cache_misses) > 0 else 0
    }

def main():
    parser = argparse.ArgumentParser(description="Encontrar imagens e vídeos duplicados.")
    parser.add_argument("folder", nargs="?", default=".", help="Caminho da pasta para verificar (padrão: pasta atual)")
    args = parser.parse_args()

    folder_path = args.folder
    
    if not os.path.isdir(folder_path):
        print(f"Erro: A pasta '{folder_path}' não existe.")
        return

    duplicates, total_checked = find_duplicates(folder_path)

    print("\n" + "="*40)
    print(f"RELATÓRIO DE DUPLICATAS")
    print("="*40)
    print(f"Total de arquivos verificados: {total_checked}")
    print(f"Conjuntos de duplicatas encontrados: {len(duplicates)}")
    
    # Exibe estatísticas de cache
    cache_stats = get_cache_stats()
    if cache_stats["hits"] + cache_stats["misses"] > 0:
        print(f"Cache: {cache_stats['hits']} hits, {cache_stats['misses']} misses ({cache_stats['hit_rate']}%)")
    
    print("-" * 40)

    if not duplicates:
        print("Nenhuma duplicata encontrada.")
    else:
        for file_hash, file_list in duplicates.items():
            print(f"\nHash: {file_hash}")
            print(f"Arquivos ({len(file_list)}):")
            for file_path in file_list:
                print(f" - {file_path}")

    print("\n" + "="*40)

if __name__ == "__main__":
    main()
