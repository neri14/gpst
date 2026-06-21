from pathlib import Path
from typing import TYPE_CHECKING

from .reader import Reader

if TYPE_CHECKING:
    from .fit_reader import FitReader
else:
    try:
        from .fit_reader import FitReader
    except Exception:  # pragma: no cover - optional dependency path
        class FitReader(Reader):
            def read(self, path: Path):
                raise ImportError("FitReader requires optional FIT dependencies.")

from .gpx_reader import GpxReader
from .vbo_reader import VboReader
