import math
import statistics
from datetime import datetime, timedelta

from ...utils.helpers import to_string, geo_distance
from ..track import Track, Value, latitude_t, longitude_t

from ...utils.logger import logger


SMOOTH_ELEVATION_WINDOW = 5 # seconds
MAX_GRADE_WINDOW = 50 # meters
MIN_GRADE_WINDOW = 20 # meters


def _calculate_times(track: Track) -> Track:
    """Calculate start_time, end_time, total_elapsed_time metadata and time point field."""

    logger.debug("Calculating time for track points...")
    start_time: datetime | None = None
    end_time: datetime | None = None

    total_time: float | None = 0.0

    for ts, point in track.points_iter:
        if start_time is None:
            start_time = ts
        end_time = ts

        total_time = (ts - start_time).total_seconds() if start_time and ts else 0.0

        if total_time is not None and 'time' not in point:
            logger.trace(f"Setting time for point at {to_string(ts)} to {total_time} seconds")
            point['time'] = total_time
    
    logger.debug("Setting calculated time metadata...")

    if start_time is not None and 'start_time' not in track.metadata:
        track.set_metadata('start_time', start_time)
        logger.info(f"Start time set to {to_string(start_time)}")
    
    if end_time is not None and 'end_time' not in track.metadata:
        track.set_metadata('end_time', end_time)
        logger.info(f"End time set to {to_string(end_time)}")

    st = track.metadata.get('start_time')
    et = track.metadata.get('end_time')
    if isinstance(st, datetime) and isinstance(et, datetime):
        elapsed_time = (et - st).total_seconds() if st and et else None

        if elapsed_time:
            track.set_metadata('total_elapsed_time', elapsed_time)
            logger.info(f"Total elapsed time set to {elapsed_time} seconds")
        elif 'total_elapsed_time' in track.metadata:
            track.remove_metadata('total_elapsed_time')
            logger.info("Total elapsed time removed due to missing start or end time")

    return track


def _calculate_bounds(track: Track) -> Track:
    """Calculate minlat, minlon, maxlat, maxlon metadata."""

    if ('minlat' in track.metadata and 'maxlat' in track.metadata and
        'minlon' in track.metadata and 'maxlon' in track.metadata):
        logger.debug("Track bounds already present in metadata. Skipping calculation.")
        return track

    logger.debug("Calculating track bounds...")

    minlat: float | None = None
    minlon: float | None = None
    maxlat: float | None = None
    maxlon: float | None = None

    for _, point in track.points_iter:
        lat = point.get('latitude')
        lon = point.get('longitude')

        if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
            if minlat is None or lat < minlat:
                minlat = lat
            if maxlat is None or lat > maxlat:
                maxlat = lat
            if minlon is None or lon < minlon:
                minlon = lon
            if maxlon is None or lon > maxlon:
                maxlon = lon


    if (not isinstance(minlat, (int, float)) or not isinstance(minlon, (int, float)) or
        not isinstance(maxlat, (int, float)) or not isinstance(maxlon, (int, float))):

        logger.debug("Insufficient data to calculate track bounds.")
        return track

    if minlat is not None and minlon is not None and \
       maxlat is not None and maxlon is not None and \
       minlat < maxlat and minlon < maxlon:
        
        track.set_metadata('minlat', minlat)
        track.set_metadata('maxlat', maxlat)
        track.set_metadata('minlon', minlon)
        track.set_metadata('maxlon', maxlon)

        logger.info(f"Track bounds set to minlat: {minlat}, minlon: {minlon}, maxlat: {maxlat}, maxlon: {maxlon}")

    return track


def _calculate_distances(track: Track) -> Track:
    """Calculate distance, track_distance point fields and total_distance metadata."""

    logger.debug("Calculating distances for track points...")

    total_distance: float = 0.0
    last_lat: float | None = None
    last_lon: float | None = None

    for ts, point in track.points_iter:
        lat = point.get('latitude')
        lon = point.get('longitude')

        if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
            if last_lat is not None and last_lon is not None:
                total_distance += geo_distance(last_lat, last_lon, lat, lon)

            last_lat = lat
            last_lon = lon

            point['track_distance'] = total_distance
            logger.trace(f"Setting track_distance for point at {to_string(ts)} to {total_distance} meters")
            if 'distance' not in point:
                point['distance'] = total_distance
                logger.trace(f"Setting distance for point at {to_string(ts)} to {total_distance} meters")

    track.set_metadata('total_track_distance', total_distance)
    logger.info(f"Total track distance set to {total_distance} meters")

    if 'total_distance' not in track.metadata:
        track.set_metadata('total_distance', total_distance)
        logger.info(f"Total distance set to {total_distance} meters")

    return track


