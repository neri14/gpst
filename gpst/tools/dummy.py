import argparse
import logging

from ._tool_descriptor import Tool


def main(in_file: str) -> bool:
    logging.info(f"Dummy tool executed with input file: {in_file}")
    return True


def add_argparser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "dummy",
        help="Dummy tool."
    )
    parser.add_argument(
        "in_file",
        help="Path to the input file."
    )


tool = Tool(
    name="dummy",
    description="Dummy tool.",
    add_argparser=add_argparser,
    main=main
)
