import math
import statistics
from datetime import datetime, timedelta

from ...utils.helpers import to_string, geo_distance
from ..track import Track, Value, latitude_t, longitude_t

from ...utils.logger import logger


MIN_GRADE_WINDOW = 0.4 # 40% grade window


def _calculate_times(track: Track) -> Track:
    """Calculate start_time, end_time, total_elapsed_time metadata and timer point field."""

    logger.debug("Calculating time for track points...")
    start_time: datetime | None = None
    end_time: datetime | None = None

    total_time: float | None = 0.0

    n: int = 0

    for ts, point in track.points_iter:
        if start_time is None:
            start_time = ts
        end_time = ts

        total_time = (ts - start_time).total_seconds() if start_time and ts else 0.0

        if total_time is not None and 'timer' not in point:
            logger.trace(f"Setting timer for point at {to_string(ts)} to {total_time} seconds")
            point['timer'] = total_time
            n += 1
    
    logger.debug(f"Calculated timer for {n} points.")
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

        if elapsed_time and 'total_elapsed_time' not in track.metadata:
            track.set_metadata('total_elapsed_time', elapsed_time)
            logger.info(f"Total elapsed time set to {elapsed_time} seconds")

        if not elapsed_time and 'total_elapsed_time' in track.metadata:
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

    n: int = 0
    n_t: int = 0

    for ts, point in track.points_iter:
        lat = point.get('latitude')
        lon = point.get('longitude')

        if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
            if last_lat is not None and last_lon is not None:
                total_distance += geo_distance(last_lat, last_lon, lat, lon)

            last_lat = lat
            last_lon = lon

            point['track_distance'] = total_distance
            n_t += 1
            logger.trace(f"Setting track_distance for point at {to_string(ts)} to {total_distance} meters")
            if 'distance' not in point:
                point['distance'] = total_distance
                n += 1
                logger.trace(f"Setting distance for point at {to_string(ts)} to {total_distance} meters")

    logger.debug(f"Calculated distances for {n} points and track distances for {n_t} points.")

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

    n: int = 0
    n_t: int = 0
    for ts, point in track.points_iter:
        distance = point.get('distance')
        timer = point.get('timer')

        if (isinstance(distance, (int, float)) and isinstance(timer, (int, float))):
            speed = (distance - last_distance) / (timer - last_time) if (timer - last_time) > 0 else 0.0

            point['track_speed'] = speed
            n_t += 1
            logger.trace(f"Setting track_speed for point at {to_string(ts)} to {speed} m/s")
            if 'speed' not in point:
                point['speed'] = speed
                n += 1
                logger.trace(f"Setting speed for point at {to_string(ts)} to {speed} m/s")

            if speed > max_track_speed:
                max_track_speed = speed
            
            if spd := point.get('speed'):
                if isinstance(spd, (int, float)) and spd > max_speed:
                    max_speed = spd

            last_distance = distance
            last_time = timer

    logger.debug(f"Calculated speeds for {n} points and track speeds for {n_t} points.")

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

    n: int = 0

    for ts, point in track.points_iter:
        if 'vertical_speed' not in point:
            elevation = point.get('elevation')
            timer = point.get('timer')

            if (isinstance(elevation, (int, float)) and
                isinstance(timer, (int, float))):

                if last_elevation is not None and last_time is not None:
                    v_speed = (elevation - last_elevation) / (timer - last_time) if (timer - last_time) > 0 else 0.0
                    point['vertical_speed'] = v_speed
                    n += 1
                    logger.trace(f"Setting vertical_speed for point at {to_string(ts)} to {v_speed} m/s")

                last_elevation = elevation
                last_time = timer

    logger.debug(f"Calculated vertical speeds for {n} points.")
    return track


def _calculate_power_averages(track: Track) -> Track:
    """Calculate power3s, power10s, power30s point fields using simple moving averages."""

    logger.debug("Calculating power averages for track points...")

    n: int = 0

    power: dict[datetime, float] = {}
    for timestamp, point in track.points_iter:
        pwr = point.get('power')
        if isinstance(pwr, (int, float)):
            power[timestamp] = pwr

        calculated = False
        if 'power3s' not in point:
            power3s = [p for ts,p in power.items() if ts > timestamp - timedelta(seconds=3)]
            if len(power3s) > 0:
                point['power3s'] = statistics.mean(power3s)
                calculated = True
                logger.trace(f"Setting power3s for point at {to_string(timestamp)} to {point['power3s']} watts")
        if 'power10s' not in point:
            power10s = [p for ts,p in power.items() if ts > timestamp - timedelta(seconds=10)]
            if len(power10s) > 0:
                point['power10s'] = statistics.mean(power10s)
                calculated = True
                logger.trace(f"Setting power10s for point at {to_string(timestamp)} to {point['power10s']} watts")
        if 'power30s' not in point:
            power30s = [p for ts,p in power.items() if ts > timestamp - timedelta(seconds=30)]
            if len(power30s) > 0:
                point['power30s'] = statistics.mean(power30s)
                calculated = True
                logger.trace(f"Setting power30s for point at {to_string(timestamp)} to {point['power30s']} watts")
        if calculated:
            n += 1

        power = {k: v for k, v in power.items() if k > timestamp - timedelta(seconds=30)}

    logger.debug(f"Calculated power averages for {n} points.")
    return track


