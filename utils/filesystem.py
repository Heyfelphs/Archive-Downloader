# utils/filesystem.py

from os import makedirs
from os.path import exists
from shutil import rmtree


def recreate_dir(path: str):
    if exists(path):
        rmtree(path)
    makedirs(path, mode=0o777, exist_ok=True)