def _calculate_speeds(track: Track) -> Track:
    """Calculate speed, track_speed point fields and avg_speed, max_speed metadata."""

    logger.debug("Calculating speeds for track points...")

    last_distance: float = 0.0
    last_time: float = 0.0

    max_speed: float = 0.0
    max_track_speed: float = 0.0

    for ts, point in track.points_iter:
        distance = point.get('distance')
        time = point.get('time')

        if (isinstance(distance, (int, float)) and isinstance(time, (int, float))):
            speed = (distance - last_distance) / (time - last_time) if (time - last_time) > 0 else 0.0

            point['track_speed'] = speed
            logger.trace(f"Setting track_speed for point at {to_string(ts)} to {speed} m/s")
            if 'speed' not in point:
                point['speed'] = speed
                logger.trace(f"Setting speed for point at {to_string(ts)} to {speed} m/s")

            if speed > max_track_speed:
                max_track_speed = speed
            
            if spd := point.get('speed'):
                if isinstance(spd, (int, float)) and spd > max_speed:
                    max_speed = spd

            last_distance = distance
            last_time = time

    track.set_metadata('max_track_speed', max_track_speed)
    logger.info(f"Max track speed set to {max_track_speed} m/s")

    if 'max_speed' not in track.metadata:
        track.set_metadata('max_speed', max_speed)
        logger.info(f"Max speed set to {max_speed} m/s")


    if 'avg_speed' not in track.metadata:
        total_time = track.metadata.get('total_elapsed_time')
        total_distance = track.metadata.get('total_distance')

        if (isinstance(total_distance, (int, float)) and
            isinstance(total_time, (int, float)) and total_time > 0):
            
            avg_speed = total_distance / total_time
            track.set_metadata('avg_speed', avg_speed)
            logger.info(f"Avg speed set to {avg_speed} m/s")


    total_time = track.metadata.get('total_elapsed_time')
    total_track_distance = track.metadata.get('total_track_distance')

    if (isinstance(total_track_distance, (int, float)) and
        isinstance(total_time, (int, float)) and total_time > 0):
        
        avg_track_speed = total_track_distance / total_time
        track.set_metadata('avg_track_speed', avg_track_speed)
        logger.info(f"Avg track speed set to {avg_track_speed} m/s")

    return track


def _calculate_vspeeds(track: Track) -> Track:
    """Calculate vertical_speed point field."""

    logger.debug("Calculating vertical speeds for track points...")

    last_elevation: float | None = None
    last_time: float | None = None

    for ts, point in track.points_iter:
        elevation = point.get('elevation')
        time = point.get('time')

        if (isinstance(elevation, (int, float)) and
            isinstance(time, (int, float))):

            if last_elevation is not None and last_time is not None:
                v_speed = (elevation - last_elevation) / (time - last_time) if (time - last_time) > 0 else 0.0
                point['vertical_speed'] = v_speed
                logger.trace(f"Setting vertical_speed for point at {to_string(ts)} to {v_speed} m/s")

            last_elevation = elevation
            last_time = time

    return track


def _calculate_power_averages(track: Track) -> Track:
    """Calculate power3s, power10s, power30s point fields using simple moving averages."""

    logger.debug("Calculating power averages for track points...")

    power: dict[datetime, float] = {}
    for timestamp, point in track.points_iter:
        pwr = point.get('power')
        if isinstance(pwr, (int, float)):
            power[timestamp] = pwr

        power3s = [p for ts,p in power.items() if ts > timestamp - timedelta(seconds=3)]
        if len(power3s) > 0:
            point['power3s'] = statistics.mean(power3s)
        power10s = [p for ts,p in power.items() if ts > timestamp - timedelta(seconds=10)]
        if len(power10s) > 0:
            point['power10s'] = statistics.mean(power10s)
        power30s = [p for ts,p in power.items() if ts > timestamp - timedelta(seconds=30)]
        if len(power30s) > 0:
            point['power30s'] = statistics.mean(power30s)

        logger.trace(f"Setting power (3/10/30s) averages for point at {to_string(timestamp)} to {point.get('power3s', 0)} / {point.get('power10s', 0)} / {point.get('power30s', 0)} watts")

        power = {k: v for k, v in power.items() if k > timestamp - timedelta(seconds=30)}

    return track


def _calculate_smooth_elevation(track: Track) -> Track:
    """Calculate smooth_elevation point field using a simple moving average."""

    logger.debug("Calculating smooth elevation for track points...")

    for ts, point, window in track.sliding_window_iter(key='elevation', size=SMOOTH_ELEVATION_WINDOW):
        elevs = [p['elevation'] for p in window if 'elevation' in p and isinstance(p['elevation'], (int, float))]
        if len(elevs) > 0:
            point['smooth_elevation'] = statistics.mean(elevs)
            logger.trace(f"Setting smooth_elevation for point at {to_string(ts)} to {point['smooth_elevation']} meters")

    return track


