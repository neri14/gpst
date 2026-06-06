from pathlib import Path

from .track import Track
from .reader import Reader, FitReader, GpxReader, VboReader


_readers = {
    '.fit': FitReader(),
    '.gpx': GpxReader(),
    '.vbo': VboReader()
}


def load_track(path: Path) -> Track|None:
    reader: Reader|None = _readers.get(path.suffix.lower())
    if reader is None:
        raise ValueError(f"Unsupported file extension '{path.suffix}'")
    return reader.read(path)
