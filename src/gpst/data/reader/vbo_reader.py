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

class VboReader(Reader):
    def read(self, path: Path) -> Track|None:
        track = Track()

        columns = []

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
                
                if '[column names]' in line.lower():
                    columns = f.readline().strip().split(' ')

                    columns = [normalize_name(col) for col in columns]
                    logger.debug(f"Found columns: {columns}")
                    continue

                if '[data]' in line.lower():
                    break
                    
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

                values = line.split(' ')
                if len(values) != len(columns):
                    logger.warning(f"Skipping line with unexpected number of values: {line}")
                    continue


                data = {}

                for col, val in zip(columns, values):
                    try:
                        val = float(val)
                    except ValueError:
                        logger.warning(f"Skipping invalid value for column '{col}': {val}")
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
                        case 'lat':
                            data['lat'] = val/60.0
                        case 'long':
                            data['lon'] = val/-60.0
                        case 'height':
                            data['ele'] = val
                        case 'velocity':
                            data['speed'] = val/3.6
                            data[col] = val
                        case _:
                            data[col] = val

                track.upsert_point(data['time'], data, custom_fields=True)

        return track
