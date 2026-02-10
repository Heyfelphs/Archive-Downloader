# main.py

from multiprocessing import freeze_support
from app import start_app


import sys
import os
import ctypes

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False

if __name__ == "__main__":
    if os.name == 'nt' and not is_admin():
        # Re-executa como administrador
        params = ' '.join([f'"{arg}"' for arg in sys.argv])
        try:
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
        except Exception as e:
            print(f"Falha ao tentar executar como administrador: {e}")
        sys.exit(0)
    freeze_support()
    start_app()
    