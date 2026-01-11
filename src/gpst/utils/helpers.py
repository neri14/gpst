import math
from datetime import datetime, timezone

radio_terrestre = 6372797.5605
grados_radianes = math.pi / 180


def to_string(value: int | float | str | datetime | None) -> str:
    if isinstance(value, datetime):
        return timestamp_str(value)
    else:
        return str(value)


def timestamp_str(dt: datetime|None) -> str:
    if dt is None or not isinstance(dt, datetime):
        return ""
    if dt.tzinfo is None:
        dt_utc = dt.replace(tzinfo=timezone.utc)
    else:
        dt_utc = dt.astimezone(timezone.utc)
    return dt_utc.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'


def timestamp_from_str(s: str|None) -> datetime|None:
    if s is None or not isinstance(s, str) or not s.strip():
        return None
    try:
        if s.endswith('Z'):
            s = s[:-1] + '+00:00'
        dt = datetime.fromisoformat(s)
        return dt
    except ValueError:
        return None


def geo_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    lat1 = lat1 * grados_radianes
    lon1 = lon1 * grados_radianes
    lat2 = lat2 * grados_radianes
    lon2 = lon2 * grados_radianes

    haversine = (math.sin((lat2 - lat1)/2.0) ** 2) + (math.cos(lat1) * math.cos(lat2) * (math.sin((lon2 - lon1)/2.0) ** 2))
    dist = 2 * math.asin(min(1.0, math.sqrt(haversine))) * radio_terrestre

    return dist