def _calculate_smooth_elevation(track: Track, window_size: int) -> Track:
    """Calculate smooth_elevation point field using a simple moving average."""

    logger.debug("Calculating smooth elevation for track points...")

    n: int = 0

    for ts, point, window in track.sliding_window_iter(key='distance', size=window_size):
        if 'smooth_elevation' not in point:
            elevs = [p['elevation'] for p in window if 'elevation' in p and isinstance(p['elevation'], (int, float))]
            if len(elevs) > 0:
                point['smooth_elevation'] = statistics.mean(elevs)
                n += 1
                logger.trace(f"Setting smooth_elevation for point at {to_string(ts)} to {point['smooth_elevation']} meters")

    logger.debug(f"Calculated smooth_elevation for {n} points.")
    return track


def _calculate_grade(track: Track, window_size: int) -> Track:
    """Calculate grade point field."""

    logger.debug("Calculating grade...")

    min_grade_window = MIN_GRADE_WINDOW * window_size

    alt_key = 'smooth_elevation'
    dist_key = 'distance'

    max_grade: float | None = None
    min_grade: float | None = None

    n: int = 0

    for ts, point, window in track.sliding_window_iter(key=dist_key, size=window_size):
        grade = 0.0

        if 'grade' in point and isinstance(point['grade'], (int, float)):
            grade = point['grade']
        else:
            dist = point.get(dist_key)
            alt = point.get(alt_key)

            if dist is None or alt is None:
                logger.trace(f"Point at {to_string(ts)} missing {dist_key} or {alt_key} for grade calculation. Skipping.")
                continue

            try:
                altitudes = [(p[dist_key], p[alt_key]) for p in window if alt_key in p and dist_key in p]
                z1,y1 = altitudes[0]
                z2,y2 = altitudes[-1]

                if dist - z1 < min_grade_window/2:
                    continue # don't calculate grade if no points available at least half of min grade window - covers beginning of activity
                if z2 - dist < min_grade_window/2:
                    continue # don't calculate grade if no points available at least half of min grade window - covers end of activity

                z = z2 - z1
                y = y2 - y1

                x = math.sqrt(z**2 - y**2) # pythagoras (x**2 + y**2 = z**2 where z is distance delta and y is altitude delta)

                grade = (y / x) * 100.0
                point['grade'] = grade
                n += 1
                logger.trace(f"Setting grade for point at {to_string(ts)} to {grade} %")
            except Exception as e:
                logger.warning(f"Failed to calculate grade for point at {to_string(ts)}: {e}")
                continue

        if max_grade is None or grade > max_grade:
            max_grade = grade
        if min_grade is None or grade < min_grade:
            min_grade = grade

    logger.debug(f"Calculated grade for {n} points.")

    if isinstance(max_grade, (int, float)) and "max_grade" not in track.metadata:
        track.set_metadata('max_grade', max_grade)
        logger.info(f"Max grade set to {max_grade} %")
    if isinstance(min_grade, (int, float)) and "min_grade" not in track.metadata:
        track.set_metadata('min_grade', min_grade)
        logger.info(f"Min grade set to {min_grade} %")

    return track


