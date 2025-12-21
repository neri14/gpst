import argparse

from pathlib import Path

from ..data.processors import calculate_additional_data, fix_elevation
from ..data.load_track import load_track
from ..data.save_track import save_track
from ._tool_descriptor import Tool
from ._common import verify_in_path, verify_out_path
from ..utils.logger import logger


def main(in_path: Path, out_path: Path, accept: bool,
         dem_files: list[Path] | None, dem_crs: str | None,
         elevation_smoothing_window: int, grade_calculation_window: int) -> bool:
    if not verify_in_path(in_path):
        return False
    if not verify_out_path(out_path, accept):
        return False

    logger.info(f"Loading '{in_path}'...")
    track = load_track(in_path)

    if track is None:
        logger.error(f"Failed to load track from '{in_path}'.")
        return False

    if dem_files is not None and len(dem_files) > 0:
        logger.info("Fixing elevation data...")
        track = fix_elevation(track, dem_files, dem_crs, report_basepath=out_path.with_suffix(''))

    logger.info("Calculating additional data...")
    track = calculate_additional_data(track,
                                      elevation_smoothing_window=elevation_smoothing_window,
                                      grade_calculation_window=grade_calculation_window)

    logger.info(f"Storing '{out_path}'...")
    ok = save_track(track, out_path)

    if not ok:
        logger.error(f"Failed to save track to '{out_path}'.")
        return False

    logger.info("Processing completed successfully.")
    return True


def add_argparser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "process",
        help="Process GPS track file and write results to a GPX file."
    )
    parser.add_argument(
        "in_path",
        type=Path,
        metavar="IN_FILE",
        help="Path to input file (.gpx or .fit)."
    )
    parser.add_argument(
        "-o", "--output",
        dest="out_path",
        type=Path,
        metavar="OUT_FILE",
        required=True,
        help="Path to the output file.",
    )
    parser.add_argument(
        "-y", "--yes",
        action="store_true",
        dest="accept",
        help="Accept questions (e.g. overwrite existing output file).",
    )
    parser.add_argument(
        "--fix-elevation",
        nargs="+",
        dest="dem_files",
        type=Path,
        metavar="DEM_FILE",
        help="Correct elevation data using DEM files.",
    )
    parser.add_argument(
        "--dem-crs",
        dest="dem_crs",
        type=str,
        metavar="DEM_CRS",
        help="Coordinate reference system of the DEM files to be used if no CRS is specified in the files themselves (e.g. 'EPSG:4326').",
    )
    parser.add_argument(
        "--elevation-smoothing-window",
        dest="elevation_smoothing_window",
        type=int,
        metavar="METERS",
        help="Smoothing window for elevation data in meters (default: 100).",
        default=100
    )
    parser.add_argument(
        "--grade-calculation-window",
        dest="grade_calculation_window",
        type=int,
        metavar="METERS",
        help="Window size for grade calculation in meters (default: 100).",
        default=100
    )


tool = Tool(
    name="process",
    description="Process GPS track file and write results to a GPX file.",
    add_argparser=add_argparser,
    main=main
)
