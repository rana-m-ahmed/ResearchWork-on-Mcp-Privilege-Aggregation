import os

def ensure_directory(path: str) -> None:
    os.makedirs(path, exist_ok=True)