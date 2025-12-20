import argparse
import logging

from pathlib import Path

from ..data.processors import calculate_additional_data

from ..data.load_track import load_track
from ..data.save_track import save_track
from ._tool_descriptor import Tool
from ._common import verify_in_path, verify_out_path


def main(in_path: Path, out_path: Path, accept: bool) -> bool:
    if not verify_in_path(in_path):
        return False
    if not verify_out_path(out_path, accept):
        return False

    logging.info(f"Loading '{in_path}'...")
    track = load_track(in_path)

    if track is None:
        logging.error(f"Failed to load track from '{in_path}'.")
        return False


    #TODO if fix elevation - fix it here and remove all fields related to elevation


    logging.info("Calculating additional data...")
    track = calculate_additional_data(track)

    logging.info(f"Storing '{out_path}'...")
    ok = save_track(track, out_path)

    if not ok:
        logging.error(f"Failed to save track to '{out_path}'.")
        return False

    logging.info("Processing completed successfully.")
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
    # parser.add_argument(
    #     "--fix-elevation",
    #     nargs="+",
    #     dest="dem_files",
    #     type=str,
    #     metavar="DEM_FILE",
    #     help="Correct elevation data using DEM files.",
    # )


tool = Tool(
    name="process",
    description="Process GPS track file and write results to a GPX file.",
    add_argparser=add_argparser,
    main=main
)
