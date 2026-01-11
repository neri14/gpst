
from pathlib import Path

from .track import Track
from .writer import Writer, GpxWriter


_writers = {
    '.gpx': GpxWriter()
}


def save_track(track: Track, path: Path) -> bool:
    writer: Writer|None = _writers.get(path.suffix.lower())
    if writer is None:
        raise ValueError(f"Unsupported file extension '{path.suffix}'")
    return writer.write(track, path)
