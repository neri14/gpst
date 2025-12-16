from pathlib import Path

from .track import Track
from .reader import FitReader, GpxReader


_readers = {
    '.fit': FitReader(),
    '.gpx': GpxReader()
}


def load_track(path: Path) -> Track:
    reader = _readers.get(path.suffix.lower())
    if reader is None:
        raise ValueError(f"Unsupported file extension '{path.suffix}'")
    return reader.read(path)
