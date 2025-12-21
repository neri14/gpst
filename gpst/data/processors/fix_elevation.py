import csv
import matplotlib as mpl
import matplotlib.pyplot as plt
import rasterio # type: ignore[import-untyped]

from matplotlib.typing import ColorType
from pathlib import Path
from rasterio.warp import transform # type: ignore[import-untyped]
from typing import Generator

from ..track import Track
from ...utils.logger import logger
from ...utils.helpers import to_string


class ElevationReference:
    def __init__(self, dem_paths: list[Path], dem_crs: str | None) -> None:
        self.dem_paths = dem_paths
        self.crs = rasterio.CRS({'init': dem_crs if dem_crs is not None else 'EPSG:4326'}) 

        self.known_crss: set[str] = set()
        self.known_crss.add(self.crs.to_string())

        self.dem_files = self._load_dem_files()


    def __del__(self) -> None:
        for f in self.dem_files:
            f.close()


    def get_elevation(self, lat: float, lon: float) -> float | None:
        coords: dict[str, tuple[float, float]] = {}

        elevation = None
        for crs_str in self.known_crss:
            if crs_str != "EPSG:4326":
                xs, ys = transform('EPSG:4326', crs_str, [lon], [lat])
                coords[crs_str] = (xs[0], ys[0])
            else:
                coords[crs_str] = (lon, lat)


        for dem in self.dem_files:
            crs = dem.crs if dem.crs is not None else self.crs

            if crs.to_string() not in coords:
                raise RuntimeError(f"CRS '{crs.to_string()}' of DEM file not known.")
        
            x, y = coords[crs.to_string()]
            minx, miny, maxx, maxy = dem.bounds
            if not (minx <= x <= maxx and miny <= y <= maxy):
                logger.trace(f"Coordinates ({x}, {y}) out of bounds for DEM file with bounds ({minx}, {miny}, {maxx}, {maxy}); skipping.")
                continue

            val = next(dem.sample([(x, y)]))[0]

            if dem.nodata is not None and val == dem.nodata:
                logger.trace(f"Coordinates ({x}, {y}) in DEM file have no data value; skipping.")
                continue

            elevation = float(val)
            logger.trace(f"Found elevation {elevation} for coordinates ({lat}, {lon}) in DEM file.")
            break

        # Return elevation for given latitude and longitude
        return elevation
    

    def _load_dem_files(self) -> list:
        dem_files = []

        for path in self.dem_paths:
            dem_file = rasterio.open(path)
            if dem_file.crs is not None:
                print(dem_file.crs)
                self.known_crss.add(dem_file.crs.to_string())
            if dem_file.crs is None and self.crs is None:
                raise ValueError(f"DEM file '{path}' has no CRS defined and no CRS was provided.")

            dem_files.append(dem_file)

        return dem_files


