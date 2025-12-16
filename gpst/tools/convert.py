import argparse
import logging

from pathlib import Path

from ..data.load_track import load_track
from ..data.save_track import save_track
from ._tool_descriptor import Tool
from ._common import verify_out_path


def main(in_file: str, out_file: str|None = None) -> bool:
    in_path = Path(in_file)

    if not in_path.exists():
        logging.error(f"Input file '{in_path}' does not exist.")
        return False
    
    if in_path.suffix.lower() != '.fit':
        logging.error(f"Input file '{in_path}' is not a FIT file.")
        return False

    if out_file is None:
        out_path = in_path.with_suffix('.gpx')
    else:
        out_path = Path(out_file)
    
    if not verify_out_path(out_path):
        return False

    logging.info(f"Converting '{in_path}' to '{out_path}'...")

    track = load_track(in_path)

    if track is None:
        logging.error(f"Failed to load track from '{in_path}'.")
        return False

    ok = save_track(track, out_path)

    if not ok:
        logging.error(f"Failed to save track to '{out_path}'.")
        return False

    logging.info("Conversion completed successfully.")
    return True


def add_argparser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "convert",
        help="Convert FIT file to GPX file."
    )
    parser.add_argument(
        "in_file",
        help="Path to input file."
    )
    parser.add_argument(
        "-o", "--output",
        dest="out_file",
        help="Path to the output file. If not provided, in file with .gpx extension is used.",
        default=None
    )

tool = Tool(
    name="convert",
    description="Convert FIT file to GPX file.",
    add_argparser=add_argparser,
    main=main
)