def _calculate_ascent_descent(track: Track) -> Track:
    """Calculate total_ascent, total_descent, avg_vam metadata."""

    logger.debug("Calculating total ascent, total descent and avg_vam...")
    if 'total_ascent' in track.metadata and 'total_descent' in track.metadata and 'avg_vam' in track.metadata:
        logger.debug("Ascent/descent/vam metadata already present. Skipping calculation.")
        return track

    total_ascent: float = 0.0
    total_descent: float = 0.0
    time_ascending: timedelta = timedelta(0)

    last_ts: datetime | None = None
    last_elevation: float | None = None

    for ts, point in track.points_iter:
        elevation = point.get('smooth_elevation')
        distance = point.get('distance')

        if not isinstance(elevation, (int, float)) or not isinstance(distance, (int, float)):
            logger.error(f"Point at {to_string(ts)} missing elevation or distance cancelling ascent/descent calculation.")
            return track

        if last_elevation is not None and last_ts is not None:
            delta_elev = elevation - last_elevation

            if delta_elev > 0:
                # ascending
                total_ascent += delta_elev
                time_ascending += ((ts - last_ts) if last_ts else timedelta(0))
            elif delta_elev < 0:
                total_descent += abs(delta_elev)

        last_ts = ts
        last_elevation = elevation

    avg_vam = (total_ascent / time_ascending.total_seconds()) if time_ascending.total_seconds() > 0 else 0.0

    logger.info(f"Total ascent calculated: {total_ascent} meters.")
    logger.info(f"Total descent calculated: {total_descent} meters.")
    logger.info(f"Average VAM calculated: {avg_vam} m/s.")

    track.set_metadata('total_ascent', total_ascent)
    track.set_metadata('total_descent', total_descent)
    track.set_metadata('avg_vam', avg_vam)

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