def _generate_report_csv(report: list[dict], path: Path) -> None:
    logger.info(f"Generating elevation fix report CSV at '{path}'...")
    with path.open('w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['timestamp', 'latitude', 'longitude', 'distance', 'old_elevation', 'new_elevation', 'correction']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for row in report:
            writer.writerow({
                'timestamp': row['timestamp'],
                'latitude': row['latitude'],
                'longitude': row['longitude'],
                'distance': row['distance'],
                'old_elevation': row['old_elevation'],
                'new_elevation': row['new_elevation'],
                'correction': row['correction']
            })


def _generate_report_png(report: list[dict], path: Path) -> None:
    logger.info(f"Generating elevation fix report PNG at '{path}'...")

    def colors() -> Generator[ColorType, None, None]:
        for c in mpl.color_sequences['tab10']:
            yield c

    x = [row['distance']/1000 for row in report]
    y1 = [row['old_elevation'] for row in report]
    y2 = [row['new_elevation'] for row in report]
    yright = [row['correction'] for row in report]

    fig, ax1 = plt.subplots(figsize=(10, 6))
    color = colors()

    ax1.plot(x, y1, label='old_elevation', linewidth=1, color=next(color))
    ax1.plot(x, y2, label='new_elevation', linewidth=1, color=next(color))
    ax1.set_xlabel('Distance (km)')
    ax1.set_ylabel('Elevation (m)')
    # ax1.legend(loc='outside upper left')
    ax1.legend(loc='upper left', bbox_to_anchor=(-0.05, 1.15), borderaxespad=0.)

    ax2 = ax1.twinx()
    ax2.plot(x, yright, label='correction', linewidth=1, color=next(color))
    ax2.set_ylabel('Elevation Correction (m)')
    # ax2.legend(loc='outside upper right')
    ax2.legend(loc='upper right', bbox_to_anchor=(1.05, 1.15), borderaxespad=0.)

    plt.grid(True)
    plt.savefig(path, bbox_inches='tight')
    plt.close(fig)


def fix_elevation(track: Track, dem_files: list[Path], dem_crs: str|None, report_basepath: Path | None = None) -> Track:
    report: list[dict] = []

    logger.debug("Loading DEM files for elevation reference.")
    reference: ElevationReference | None = None
    try:
        reference = ElevationReference(dem_files, dem_crs)
    except Exception as e:
        logger.error(f"Failed to load DEM files: {e}")
        return track

    if reference is None:
        logger.error("No valid elevation reference could be created from DEM files.")
        return track

    cnt_fixed = 0
    cnt_not_fixed = 0
    correction_sum = 0.0
    correction_cnt = 0
    correction_max = 0.0

    logger.info("Correcting elevation points.")
    for dt,point in track.points_iter:
        lat = point.get('latitude')
        lon = point.get('longitude')

        if not isinstance(lat, float) or not isinstance(lon, float):
            logger.warning(f"Point at {to_string(dt)} missing location data; skipping elevation fix.")
            continue

        old_elevation = point.get('elevation')
        new_elevation = reference.get_elevation(lat, lon)

        if new_elevation is not None:
            logger.trace(f"Fixing elevation at {to_string(dt)} from {to_string(old_elevation)} to {to_string(new_elevation)}.")
            point['elevation'] = new_elevation
            cnt_fixed += 1
        else:
            cnt_not_fixed += 1

        #cleanup elevation dependant data
        if 'smooth_elevation' in point:
            del point['smooth_elevation']
        if 'grade' in point:
            del point['grade']
        if 'vertical_speed' in point:
            del point['vertical_speed']


        correction = None
        if isinstance(new_elevation, (int, float)) and isinstance(old_elevation, (int, float)):
            correction = new_elevation - old_elevation
            correction_sum += correction
            correction_cnt += 1
            if abs(correction) > abs(correction_max):
                correction_max = correction

        report.append({
            'timestamp': dt,
            'latitude': lat,
            'longitude': lon,
            'distance': point.get('distance'),
            'old_elevation': old_elevation,
            'new_elevation': new_elevation,
            'correction': correction
        })

    logger.info(f"Elevation correction completed: {cnt_fixed} points fixed, {cnt_not_fixed} points not fixed.")
    logger.info(f"Average elevation correction: {correction_sum / correction_cnt if correction_cnt > 0 else 0.0} m over {correction_cnt} points.")
    logger.info(f"Maximal elevation correction: {correction_max} m.")

    logger.info("Removing metadata dependant on elevation.")
    if 'total_ascent' in track.metadata:
        del track.metadata['total_ascent']
    if 'total_descent' in track.metadata:
        del track.metadata['total_descent']
    if 'max_grade' in track.metadata:
        del track.metadata['max_grade']
    if 'min_grade' in track.metadata:
        del track.metadata['min_grade']
    if 'avg_vam' in track.metadata:
        del track.metadata['avg_vam']

    if report_basepath is not None:
        _generate_report_csv(report, report_basepath.with_suffix('.elevation_fix.csv'))
        _generate_report_png(report, report_basepath.with_suffix('.elevation_fix.png'))

    return track
