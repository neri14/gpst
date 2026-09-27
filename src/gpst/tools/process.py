import argparse

from datetime import datetime, timedelta
from pathlib import Path

from ..data.processors import calculate_additional_data, fix_elevation
from ..data.load_track import load_track
from ..data.save_track import save_track
from ..data.processors import Racetrack, load_racetrack
from ._tool_descriptor import Tool
from ._common import verify_in_path, verify_out_path
from ..utils.helpers import to_string
from ..utils.logger import logger


HOTLAP_PADDING_SECONDS = 60.0


def main(in_path: Path, out_path: Path, accept: bool,
         dem_files: list[Path] | None, dem_crs: str | None,
         elevation_smoothing_window: int, grade_calculation_window: int,
         racetrack: Path | None,
         reference: Path | None, reference_best: bool,
         hotlap: bool) -> bool:
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
    if hotlap and racetrack is None:
        logger.error("The '--hotlap' option requires '--track' to be specified.")
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

    if hotlap:
        logger.info("Extracting hotlap...")

        hotlap_segment = Racetrack.find_fastest_lap_segment(track)
        if hotlap_segment is None:
            logger.error("No completed laps found in session; cannot extract hotlap.")
            return False

        lap_start = hotlap_segment.get('start_time')
        lap_end = hotlap_segment.get('end_time')
        if not isinstance(lap_start, datetime) or not isinstance(lap_end, datetime):
            logger.error("Fastest lap segment is missing start/end time; cannot extract hotlap.")
            return False

        window_start = lap_start - timedelta(seconds=HOTLAP_PADDING_SECONDS)
        window_end = lap_end + timedelta(seconds=HOTLAP_PADDING_SECONDS)

        logger.info(f"Hotlap is '{hotlap_segment.get('name')}' ({hotlap_segment['total_elapsed_time']:.3f}s). "
                    f"Trimming track to {to_string(window_start)} - {to_string(window_end)}.")
        track.trim_points(window_start, window_end)

        if reference_lap_time is not None:
            hotlap_time = hotlap_segment['total_elapsed_time']
            updated_reference_lap_time = min(hotlap_time, reference_lap_time)

            if updated_reference_lap_time < reference_lap_time:
                logger.info(f"Hotlap ({hotlap_time:.3f}s) beats reference lap ({reference_lap_time:.3f}s); "
                            f"personal best will update to {updated_reference_lap_time:.3f}s once the hotlap finishes.")

            # rtx_reference_lap should always be present, holding the reference lap time up to
            # the end of the hotlap, then switching to the new personal best (if any) afterwards.
            # rtx_reference_lap_delta (live timer/delta) should only exist during the hotlap itself.
            for ts, point in track.points_iter:
                point['rtx_reference_lap'] = reference_lap_time if ts <= lap_end else updated_reference_lap_time

                if not (lap_start <= ts <= lap_end):
                    point.pop('rtx_reference_lap_delta', None)

        # Whole-session metadata (bounds, totals, averages) is now stale; drop it and let
        # calculate_additional_data regenerate it from the remaining (trimmed) points only.
        preserved_metadata_keys = {'name', 'sport', 'sub_sport', 'sport_profile_name', 'device'}
        track.remove_metadata([key for key in track.metadata.keys() if key not in preserved_metadata_keys])

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
    parser.add_argument(
        "--hotlap",
        dest="hotlap",
        action="store_true",
        help=f"Trim output to the fastest lap of the session, plus {int(HOTLAP_PADDING_SECONDS)}s before and after (requires --track).",
    )


tool = Tool(
    name="process",
    description="Process GPS track file and write results to a GPX file.",
    add_argparser=add_argparser,
    main=main
)
