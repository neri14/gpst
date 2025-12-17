import argparse
import logging

from pathlib import Path

from ..data.load_track import load_track
from ..data.save_track import save_track
from ._tool_descriptor import Tool
from ._common import verify_in_path, verify_out_path


def main(in_path: Path, out_path: Path) -> bool:
    if not verify_in_path(in_path):
        return False
    if not verify_out_path(out_path):
        return False

    logging.info(f"Loading '{in_path}'...")
    track = load_track(in_path)

    if track is None:
        logging.error(f"Failed to load track from '{in_path}'.")
        return False

    #TODO if any of processing options were selected, process the track here
    # logging.info(f"Processing track {track}...")

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
    # parser.add_argument(
    #     "--calculate",
    #     nargs="+",
    #     dest="calculate_fields",
    #     help="Calculate additional fields ('all' for all additional fields).",
    # )
    # parser.add_argument(
    #     "--fix-altitude",
    #     nargs="+",
    #     dest="dem_files",
    #     type=str,
    #     metavar="DEM_FILE",
    #     help="Correct elevation data using DEM files.",
    # )
    # parser.add_argument(
    #     "--trim-begin",
    #     dest="trim_begin",
    #     type=float,
    #     metavar="SECONDS",
    #     help="Trim track start seconds.",
    # )
    # parser.add_argument(
    #     "--trim-end",
    #     dest="trim_end",
    #     type=float,
    #     metavar="SECONDS",
    #     help="Trim track end seconds.",
    # )
    # parser.add_argument(
    #     "--add-metadata",
    #     nargs="+",
    #     dest="add_metadata",
    #     type=str,
    #     metavar="KEY=VALUE",
    #     help="Add metadata to the track (format: KEY=VALUE).",
    # )
    # parser.add_argument(
    #     "--remove-metadata",
    #     nargs="+",
    #     dest="remove_metadata",
    #     type=str,
    #     metavar="KEY",
    #     help="Remove specified metadata from the track.",
    # )
    parser.add_argument(
        "-o", "--output",
        dest="out_path",
        type=Path,
        metavar="OUT_FILE",
        required=True,
        help="Path to the output file.",
    )


tool = Tool(
    name="process",
    description="Process GPS track file and write results to a GPX file.",
    add_argparser=add_argparser,
    main=main
)
