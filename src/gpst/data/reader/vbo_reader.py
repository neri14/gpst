import re
import xml.etree.ElementTree as ET

from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from ..track import Track, Value, SegmentType
from .reader import Reader
from ...utils.logger import logger
from ...utils.helpers import timestamp_from_str

def normalize_name(name: str) -> str:
    name = name.strip().lower()
    name = re.sub(r'\W+', '_', name)
    return name


def canonical_field_name(name: str) -> str:
    """Normalize source-specific field names to stable internal keys."""
    normalized = normalize_name(name)
    aliases = {
        'latitude': 'lat',
        'longitude': 'lon',
        'long': 'lon',
        'lng': 'lon',
        'velocity_kmh': 'velocity',
        'speed_kmh': 'velocity',
    }
    return aliases.get(normalized, normalized)

class VboReader(Reader):
    def read(self, path: Path) -> Track|None:
        track = Track()

        header_fields: list[str] = []
        column_fields: list[str] = []
        effective_fields: list[str] = []

        now = datetime.now()
        yy, mm, dd = now.year, now.month, now.day

        with open(path, 'r', encoding='utf-8') as f:
            while True:
                line = f.readline()
                if not line:
                    break
                line = line.strip()

                if line.startswith('File created on'):
                    datestr = line[len('File created on '):].split(' ')[0]
                    dd, mm, yy = map(int, datestr.split('/'))
                    logger.debug(f"Parsed date from file header: {yy}-{mm:02d}-{dd:02d}")
                    continue

                if '[header]' in line.lower():
                    header_fields = []
                    while True:
                        field_line = f.readline()
                        if not field_line:
                            break
                        field_line = field_line.strip()
                        if not field_line:
                            continue
                        if field_line.startswith('[') and field_line.endswith(']'):
                            line = field_line
                            break
                        header_fields.append(canonical_field_name(field_line))

                    logger.debug(f"Found header fields: {header_fields}")
                    if not (line.startswith('[') and line.endswith(']')):
                        continue
                
                if '[column names]' in line.lower():
                    column_line = f.readline().strip()
                    column_fields = [canonical_field_name(col) for col in column_line.split()]
                    logger.debug(f"Found column fields: {column_fields}")

                    if header_fields and len(header_fields) == len(column_fields):
                        effective_fields = header_fields
                        logger.debug('Using [header] fields as source schema for [data] rows.')
                    else:
                        effective_fields = column_fields
                        if header_fields and len(header_fields) != len(column_fields):
                            logger.warning(
                                'Header/column field count mismatch '
                                f'({len(header_fields)} != {len(column_fields)}). '
                                'Falling back to [column names].'
                            )

                    continue

                if '[data]' in line.lower():
                    break

            if not effective_fields:
                logger.warning('No VBO schema found ([header] or [column names]).')
                return track
                    
            while True:
                line = f.readline()
                if not line:
                    break
                line = line.strip()
                if not line:
                    continue
                
                if line.startswith('[') and line.endswith(']'):
                    logger.debug(f"Reached end of data section at line: {line}")
                    break

                values = line.split()
                if len(values) != len(effective_fields):
                    logger.warning(f"Skipping line with unexpected number of values: {line}")
                    continue


                data: dict[str, Value] = {}

                ts: datetime|None = None

                for col, val_str in zip(effective_fields, values):
                    try:
                        val = float(val_str)
                    except ValueError:
                        logger.warning(f"Skipping invalid value for column '{col}': {val_str}")
                        continue
                    
                    match col:
                        case 'time':
                            ...# parse time HHMMSS.mmm
                            h = int(val // 10000)
                            val = val - h * 10000
                            m = int(val // 100)
                            val = val - m * 100
                            s = int(val)
                            us = int((val - s) * 1_000_000)
                            time  = datetime(yy, mm, dd, h, m, s, us, tzinfo=timezone.utc)

                            data['time'] = time
                            ts = time
                        case 'lat':
                            data['lat'] = val/60.0
                        case 'lon':
                            data['lon'] = val/-60.0
                        case 'height':
                            data['ele'] = val
                        case 'velocity':
                            data['speed'] = val/3.6
                            data[col] = val
                        case _:
                            data[col] = val

                if ts is None:
                    logger.warning(f"Skipping line with missing time value: {line}")
                    continue
                track.upsert_point(ts, data, custom_fields=True)

        return track
