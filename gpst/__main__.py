import argparse
import logging
import os
import sys
from .tools import tools
from . import __version__


def setup_logger() -> None:
    log_level = logging.INFO
    dbg = os.getenv("DEBUG", "0")
    if dbg >= "1":
        log_level = logging.DEBUG
    elif dbg >= "2":
        log_level = logging.NOTSET
    logging.basicConfig(level=log_level, format="%(levelname)s: %(message)s")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="GPS Tools - A collection of tools to work with GPS track files."
    )

    subparsers = parser.add_subparsers(
        metavar="tool",
        dest="tool",
        help="Available tools:",
        required=True
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"GPS Tools {__version__}"
    )

    for tool in tools.values():
        tool.add_argparser(subparsers)

    return parser.parse_args()


def main() -> int:
    setup_logger()

    args = parse_args()
    tool_args = {k: v for k, v in vars(args).items() if k != 'tool'}

    success = tools[args.tool](**tool_args)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
