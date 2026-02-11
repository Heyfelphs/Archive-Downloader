# main.py

from multiprocessing import freeze_support
from app import start_app

if __name__ == "__main__":
    freeze_support()
    start_app()
    