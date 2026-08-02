import argparse

from pathlib import Path

from ..data.processors import calculate_additional_data, fix_elevation
from ..data.load_track import load_track
from ..data.save_track import save_track
from ..data.processors import load_racetrack
from ._tool_descriptor import Tool
from ._common import verify_in_path, verify_out_path
from ..utils.logger import logger


def main(in_path: Path, out_path: Path, accept: bool,
         dem_files: list[Path] | None, dem_crs: str | None,
         elevation_smoothing_window: int, grade_calculation_window: int,
         racetrack: Path | None,
         reference: Path | None, reference_best: bool) -> bool:
    if not verify_in_path(in_path):
        return False
    if not verify_out_path(out_path, accept):
        return False

    if reference is not None and racetrack is None:
        logger.error("The '--reference' option requires '--track' to be specified.")
        return False
    if reference_best and racetrack is None:
        logger.error("The '--reference-best' option requires '--track' to be specified.")
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
    
    if racetrack is not None:
        logger.info(f"Loading racetrack from '{racetrack}'...")

        try:
            rt = load_racetrack(racetrack)
            if rt is None:
                logger.error(f"Failed to load racetrack from '{racetrack}'.")
                return False
        except Exception as e:
            logger.error(f"Error loading racetrack from '{racetrack}': {e}")
            return False

        reference_lap_time: float | None = None
        reference_lap_progress: list[tuple[float, float]] | None = None

        if reference is not None:
            logger.info(f"Loading reference track from '{reference}'...")
            ref_track = load_track(reference)
            if ref_track is None:
                logger.error(f"Failed to load reference track from '{reference}'.")
                return False

            logger.info("Processing reference track...")
            ref_track = calculate_additional_data(ref_track,
                                                  elevation_smoothing_window=elevation_smoothing_window,
                                                  grade_calculation_window=grade_calculation_window)
            ref_track = rt.calculate_racetrack_data(ref_track)

            ref_result = rt.extract_best_lap_progress(ref_track)
            if ref_result is None:
                logger.error(f"No valid laps found in reference track '{reference}'.")
                return False

            reference_lap_time, reference_lap_progress = ref_result
            logger.info(f"Reference best lap time: {reference_lap_time:.3f}s")

        logger.info(f"Calculating racetrack data using '{racetrack}'...")
        track = rt.calculate_racetrack_data(track,
                                            reference_lap_time=reference_lap_time,
                                            reference_lap_progress=reference_lap_progress,
                                            reference_best=reference_best)

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
        help="Path to input file (.gpx, .fit, .vbo)."
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
    parser.add_argument(
        "--track",
        dest="racetrack",
        type=Path,
        metavar="TRACK_FILE",
        help="Path to a track file to be used for racetrack calculations",
    )
    parser.add_argument(
        "--reference",
        dest="reference",
        type=Path,
        metavar="REF_FILE",
        help="Path to an input file (.gpx, .fit, .vbo) to use as reference lap (requires --track).",
    )
    parser.add_argument(
        "--reference-best",
        dest="reference_best",
        action="store_true",
        help="Update the reference lap if the current session produces a faster lap (requires --track and --reference).",
    )


tool = Tool(
    name="process",
    description="Process GPS track file and write results to a GPX file.",
    add_argparser=add_argparser,
    main=main
)
