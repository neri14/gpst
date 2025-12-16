from pathlib import Path

from ..track import Track
from .reader import Reader


class GpxReader(Reader):
    def read(self, path: Path) -> Track|None:
        raise NotImplementedError("GPX reading not yet implemented")
