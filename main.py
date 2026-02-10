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

import traceback

def log_exception_to_file():
    with open("log.txt", "a", encoding="utf-8") as f:
        f.write("\n--- Exception Traceback ---\n")
        traceback.print_exc(file=f)

if __name__ == "__main__":
        # ...elevação de privilégio removida...
    try:
        print("[DEBUG] Processo iniciado. is_admin=", is_admin())
        freeze_support()
        print("[DEBUG] Chamando start_app()...")
        start_app()
        print("[DEBUG] start_app() retornou.")
    except Exception:
        log_exception_to_file()
        raise
    