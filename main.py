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
    if os.name == 'nt' and not is_admin() and not os.environ.get("NO_ADMIN_CHECK"):
        # Re-executa como administrador
        params = ' '.join([f'"{arg}"' for arg in sys.argv])
        try:
            # 0 = SW_HIDE, 1 = SW_SHOWNORMAL (com janela), 7 = SW_SHOWMINNOACTIVE
            ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 0)
            # Usando SW_HIDE (0) para não abrir janela de cmd
            # Se quiser janela, troque para 1
            if int(ret) <= 32:
                print(f"Falha ao tentar executar como administrador. Código de retorno: {ret}")
            else:
                print("Processo de elevação iniciado com sucesso. Encerrando processo original.")
        except Exception as e:
            print(f"Falha ao tentar executar como administrador: {e}")
        sys.exit(0)
    try:
        print("[DEBUG] Processo iniciado. is_admin=", is_admin())
        freeze_support()
        print("[DEBUG] Chamando start_app()...")
        start_app()
        print("[DEBUG] start_app() retornou.")
    except Exception:
        log_exception_to_file()
        raise
    