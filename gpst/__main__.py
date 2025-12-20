import argparse
import os
import sys
from .tools import tools
from . import __version__

from .utils.logger import setup_logger, logger


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

    try:
        logger.debug(f"Running tool '{args.tool}' with arguments: {tool_args}")
        success = tools[args.tool](**tool_args)
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        success = False
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
