from abc import ABC, abstractmethod
from pathlib import Path
from ..track import Track


class Writer(ABC):
    @abstractmethod
    def write(self, track: Track, path: Path) -> bool:
        pass
