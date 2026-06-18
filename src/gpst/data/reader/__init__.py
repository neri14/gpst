from .reader import Reader

try:
    from .fit_reader import FitReader
except Exception:  # pragma: no cover - optional dependency path
    FitReader = None  # type: ignore[assignment]

from .gpx_reader import GpxReader
from .vbo_reader import VboReader
