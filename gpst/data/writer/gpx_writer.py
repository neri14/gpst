from pathlib import Path

from ..track import Track
from .writer import Writer


class GpxWriter(Writer):
    def write(self, track: Track, path: Path) -> bool:
        raise NotImplementedError("GPX writing not yet implemented")
