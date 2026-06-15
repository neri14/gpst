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


def find_closest_point_on_line(lat: float, lon: float, line_start: tuple[float, float], line_end: tuple[float, float]) -> tuple[float, float]:
    # This function finds the closest point on the line defined by line_start and line_end to the point (lat, lon)
    # It uses a projection of the point onto the line segment and checks if the projection falls within the segment
    # If it does, it returns the projected point; otherwise, it returns the closest endpoint

    # Convert lat/lon to Cartesian coordinates for easier calculations
    def latlon_to_cartesian(lat: float, lon: float) -> tuple[float, float]:
        x = radio_terrestre * math.cos(lat * grados_radianes) * math.cos(lon * grados_radianes)
        y = radio_terrestre * math.cos(lat * grados_radianes) * math.sin(lon * grados_radianes)
        return x, y

    p = latlon_to_cartesian(lat, lon)
    a = latlon_to_cartesian(line_start[0], line_start[1])
    b = latlon_to_cartesian(line_end[0], line_end[1])

    ap = (p[0] - a[0], p[1] - a[1])
    ab = (b[0] - a[0], b[1] - a[1])
    ab_length_squared = ab[0]**2 + ab[1]**2

    if ab_length_squared == 0:
        return line_start  # Line start and end are the same point

    t = (ap[0] * ab[0] + ap[1] * ab[1]) / ab_length_squared
    t_clamped = max(0, min(1, t))

    closest_point_cartesian = (a[0] + t_clamped * ab[0], a[1] + t_clamped * ab[1])

    # Convert back to lat/lon
    def cartesian_to_latlon(x: float, y: float) -> tuple[float, float]:
        r = math.sqrt(x**2 + y**2)
        lat = math.acos(r / radio_terrestre) / grados_radianes
        lon = math.atan2(y, x) / grados_radianes
        return lat, lon

    closest_point_latlon = cartesian_to_latlon(closest_point_cartesian[0], closest_point_cartesian[1])
    return closest_point_latlon
