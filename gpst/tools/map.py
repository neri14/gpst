import argparse
import rasterio # type: ignore[import-untyped]

import matplotlib.pyplot as plt

from enum import StrEnum
from pathlib import Path
from rasterio.merge import merge # type: ignore[import-untyped]
from rasterio.warp import transform # type: ignore[import-untyped]
from matplotlib.colors import LightSource

from ._tool_descriptor import Tool
from ._common import verify_in_path
from ..data.load_track import load_track
from ..utils.logger import logger

WGS_84_EPSG = 'EPSG:4326' # WGS 84 - normal Latitude/Longitude
DEFAULT_CRS = 'EPSG:3857' # Web Mercator
DEFAULT_WIDTH = 4096
DEFAULT_HEIGHT = 4096


class TrimMode(StrEnum):
    TIGHT = 'tight'
    BOX = 'box'


def _get_track_bounds(track_x: list[float | None], track_y: list[float | None], trim: TrimMode) -> tuple[float, float, float, float] | None:
    valid_x = [x for x in track_x if x is not None]
    valid_y = [y for y in track_y if y is not None]
    if valid_x and valid_y:
        minx, maxx = min(valid_x), max(valid_x)
        miny, maxy = min(valid_y), max(valid_y)

        dx = maxx - minx
        dy = maxy - miny

        if trim == TrimMode.BOX:
            dmax = max(dx, dy)
            midx, midy = (minx + maxx) / 2, (miny + maxy) / 2
            minx, maxx = midx - dmax / 2, midx + dmax / 2
            miny, maxy = midy - dmax / 2, midy + dmax / 2
            dx = dy = dmax

        if dx == 0:
            dx = 1
        if dy == 0:
            dy = 1
        
        padding = max(dx, dy) * 0.05

        left = minx - padding
        right = maxx + padding
        bottom = miny - padding
        top = maxy + padding

        return left, right, bottom, top
    return None


def main(path: Path, dem_files: list[Path] | None = None, dem_crs: str | None = None, output: Path | None = None,
         width: int = DEFAULT_WIDTH, height: int = DEFAULT_HEIGHT, line_width: float = 2.5,
         show_title: bool = False, trim: TrimMode | None = None) -> bool:
    if not verify_in_path(path):
        return False

    px = 1/plt.rcParams['figure.dpi']
    fig, ax = plt.subplots(figsize=(width*px, height*px))

    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
    ax.set_axis_off()

    crs = rasterio.CRS({'init': dem_crs if dem_crs is not None else DEFAULT_CRS}) 

    if dem_files:
        dem_datasets = []
        logger.info("Loading DEM files...")
        for dem_file in dem_files:
            src = rasterio.open(dem_file)
            dem_datasets.append(src)

            if src.crs is not None:
                crs = src.crs

        logger.info("Merging DEM files...")
        mosaic, out_trans = merge(dem_datasets)

        logger.info("Closing DEM files...")
        for src in dem_datasets:
            src.close()

        logger.info("Generating shaded relief...")
        elevation_data = mosaic[0]

        # Create a LightSource for the shaded relief effect
        ls = LightSource(azdeg=315, altdeg=45) # azdeg: Source azimuth (0-360, 315 is NW), altdeg: Source altitude (0-90)

        # Calculate hillshade
        shaded_relief = ls.hillshade(elevation_data, vert_exag=2) # vert_exag: Vertical exaggeration (increase to make relief more pronounced)

        # Calculate the extent for the plot [left, right, bottom, top]
        # out_trans is an Affine transform
        h, w = elevation_data.shape
        left = out_trans[2]
        top = out_trans[5]
        right = left + (w * out_trans[0])
        bottom = top + (h * out_trans[4]) # out_trans[4] is usually negative

        ax.imshow(
            shaded_relief, 
            cmap='gray', 
            extent=(left, right, bottom, top), 
            origin='upper'
        )

    logger.info(f"Loading track from '{path}'...")
    track = load_track(path)

    if track is None:
        logger.error(f"Failed to load track from '{path}'.")
    else:
        if show_title:
            title = str(track.metadata.get('name', 'Unknown Activity'))
            ax.text(0.5, 1, title,
                    transform=ax.transAxes,
                    ha='center', va='top',
                    fontsize=20, color='black',
                    zorder=20
            )

        track_x: list = []
        track_y: list = []

        for _, point in track.points_iter:
            lat = point.get('latitude')
            lon = point.get('longitude')

            if not isinstance(lat, float) or not isinstance(lon, float):
                logger.warning(f"Point missing location data; skipping.")
                track_x.append(None)
                track_y.append(None)
            else:
                xs, ys = transform(WGS_84_EPSG, crs, [lon], [lat])
                track_x.append(xs[0])
                track_y.append(ys[0])

        logger.info("Plotting track...")
        ax.plot(track_x, track_y, color='red', linewidth=line_width, alpha=0.8, zorder=10)

        if trim is not None:
            bounds = _get_track_bounds(track_x, track_y, trim)
            if bounds is not None:
                left, right, bottom, top = bounds
                ax.set_xlim(left, right)
                ax.set_ylim(bottom, top)

        # If no DEM is present, ensure the plot has a reasonable aspect ratio
        if not dem_files:
            ax.set_aspect('equal')

    if output:
        logger.info(f"Saving map to '{output}'...")
        plt.savefig(output, bbox_inches='tight', pad_inches=0, dpi=plt.rcParams['figure.dpi'])
    else:
        logger.info("Displaying map...")
        plt.show()

    return True


def add_argparser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "map",
        help="Draw map of input file."
    )
    parser.add_argument(
        "path",
        type=Path,
        metavar="FILE",
        help="Path to input file (.gpx or .fit)."
    )
    parser.add_argument(
        "--dem",
        nargs="+",
        dest="dem_files",
        type=Path,
        metavar="DEM_FILE",
        help="DEM files to use as background elevation data.",
    )
    parser.add_argument(
        "--dem-crs",
        dest="dem_crs",
        type=str,
        metavar="DEM_CRS",
        help="Coordinate reference system of the DEM files to be used if no CRS is specified in the files themselves (e.g. 'EPSG:4326').",
    )
    parser.add_argument(
        "--width",
        dest="width",
        type=int,
        help=f"Width of the output image in pixels (default: {DEFAULT_WIDTH}).",
        default=DEFAULT_WIDTH
    )
    parser.add_argument(
        "--height",
        dest="height",
        type=int,
        help=f"Height of the output image in pixels (default: {DEFAULT_HEIGHT}).",
        default=DEFAULT_HEIGHT
    )
    parser.add_argument(
        "--line-width",
        dest="line_width",
        type=float,
        help="Width of the track line (default: 2.5).",
        default=2.5
    )
    parser.add_argument(
        "-o", "--output",
        dest="output",
        type=Path,
        help="Path to the output image file. If not provided, shows the map interactively.",
        default=None
    )
    parser.add_argument(
        "--show-title",
        dest="show_title",
        action="store_true",
        help="Show the activity name as the title of the map.",
        default=False
    )
    parser.add_argument(
        "--trim",
        dest="trim",
        help="Trim the map to the track bounds.",
        type=TrimMode,
        choices=[TrimMode.TIGHT, TrimMode.BOX],
        default=None
    )

tool = Tool(
    name="map",
    description="Draw map of input file.",
    add_argparser=add_argparser,
    main=main
)
