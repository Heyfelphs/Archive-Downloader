# utils/filesystem.py

from os import makedirs, listdir
from os.path import exists
from shutil import rmtree
from fnmatch import filter as fnmatch_filter


def recreate_dir(path: str):
    if exists(path):
        rmtree(path)
    makedirs(path, mode=0o777, exist_ok=True)


def count_files(path: str) -> int:
    return len(fnmatch_filter(listdir(path), "*.*"))