def _calculate_segments(track: Track) -> Track:
    """Calculate missing segments metadata"""

    logger.debug("Calculating segments")

    for n,(_,segment) in enumerate(track.segments_iter):
        logger.debug(f"Calculating segment {n}...")

        start_ts = segment.get('start_time')
        end_ts = segment.get('end_time')
        if not isinstance(start_ts, datetime) or not isinstance(end_ts, datetime):
            logger.warning(f"Segment {n} missing start_time or end_time. Skipping segment calculation.")
            continue

        # Initialize calculated fields
        start_timer: float | None = None
        end_timer: float | None = None

        start_distance: float | None = None
        end_distance: float | None = None

        start_elevation: float | None = None
        end_elevation: float | None = None

        start_latitude: float | None = None
        start_longitude: float | None = None
        end_latitude: float | None = None
        end_longitude: float | None = None

        minlat: float | None = None
        minlon: float | None = None
        maxlat: float | None = None
        maxlon: float | None = None

        total_ascent: float = 0.0
        total_descent: float = 0.0
        time_ascending: timedelta = timedelta(0)

        last_ts: datetime | None = None
        last_elevation: float | None = None

        max_grade = None
        min_grade = None

        max_speed = None

        power_time_lst: list[float, timedelta] = []
        max_power = None
        power30s_lst = []

        cadences = []
        heart_rates = []

        for ts, point in track.points_iter:
            if ts < start_ts:
                continue
            if ts > end_ts:
                break

            # Collect data for segment
            timer = point.get('timer')
            if isinstance(timer, (int, float)):
                if start_timer is None:
                    start_timer = timer
                end_timer = timer

            distance = point.get('distance')
            if isinstance(distance, (int, float)):
                if start_distance is None:
                    start_distance = distance
                end_distance = distance
            
            elevation = point.get('elevation')
            if isinstance(elevation, (int, float)):
                if start_elevation is None:
                    start_elevation = elevation
                end_elevation = elevation

            latitude = point.get('latitude')
            longitude = point.get('longitude')
            if isinstance(latitude, (int, float)) and isinstance(longitude, (int, float)):
                if start_latitude is None and start_longitude is None:
                    start_latitude = latitude
                    start_longitude = longitude
                end_latitude = latitude
                end_longitude = longitude

                if minlat is None or latitude < minlat:
                    minlat = latitude
                if maxlat is None or latitude > maxlat:
                    maxlat = latitude
                if minlon is None or longitude < minlon:
                    minlon = longitude
                if maxlon is None or longitude > maxlon:
                    maxlon = longitude

            smooth_elevation = point.get('smooth_elevation')
            if isinstance(smooth_elevation, (int, float)) and isinstance(distance, (int, float)):
                if last_elevation is not None and last_ts is not None:
                    delta_elev = smooth_elevation - last_elevation

                    if delta_elev > 0:
                        # ascending
                        total_ascent += delta_elev
                        time_ascending += ((ts - last_ts) if last_ts else timedelta(0))
                    elif delta_elev < 0:
                        total_descent += abs(delta_elev)

            grade = point.get('grade')
            if isinstance(grade, (int, float)):
                if max_grade is None or grade > max_grade:
                    max_grade = grade
                if min_grade is None or grade < min_grade:
                    min_grade = grade

            speed = point.get('speed')
            if isinstance(speed, (int, float)):
                if max_speed is None or speed > max_speed:
                    max_speed = speed

            power = point.get('power')
            if isinstance(power, (int, float)):
                power_time_lst.append((power, (ts-last_ts) if last_ts else timedelta(0)))
                if max_power is None or power > max_power:
                    max_power = power

            power30s = point.get('power30s')
            if ts-start_ts >= timedelta(seconds=30) and isinstance(power30s, (int, float)):
                power30s_lst.append(power30s)

            heart_rate = point.get('heart_rate')
            if isinstance(heart_rate, (int, float)):
                heart_rates.append(heart_rate)

            cadence = point.get('cadence')
            if isinstance(cadence, (int, float)):
                cadences.append(cadence)

            last_ts = ts
            last_elevation = smooth_elevation

        # Set calculated segment fields if not already present
        if isinstance(start_timer, (int, float)) and 'start_timer' not in segment:
            segment['start_timer'] = start_timer
            logger.trace(f"Segment {n}: start_timer set to {start_timer} seconds")
        if isinstance(end_timer, (int, float)) and 'end_timer' not in segment:
            segment['end_timer'] = end_timer
            logger.trace(f"Segment {n}: end_timer set to {end_timer} seconds")
        if isinstance(start_timer, (int, float)) and isinstance(end_timer, (int,float)) and 'total_elapsed_time' not in segment:
            segment['total_elapsed_time'] = end_timer - start_timer
            logger.trace(f"Segment {n}: total_elapsed_time set to {segment['total_elapsed_time']} seconds")

        if isinstance(start_distance, (int, float)) and 'start_distance' not in segment:
            segment['start_distance'] = start_distance
            logger.trace(f"Segment {n}: start_distance set to {start_distance} meters")
        if isinstance(end_distance, (int, float)) and 'end_distance' not in segment:
            segment['end_distance'] = end_distance
            logger.trace(f"Segment {n}: end_distance set to {end_distance} meters")
        if isinstance(start_distance, (int, float)) and isinstance(end_distance, (int, float)) and 'total_distance' not in segment:
            segment['total_distance'] = end_distance - start_distance
            logger.trace(f"Segment {n}: total_distance set to {segment['total_distance']} meters")

        if isinstance(start_elevation, (int, float)) and 'start_elevation' not in segment:
            segment['start_elevation'] = start_elevation
            logger.trace(f"Segment {n}: start_elevation set to {start_elevation} meters")
        if isinstance(end_elevation, (int, float)) and 'end_elevation' not in segment:
            segment['end_elevation'] = end_elevation
            logger.trace(f"Segment {n}: end_elevation set to {end_elevation} meters")

        if (isinstance(start_latitude, (int, float)) and isinstance(start_longitude, (int, float)) and
            'start_latitude' not in segment and 'start_longitude' not in segment):
            segment['start_latitude'] = start_latitude
            segment['start_longitude'] = start_longitude
            logger.trace(f"Segment {n}: start_latitude set to {start_latitude}, start_longitude set to {start_longitude}")
        if (isinstance(end_latitude, (int, float)) and isinstance(end_longitude, (int, float)) and
            'end_latitude' not in segment and 'end_longitude' not in segment):
            segment['end_latitude'] = end_latitude
            segment['end_longitude'] = end_longitude
            logger.trace(f"Segment {n}: end_latitude set to {end_latitude}, end_longitude set to {end_longitude}")

        if (isinstance(minlat, (int, float)) and isinstance(minlon, (int, float)) and
            isinstance(maxlat, (int, float)) and isinstance(maxlon, (int, float)) and
            'minlat' not in segment and 'minlon' not in segment and
            'maxlat' not in segment and 'maxlon' not in segment):
            segment['minlat'] = minlat
            segment['minlon'] = minlon
            segment['maxlat'] = maxlat
            segment['maxlon'] = maxlon
            logger.trace(f"Segment {n}: minlat set to {minlat}, minlon set to {minlon}, maxlat set to {maxlat}, maxlon set to {maxlon}")
        
        if 'total_ascent' not in segment:
            segment['total_ascent'] = total_ascent
            logger.trace(f"Segment {n}: total_ascent set to {total_ascent} meters")
        if 'total_descent' not in segment:
            segment['total_descent'] = total_descent
            logger.trace(f"Segment {n}: total_descent set to {total_descent} meters")

        avg_vam = (total_ascent / time_ascending.total_seconds()) if time_ascending.total_seconds() > 0 else None
        if avg_vam is not None and 'avg_vam' not in segment:
            segment['avg_vam'] = avg_vam
            logger.trace(f"Segment {n}: avg_vam set to {avg_vam} m/s")

        if isinstance(max_grade, (int, float)) and 'max_grade' not in segment:
            segment['max_grade'] = max_grade
            logger.trace(f"Segment {n}: max_grade set to {max_grade} %")
        if isinstance(min_grade, (int, float)) and 'min_grade' not in segment:
            segment['min_grade'] = min_grade
            logger.trace(f"Segment {n}: min_grade set to {min_grade} %")

        if isinstance(start_distance, (int, float)) and isinstance(end_distance, (int, float)) and \
           isinstance(start_elevation, (int, float)) and isinstance(end_elevation, (int, float)) and \
           'grade' not in segment:
            dst = end_distance - start_distance
            elev = end_elevation - start_elevation
            x = math.sqrt(dst**2 - elev**2) # pythagoras (x**2 + y**2 = z**2 where z is distance delta and y is altitude delta)
            
            grade = (elev / x) * 100.0 if x > 0 else 0.0
            segment['avg_grade'] = grade
            logger.trace(f"Segment {n}: avg_grade set to {grade} %")

        if isinstance(max_speed, (int, float)) and 'max_speed' not in segment:
            segment['max_speed'] = max_speed
            logger.trace(f"Segment {n}: max_speed set to {max_speed} m/s")

        if isinstance(start_timer, (int, float)) and isinstance(end_timer, (int, float)) and \
           isinstance(start_distance, (int, float)) and isinstance(end_distance, (int, float)) and \
           'avg_speed' not in segment:
            time_delta = end_timer - start_timer
            distance_delta = end_distance - start_distance
            avg_speed = (distance_delta / time_delta) if time_delta > 0 else 0.0
            segment['avg_speed'] = avg_speed
            logger.trace(f"Segment {n}: avg_speed set to {avg_speed} m/s")

        if power_time_lst and 'avg_power' not in segment:
            total_power = sum(p * (dt.total_seconds()) for p,dt in power_time_lst)
            total_time = sum(dt.total_seconds() for _,dt in power_time_lst)
            avg_power = (total_power / total_time) if total_time > 0 else 0.0
            segment['avg_power'] = avg_power
            logger.trace(f"Segment {n}: avg_power set to {avg_power} watts")

        if isinstance(max_power, (int, float)) and 'max_power' not in segment:
            segment['max_power'] = max_power
            logger.trace(f"Segment {n}: max_power set to {max_power} watts")

        if power30s_lst and 'normalized_power' not in segment:
            normalized_power = statistics.mean([p**4 for p in power30s_lst]) ** (1/4)
            segment['normalized_power'] = normalized_power
            logger.trace(f"Segment {n}: normalized_power set to {normalized_power} watts")

        if heart_rates:
            if 'avg_heart_rate' not in segment:
                avg_heart_rate = statistics.mean(heart_rates)
                segment['avg_heart_rate'] = avg_heart_rate
                logger.trace(f"Segment {n}: avg_heart_rate set to {avg_heart_rate} bpm")
            if 'max_heart_rate' not in segment:
                max_heart_rate = max(heart_rates)
                segment['max_heart_rate'] = max_heart_rate
                logger.trace(f"Segment {n}: max_heart_rate set to {max_heart_rate} bpm")

        if cadences:
            if 'avg_cadence' not in segment:
                avg_cadence = statistics.mean(cadences)
                segment['avg_cadence'] = avg_cadence
                logger.trace(f"Segment {n}: avg_cadence set to {avg_cadence} rpm")
            if 'max_cadence' not in segment:
                max_cadence = max(cadences)
                segment['max_cadence'] = max_cadence
                logger.trace(f"Segment {n}: max_cadence set to {max_cadence} rpm")

    return track


def calculate_additional_data(track: Track, elevation_smoothing_window: int, grade_calculation_window: int) -> Track:
    track = _calculate_times(track) # metadata: start_time, end_time, total_elapsed_time, fields: timer
    track = _calculate_bounds(track) # metadata: minlat, minlon, maxlat, maxlon
    track = _calculate_distances(track) # metadata: total_distance, total_track_distance, fields: distance, track_distance
    track = _calculate_speeds(track) # metadata: avg_speed, avg_track_speed, max_speed, max_track_speed, fields: speed, track_speed
    track = _calculate_vspeeds(track) # fields: vertical_speed
    track = _calculate_power_averages(track) # fields: power3s, power10s, power30s
    track = _calculate_smooth_elevation(track, window_size=elevation_smoothing_window) # fields: smooth_elevation
    track = _calculate_grade(track, window_size=grade_calculation_window) # metadata: max_grade, min_grade, fields: grade
    track = _calculate_ascent_descent(track) # metadata: total_ascent, total_descent, avg_vam
    track = _calculate_misc(track) # metadata: jump_count
    track = _calculate_segments(track) # segments

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
