from pathlib import Path

from ..track import Track
from .reader import Reader


class FitReader(Reader):
    def read(self, path: Path) -> Track:
        raise NotImplementedError("FIT reading not yet implemented")
