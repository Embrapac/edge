import os
from pathlib import Path

MAX_STORAGE_BYTES = 25 * 1024 ** 3  # 25 GB

class VideoBufferManager:
    def __init__(self, storage_path: str):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def current_size(self) -> int:
        return sum(f.stat().st_size for f in self.storage_path.rglob("*") if f.is_file())

    def enforce_limit(self):
        """Remove os arquivos mais antigos até estar dentro do limite."""
        files = sorted(
            self.storage_path.rglob("*.mp4"),
            key=lambda f: f.stat().st_mtime
        )
        while self.current_size() > MAX_STORAGE_BYTES and files:
            oldest = files.pop(0)
            oldest.unlink()

    def available_space(self) -> int:
        return max(0, MAX_STORAGE_BYTES - self.current_size())
