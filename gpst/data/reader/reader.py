from abc import ABC, abstractmethod
from pathlib import Path
from ..track import Track


class Reader(ABC):
    @abstractmethod
    def read(self, path: Path) -> Track:
        pass
