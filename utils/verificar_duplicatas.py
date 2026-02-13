import os
import hashlib
import argparse
from collections import defaultdict

def calculate_md5(file_path, block_size=65536):
    """Calcula o hash MD5 de um arquivo."""
    md5 = hashlib.md5()
    try:
        with open(file_path, 'rb') as f:
            for block in iter(lambda: f.read(block_size), b''):
                md5.update(block)
        return md5.hexdigest()
    except Exception as e:
        print(f"Erro ao ler arquivo {file_path}: {e}")
        return None

def find_duplicates(folder_path):
    """Encontra arquivos duplicados em uma pasta baseada no hash MD5."""
    # Dicionário para armazenar hash -> lista de arquivos
    hashes = defaultdict(list)
    
    # Extensões comuns de imagem e vídeo para verificar
    valid_extensions = {
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp',  # Imagens
        '.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.m4v'      # Vídeos
    }

    print(f"Verificando arquivos em: {folder_path}")
    print("Isso pode levar algum tempo dependendo do número e tamanho dos arquivos...")

    files_checked = 0
    for root, _, files in os.walk(folder_path):
        for filename in files:
            file_extension = os.path.splitext(filename)[1].lower()
            
            if file_extension in valid_extensions:
                file_path = os.path.join(root, filename)
                file_hash = calculate_md5(file_path)
                
                if file_hash:
                    hashes[file_hash].append(file_path)
                    files_checked += 1
                    if files_checked % 100 == 0:
                        print(f"Processados {files_checked} arquivos...")

    duplicates = {k: v for k, v in hashes.items() if len(v) > 1}
    
    return duplicates, files_checked

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
