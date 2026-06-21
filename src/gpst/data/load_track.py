from pathlib import Path

from .track import Track
from .reader.reader import Reader


def _build_reader(path: Path) -> Reader:
    suffix = path.suffix.lower()
    if suffix == '.fit':
        from .reader.fit_reader import FitReader
        return FitReader()
    if suffix == '.gpx':
        from .reader.gpx_reader import GpxReader
        return GpxReader()
    if suffix == '.vbo':
        from .reader.vbo_reader import VboReader
        return VboReader()
    raise ValueError(f"Unsupported file extension '{path.suffix}'")


def load_track(path: Path) -> Track|None:
    reader = _build_reader(path)
    return reader.read(path)
