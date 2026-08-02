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

    # Convert lat/lon to 3D Cartesian coordinates on the sphere for proper geometric calculations
    def latlon_to_cartesian(lat: float, lon: float) -> tuple[float, float, float]:
        lat_rad = lat * grados_radianes
        lon_rad = lon * grados_radianes
        x = radio_terrestre * math.cos(lat_rad) * math.cos(lon_rad)
        y = radio_terrestre * math.cos(lat_rad) * math.sin(lon_rad)
        z = radio_terrestre * math.sin(lat_rad)
        return x, y, z

    p = latlon_to_cartesian(lat, lon)
    a = latlon_to_cartesian(line_start[0], line_start[1])
    b = latlon_to_cartesian(line_end[0], line_end[1])

    ap = (p[0] - a[0], p[1] - a[1], p[2] - a[2])
    ab = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
    ab_length_squared = ab[0]**2 + ab[1]**2 + ab[2]**2

    if ab_length_squared == 0:
        return line_start  # Line start and end are the same point

    t = (ap[0] * ab[0] + ap[1] * ab[1] + ap[2] * ab[2]) / ab_length_squared
    t_clamped = max(0, min(1, t))

    closest_point_cartesian = (a[0] + t_clamped * ab[0], a[1] + t_clamped * ab[1], a[2] + t_clamped * ab[2])

    # Convert back to lat/lon
    def cartesian_to_latlon(x: float, y: float, z: float) -> tuple[float, float]:
        r = math.sqrt(x**2 + y**2 + z**2)
        # Normalize the point to ensure it's on the sphere surface
        x, y, z = x / r * radio_terrestre, y / r * radio_terrestre, z / r * radio_terrestre
        lat = math.asin(z / radio_terrestre) / grados_radianes
        lon = math.atan2(y, x) / grados_radianes
        return lat, lon

    closest_point_latlon = cartesian_to_latlon(closest_point_cartesian[0], closest_point_cartesian[1], closest_point_cartesian[2])
    return closest_point_latlon


def lines_intersect(lat1: float, lon1: float, lat2: float, lon2: float, lat3: float, lon3: float, lat4: float, lon4: float) -> bool:
    # This function checks if the line segment from (lat1, lon1) to (lat2, lon2) intersects with the line segment from (lat3, lon3) to (lat4, lon4)
    # For small local areas (< 100km), uses planar approximation which is simpler and more reliable than great-circle math
    # Convert lat/lon to local Cartesian coordinates using Mercator projection
    def latlon_to_local_cartesian(lat: float, lon: float, ref_lat: float, ref_lon: float) -> tuple[float, float]:
        # Use Mercator projection centered at reference point for local calculations
        dx = (lon - ref_lon) * math.cos(ref_lat * grados_radianes) * radio_terrestre * grados_radianes
        dy = (lat - ref_lat) * radio_terrestre * grados_radianes
        return dx, dy

    # Use reference point as midpoint for better accuracy
    ref_lat = (lat1 + lat2 + lat3 + lat4) / 4
    ref_lon = (lon1 + lon2 + lon3 + lon4) / 4

    # Convert all points to local Cartesian
    p1 = latlon_to_local_cartesian(lat1, lon1, ref_lat, ref_lon)
    p2 = latlon_to_local_cartesian(lat2, lon2, ref_lat, ref_lon)
    p3 = latlon_to_local_cartesian(lat3, lon3, ref_lat, ref_lon)
    p4 = latlon_to_local_cartesian(lat4, lon4, ref_lat, ref_lon)

    # Check if segments intersect using 2D cross product method
    def ccw(ax: float, ay: float, bx: float, by: float, cx: float, cy: float) -> bool:
        return (cy - ay) * (bx - ax) >= (by - ay) * (cx - ax)

    return ccw(p1[0], p1[1], p3[0], p3[1], p4[0], p4[1]) != ccw(p2[0], p2[1], p3[0], p3[1], p4[0], p4[1]) and \
           ccw(p1[0], p1[1], p2[0], p2[1], p3[0], p3[1]) != ccw(p1[0], p1[1], p2[0], p2[1], p4[0], p4[1])