def _calculate_grade(track: Track) -> Track:
    """Calculate grade point field."""

    logger.debug("Calculating grade")

    alt_key = 'smooth_elevation'
    dist_key = 'distance'

    max_grade: float | None = None
    min_grade: float | None = None

    for ts, point, window in track.sliding_window_iter(key=dist_key, size=MAX_GRADE_WINDOW):
        dist = point.get(dist_key)
        alt = point.get(alt_key)

        if dist is None or alt is None:
            logger.trace(f"Point at {to_string(ts)} missing {dist_key} or {alt_key} for grade calculation. Skipping.")
            continue

        altitudes = [(p[dist_key], p[alt_key]) for p in window if alt_key in p and dist_key in p]
        z1,y1 = altitudes[0]
        z2,y2 = altitudes[-1]

        if dist - z1 < MIN_GRADE_WINDOW/2:
            continue # don't calculate grade - covers beginning of activity
        if z2 - dist < MIN_GRADE_WINDOW/2:
            continue # don't calculate grade - covers end of activity

        z = z2 - z1
        y = y2 - y1

        x = math.sqrt(z**2 - y**2) # pythagoras (x**2 + y**2 = z**2 where z is distance delta and y is altitude delta)

        grade = (y / x) * 100.0
        point['grade'] = grade
        logger.trace(f"Setting grade for point at {to_string(ts)} to {grade} %")

        if max_grade is None or grade > max_grade:
            max_grade = grade
        if min_grade is None or grade < min_grade:
            min_grade = grade

    if isinstance(max_grade, (int, float)):
        track.set_metadata('max_grade', max_grade)
        logger.info(f"Max grade set to {max_grade} %")
    if isinstance(min_grade, (int, float)):
        track.set_metadata('min_grade', min_grade)
        logger.info(f"Min grade set to {min_grade} %")

    return track


def _calculate_misc(track: Track) -> Track:
    """Calculate miscellaneous metadata like jump_count."""

    logger.debug("Calculating miscellaneous metadata...")

    jump_count: int = 0

    for ts, point in track.points_iter:
        if any(f in point for f in ['jump_distance', 'jump_height', 'jump_rotations', 'jump_hang_time', 'jump_score']):
            logger.trace(f"Jump detected at {to_string(ts)}")
            jump_count += 1

    track.set_metadata('jump_count', jump_count)
    logger.info(f"Jump count set to {jump_count}")

    return track


def calculate_additional_data(track: Track) -> Track:
    track = _calculate_times(track) # metadata: start_time, end_time, total_elapsed_time, fields: time
    track = _calculate_bounds(track) # metadata: minlat, minlon, maxlat, maxlon
    track = _calculate_distances(track) # metadata: total_distance, total_track_distance, fields: distance, track_distance
    track = _calculate_speeds(track) # metadata: avg_speed, avg_track_speed, max_speed, max_track_speed, fields: speed, track_speed
    track = _calculate_vspeeds(track) # fields: vertical_speed
    track = _calculate_power_averages(track) # fields: power3s, power10s, power30s
    track = _calculate_smooth_elevation(track) # fields: smooth_elevation
    track = _calculate_grade(track)
    track = _calculate_misc(track) # metadata: jump_count

    return track




# TODO fields
# - accumulated_power # future improvement

# TODO metadata
# - total_ascent  # to be added for elevation correction handling
# - total_descent  # to be added for elevation correction handling
# - avg_vam  # to be added for elevation correction handling (and with ascent detection?)
# - start_latitude  # future improvement
# - start_longitude  # future improvement
# - end_latitude  # future improvement
# - end_longitude  # future improvement
# - avg_power  # future improvement
# - max_power  # future improvement
# - normalized_power  # future improvement
# - avg_respiration_rate  # future improvement
# - max_respiration_rate  # future improvement
# - min_respiration_rate  # future improvement
# - avg_right_torque_effectiveness  # future improvement
# - avg_left_torque_effectiveness  # future improvement
# - avg_right_pedal_smoothness  # future improvement
# - avg_left_pedal_smoothness  # future improvement
# - avg_heart_rate  # future improvement
# - max_heart_rate  # future improvement
# - avg_cadence  # future improvement
# - max_cadence  # future improvement
# - avg_temperature  # future improvement
# - max_temperature  # future improvement
# - min_temperature  # future improvement
