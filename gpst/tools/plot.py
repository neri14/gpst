import argparse

import matplotlib as mpl
import matplotlib.pyplot as plt

from pathlib import Path
from typing import Generator
from matplotlib.typing import ColorType

from ._tool_descriptor import Tool
from ._common import verify_in_path, verify_out_path
from ..data.load_track import load_track
from ..data.track import point_fields
from ..utils.logger import logger


conversion_factors = {
    'distance':       0.001, # meters to kilometers
    'track_distance': 0.001, # meters to kilometers
    'speed':          3.6,   # m/s to km/h
    'track_speed':    3.6,   # m/s to km/h
}

converted_units = {
    'distance':       'km',
    'track_distance': 'km',
    'speed':          'km/h',
    'track_speed':    'km/h',
}

LINE_WIDTH = 1
POINT_SIZE = 3


def label(field: str) -> str:
    unit = converted_units.get(field, None)
    if unit is None:
        ftype = point_fields.get(field, None)
        if ftype is not None:
            unit = ftype.unit
    return f"{field} ({unit})" if unit else field


def read_data(path: Path, x_axis: str, y_axis: list[str], y_axis_right: list[str] = []) -> tuple[str, list, dict, dict] | None:
    if not verify_in_path(path):
        return None

    logger.info(f"Loading '{path}'...")
    track = load_track(path)

    if track is None:
        logger.error(f"Failed to load track from '{path}'.")
        return None

    xpoints: list = []
    ypoints: dict[str, list] = {y: [] for y in y_axis}
    ypoints_right: dict[str, list] = {y: [] for y in y_axis_right}

    for timestamp, point in sorted(track.points_iter):
        if x_axis not in point:
            logger.warning(f"X-axis field '{x_axis}' not found in point at {timestamp}. Skipping.")
            continue

        xpoints.append(point[x_axis])

        for y in y_axis:
            factor = conversion_factors.get(y, 1)
            if y not in point:
                logger.debug(f"Y-axis field '{y}' not found in point at {timestamp}. Appending None.")
                ypoints[y].append(None)
            else:
                val = point[y]
                if isinstance(val, (int, float)):
                    ypoints[y].append(val * factor)
                else:
                    ypoints[y].append(val)

        for y in y_axis_right:
            factor = conversion_factors.get(y, 1)
            if y not in point:
                logger.debug(f"Y-axis right field '{y}' not found in point at {timestamp}. Appending None.")
                ypoints_right[y].append(None)
            else:
                val = point[y]
                if isinstance(val, (int, float)):
                    ypoints_right[y].append(val * factor)
                else:
                    ypoints_right[y].append(val)

    return str(track.metadata.get('name', 'Unknown Activity')), xpoints, ypoints, ypoints_right



def colors() -> Generator[ColorType, None, None]:
    for c in mpl.color_sequences['tab10']:
        yield c
    for c in mpl.color_sequences['tab20']:
        yield c


def draw_plot(plot_type: str, plot_type_right: str, activity_name: str,
              x_axis: str, y_axis: list[str], y_axis_right: list[str],
              xpoints: list, ypoints: dict, ypoints_right: dict,
              output: str|None) -> None:
    fig, ax1 = plt.subplots()
    color = colors()

    if plot_type == 'line':
        for y in y_axis:
            ax1.plot(xpoints, ypoints[y], label=label(y), linewidth=LINE_WIDTH, color=next(color))
    elif plot_type == 'scatter':
        for y in y_axis:
            ax1.scatter(xpoints, ypoints[y], label=label(y), s=POINT_SIZE, color=next(color))

    ax1.set_xlabel(label(x_axis))
    ax1.set_ylabel(", ".join([label(y) for y in y_axis]))
    ax1.set_title(activity_name)
    ax1.legend(loc='upper left')

    ax2 = None
    if y_axis_right:
        ax2 = ax1.twinx()
        if plot_type_right == 'line':
            for y in y_axis_right:
                ax2.plot(xpoints, ypoints_right[y], label=label(y), linewidth=LINE_WIDTH, color=next(color))
        elif plot_type_right == 'scatter':
            for y in y_axis_right:
                ax2.scatter(xpoints, ypoints_right[y], label=label(y), s=POINT_SIZE, color=next(color))

        ax2.set_ylabel(", ".join([label(y) for y in y_axis_right]))
        ax2.legend(loc='upper right')

    ax1.grid(True)

    if output:
        plt.savefig(output)
    else:
        plt.show()


def main(path: Path,
         x_axis: str, y_axis: list[str], y_axis_right: list[str] = [],
         plot_type: str = 'line', plot_type_right: str = 'line',
         output: str|None = None) -> bool:
    logger.info(f"Plotting file: {path}")

    logger.debug(f"X-axis: {x_axis}")
    logger.debug(f"Y-axis: {y_axis}")
    logger.debug(f"Y-axis (right): {y_axis_right}")
    logger.debug(f"Plot type: {plot_type}")
    logger.debug(f"Plot type (right y-axis): {plot_type_right}")
    logger.debug(f"Output: {output}")

    try:
        data = read_data(path, x_axis, y_axis, y_axis_right)
        if data is not None:
            activity_name, xpoints, ypoints, ypoints_right = data
            draw_plot(plot_type, plot_type_right, activity_name, x_axis, y_axis, y_axis_right, xpoints, ypoints, ypoints_right, output)
    except Exception as e:
        logger.error(f"Failed to plot data: {e}")
        return False

    return True


def add_argparser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "plot",
        help="Plot data from the fit file."
    )
    parser.add_argument(
        "path",
        type=Path,
        metavar="FILE",
        help="Path to input file (.gpx or .fit)."
    )
    parser.add_argument(
        "-x", "--x-axis",
        dest="x_axis",
        help="Field to use for the x-axis.",
        required=True
    )
    parser.add_argument(
        "-y", "--y-axis",
        dest="y_axis",
        help="Field to use for the y-axis.",
        required=True,
        nargs='+'
    )
    parser.add_argument(
        "--y-right",
        dest="y_axis_right",
        help="Field to use for the y-axis on the right side.",
        nargs='+',
        default=[]
    )
    parser.add_argument(
        "-t", "--type",
        dest="plot_type",
        help="Plot type: line, scatter. Default is line.",
        choices=["line", "scatter"],
        default="line"
    )
    parser.add_argument(
        "--type-right",
        dest="plot_type_right",
        help="Plot type for right y-axis: line, scatter. Default is line.",
        choices=["line", "scatter"],
        default="line"
    )
    parser.add_argument(
        "-o", "--output",
        dest="output",
        help="Path to the output image file. If not provided, shows the plot interactively.",
        default=None
    )

tool = Tool(
    name="plot",
    description="Plot data from the fit file.",
    add_argparser=add_argparser,
    main=main
)
