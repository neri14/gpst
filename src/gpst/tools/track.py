import argparse
import math
from dataclasses import dataclass
from pathlib import Path
from statistics import median

from ._common import verify_in_path
from ._tool_descriptor import Tool
from ..data.load_track import load_track
from ..utils.helpers import geo_distance
from ..utils.logger import logger

EARTH_RADIUS = 6372797.5605
DEG_TO_RAD = math.pi / 180.0

GateSegment = tuple[tuple[float, float], tuple[float, float]]


@dataclass(frozen=True)
class CrossingEvent:
    segment_index: int
    t: float
    gate: str
    point: tuple[float, float]


@dataclass(frozen=True)
class LapCandidate:
    points: list[tuple[float, float]]
    length_m: float



def _to_local_xy(lat: float, lon: float, ref_lat: float, ref_lon: float) -> tuple[float, float]:
    x = (lon - ref_lon) * math.cos(ref_lat * DEG_TO_RAD) * EARTH_RADIUS * DEG_TO_RAD
    y = (lat - ref_lat) * EARTH_RADIUS * DEG_TO_RAD
    return x, y



def _to_lat_lon(x: float, y: float, ref_lat: float, ref_lon: float) -> tuple[float, float]:
    lat = y / (EARTH_RADIUS * DEG_TO_RAD) + ref_lat
    cos_ref = math.cos(ref_lat * DEG_TO_RAD)
    if abs(cos_ref) < 1e-12:
        lon = ref_lon
    else:
        lon = x / (EARTH_RADIUS * DEG_TO_RAD * cos_ref) + ref_lon
    return lat, lon



def _cross_2d(ax: float, ay: float, bx: float, by: float) -> float:
    return ax * by - ay * bx



def _segment_intersection(
    a1: tuple[float, float],
    a2: tuple[float, float],
    b1: tuple[float, float],
    b2: tuple[float, float],
) -> tuple[float, tuple[float, float]] | None:
    ref_lat = (a1[0] + a2[0] + b1[0] + b2[0]) / 4.0
    ref_lon = (a1[1] + a2[1] + b1[1] + b2[1]) / 4.0

    ax1, ay1 = _to_local_xy(a1[0], a1[1], ref_lat, ref_lon)
    ax2, ay2 = _to_local_xy(a2[0], a2[1], ref_lat, ref_lon)
    bx1, by1 = _to_local_xy(b1[0], b1[1], ref_lat, ref_lon)
    bx2, by2 = _to_local_xy(b2[0], b2[1], ref_lat, ref_lon)

    rx = ax2 - ax1
    ry = ay2 - ay1
    sx = bx2 - bx1
    sy = by2 - by1

    denom = _cross_2d(rx, ry, sx, sy)
    if abs(denom) < 1e-9:
        return None

    qpx = bx1 - ax1
    qpy = by1 - ay1

    t = _cross_2d(qpx, qpy, sx, sy) / denom
    u = _cross_2d(qpx, qpy, rx, ry) / denom

    if not (0.0 <= t <= 1.0 and 0.0 <= u <= 1.0):
        return None

    ix = ax1 + t * rx
    iy = ay1 + t * ry
    lat, lon = _to_lat_lon(ix, iy, ref_lat, ref_lon)
    return t, (lat, lon)



def _extract_points(in_path: Path) -> list[tuple[float, float]]:
    track = load_track(in_path)
    if track is None:
        raise ValueError(f"Failed to load track from '{in_path}'.")

    points: list[tuple[float, float]] = []
    for _, point in track.points_iter:
        lat = point.get("lat")
        lon = point.get("lon")
        if isinstance(lat, float) and isinstance(lon, float):
            points.append((lat, lon))

    if len(points) < 3:
        raise ValueError("Input data has too few valid GPS points.")

    return points



def _collect_crossings(points: list[tuple[float, float]], gates: dict[str, GateSegment]) -> list[CrossingEvent]:
    events: list[CrossingEvent] = []

    for i in range(len(points) - 1):
        p1 = points[i]
        p2 = points[i + 1]

        segment_events: list[CrossingEvent] = []
        for gate_name, gate in gates.items():
            intersection = _segment_intersection(p1, p2, gate[0], gate[1])
            if intersection is None:
                continue

            t, crossing = intersection
            segment_events.append(
                CrossingEvent(
                    segment_index=i,
                    t=t,
                    gate=gate_name,
                    point=crossing,
                )
            )

        segment_events.sort(key=lambda event: event.t)
        events.extend(segment_events)

    return events



def _polyline_length(points: list[tuple[float, float]]) -> float:
    return sum(
        geo_distance(a[0], a[1], b[0], b[1])
        for a, b in zip(points, points[1:])
    )



def _build_full_laps(
    points: list[tuple[float, float]],
    events: list[CrossingEvent],
    min_lap_points: int,
    min_lap_length_m: float,
) -> list[LapCandidate]:
    finish_indices = [i for i, event in enumerate(events) if event.gate == "finish"]
    if len(finish_indices) < 2:
        raise ValueError("Not enough finish line crossings to build laps.")

    laps: list[LapCandidate] = []

    for a, b in zip(finish_indices, finish_indices[1:]):
        start_event = events[a]
        end_event = events[b]

        if end_event.segment_index < start_event.segment_index:
            continue

        gate_events = events[a + 1:b]
        is_pit_lap = any(event.gate in {"pit_entry", "pit_exit"} for event in gate_events)
        if is_pit_lap:
            continue

        lap_points = [start_event.point]
        lap_points.extend(points[start_event.segment_index + 1:end_event.segment_index + 1])
        lap_points.append(end_event.point)

        if len(lap_points) < min_lap_points:
            continue

        lap_len = _polyline_length(lap_points)
        if lap_len < min_lap_length_m:
            continue

        laps.append(LapCandidate(points=lap_points, length_m=lap_len))

    if not laps:
        raise ValueError("No valid full laps found (finish-to-finish without pit entry/exit).")

    return laps



def _resample_polyline(
    points: list[tuple[float, float]],
    sample_count: int,
) -> list[tuple[float, float]]:
    if sample_count < 3:
        raise ValueError("sample_count must be at least 3.")

    cumulative = [0.0]
    for a, b in zip(points, points[1:]):
        cumulative.append(cumulative[-1] + geo_distance(a[0], a[1], b[0], b[1]))

    total = cumulative[-1]
    if total <= 0.0:
        raise ValueError("Cannot resample lap with zero length.")

    targets = [total * i / sample_count for i in range(sample_count)]

    result: list[tuple[float, float]] = []
    segment_index = 0

    for target in targets:
        while segment_index < len(cumulative) - 2 and cumulative[segment_index + 1] < target:
            segment_index += 1

        d0 = cumulative[segment_index]
        d1 = cumulative[segment_index + 1]
        p0 = points[segment_index]
        p1 = points[segment_index + 1]

        if d1 <= d0:
            ratio = 0.0
        else:
            ratio = (target - d0) / (d1 - d0)

        lat = p0[0] + (p1[0] - p0[0]) * ratio
        lon = p0[1] + (p1[1] - p0[1]) * ratio
        result.append((lat, lon))

    return result



def _build_median_line(laps: list[LapCandidate], sample_count: int) -> list[tuple[float, float]]:
    sampled_laps = [_resample_polyline(lap.points, sample_count) for lap in laps]

    median_points: list[tuple[float, float]] = []
    for index in range(sample_count):
        lats = [lap[index][0] for lap in sampled_laps]
        lons = [lap[index][1] for lap in sampled_laps]
        median_points.append((median(lats), median(lons)))

    return median_points



def _fmt(value: float) -> str:
    text = f"{value:.15g}"
    if text == "-0":
        return "0"
    return text



def _gate_to_text(gate: GateSegment) -> str:
    return f"{_fmt(gate[0][0])} {_fmt(gate[0][1])} {_fmt(gate[1][0])} {_fmt(gate[1][1])}"



def _write_track_file(
    out_path: Path,
    finish_line: GateSegment,
    pit_entry: GateSegment | None,
    pit_exit: GateSegment | None,
    track_points: list[tuple[float, float]],
) -> None:
    lines: list[str] = []

    lines.append("[finish_line]")
    lines.append(_gate_to_text(finish_line))
    lines.append("")

    if pit_entry is not None:
        lines.append("[pit_entry]")
        lines.append(_gate_to_text(pit_entry))
        lines.append("")

    if pit_exit is not None:
        lines.append("[pit_exit]")
        lines.append(_gate_to_text(pit_exit))
        lines.append("")

    lines.append("[track]")
    for lat, lon in track_points:
        lines.append(f"{_fmt(lat)} {_fmt(lon)}")

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")



def _verify_out_path(out_path: Path, accept: bool) -> bool:
    if out_path.suffix.lower() != ".track":
        logger.error(f"Output file '{out_path}' must have .track extension.")
        return False

    if out_path.exists() and not accept:
        logger.warning(f"Output file '{out_path}' already exists and will be overwritten.")
        confirm = "n"
        try:
            confirm = input("Do you want to continue? (y/N): ")
        except KeyboardInterrupt:
            print()
        if confirm.lower() != "y":
            logger.info("Operation cancelled by user.")
            return False

    return True



def _gate_from_values(values: list[float], gate_name: str) -> GateSegment:
    if len(values) != 4:
        raise ValueError(f"Gate '{gate_name}' must contain exactly four values.")

    lat1, lon1, lat2, lon2 = values
    return (lat1, lon1), (lat2, lon2)


def _parse_gates_file(gates_file: Path) -> tuple[GateSegment, GateSegment | None, GateSegment | None]:
    if not gates_file.exists():
        raise ValueError(f"Gates file '{gates_file}' does not exist.")

    valid_sections = {"finish_line", "pit_entry", "pit_exit", "track"}
    section_values: dict[str, str] = {}
    current_section: str | None = None

    with open(gates_file, "r", encoding="utf-8") as f:
        for line_number, raw_line in enumerate(f, start=1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue

            if line.startswith("[") and line.endswith("]"):
                section_name = line[1:-1].strip()
                if section_name not in valid_sections:
                    raise ValueError(f"Unknown section '{section_name}' in gates file at line {line_number}.")
                current_section = section_name
                continue

            if current_section is None:
                raise ValueError(f"Data line outside of a section in gates file at line {line_number}.")

            if current_section == "track":
                continue

            if current_section in section_values:
                raise ValueError(
                    f"Section '{current_section}' in gates file must contain exactly one gate line."
                )
            section_values[current_section] = line

    finish_raw = section_values.get("finish_line")
    if finish_raw is None:
        raise ValueError("Gates file is missing required [finish_line] section.")

    def parse_gate_line(raw: str, section_name: str) -> GateSegment:
        parts = raw.split()
        if len(parts) != 4:
            raise ValueError(
                f"Section '{section_name}' in gates file must contain exactly 4 numeric values."
            )
        try:
            values = [float(part) for part in parts]
        except ValueError as exc:
            raise ValueError(
                f"Section '{section_name}' in gates file contains non-numeric values."
            ) from exc
        return _gate_from_values(values, section_name)

    finish_gate = parse_gate_line(finish_raw, "finish_line")

    pit_entry_gate: GateSegment | None = None
    pit_entry_raw = section_values.get("pit_entry")
    if pit_entry_raw is not None:
        pit_entry_gate = parse_gate_line(pit_entry_raw, "pit_entry")

    pit_exit_gate: GateSegment | None = None
    pit_exit_raw = section_values.get("pit_exit")
    if pit_exit_raw is not None:
        pit_exit_gate = parse_gate_line(pit_exit_raw, "pit_exit")

    return finish_gate, pit_entry_gate, pit_exit_gate



def main(
    in_path: Path,
    out_path: Path,
    finish_line: list[float] | None,
    pit_entry: list[float] | None,
    pit_exit: list[float] | None,
    gates_file: Path | None,
    samples: int,
    min_lap_points: int,
    min_lap_length_m: float,
    accept: bool,
) -> bool:
    if not verify_in_path(in_path):
        return False
    if not _verify_out_path(out_path, accept):
        return False

    if gates_file is not None:
        if finish_line is not None or pit_entry is not None or pit_exit is not None:
            raise ValueError("When --gates-file is used, --finish-line/--pit-entry/--pit-exit must not be provided.")
        finish_gate, pit_entry_gate, pit_exit_gate = _parse_gates_file(gates_file)
    else:
        if finish_line is None:
            raise ValueError("--finish-line is required when --gates-file is not provided.")
        finish_gate = _gate_from_values(finish_line, "finish_line")
        pit_entry_gate = _gate_from_values(pit_entry, "pit_entry") if pit_entry is not None else None
        pit_exit_gate = _gate_from_values(pit_exit, "pit_exit") if pit_exit is not None else None

    logger.info(f"Loading '{in_path}'...")
    points = _extract_points(in_path)

    gates: dict[str, GateSegment] = {"finish": finish_gate}
    if pit_entry_gate is not None:
        gates["pit_entry"] = pit_entry_gate
    if pit_exit_gate is not None:
        gates["pit_exit"] = pit_exit_gate

    events = _collect_crossings(points, gates)
    laps = _build_full_laps(points, events, min_lap_points=min_lap_points, min_lap_length_m=min_lap_length_m)

    logger.info(f"Detected {len(laps)} valid full lap(s).")

    median_line = _build_median_line(laps, sample_count=samples)

    logger.info(f"Writing '{out_path}'...")
    _write_track_file(
        out_path=out_path,
        finish_line=finish_gate,
        pit_entry=pit_entry_gate,
        pit_exit=pit_exit_gate,
        track_points=median_line,
    )

    logger.info("Track generation completed successfully.")
    return True



def add_argparser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "track",
        help="Generate a .track file from .fit, .gpx, or .vbo activity data.",
    )
    parser.add_argument(
        "in_path",
        type=Path,
        metavar="IN_FILE",
        help="Path to input file (.gpx, .fit, .vbo).",
    )
    parser.add_argument(
        "-o",
        "--output",
        dest="out_path",
        type=Path,
        metavar="OUT_FILE",
        required=True,
        help="Path to output .track file.",
    )
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        "--finish-line",
        dest="finish_line",
        nargs=4,
        type=float,
        default=None,
        metavar=("LAT1", "LON1", "LAT2", "LON2"),
        help="Finish gate as 4 values: LAT1 LON1 LAT2 LON2.",
    )
    mode_group.add_argument(
        "--gates-file",
        dest="gates_file",
        type=Path,
        default=None,
        metavar="FILE",
        help="Path to file with [finish_line] and optional [pit_entry]/[pit_exit] sections.",
    )
    parser.add_argument(
        "--pit-entry",
        dest="pit_entry",
        nargs=4,
        type=float,
        default=None,
        metavar=("LAT1", "LON1", "LAT2", "LON2"),
        help="Optional pit entry gate as 4 values: LAT1 LON1 LAT2 LON2.",
    )
    parser.add_argument(
        "--pit-exit",
        dest="pit_exit",
        nargs=4,
        type=float,
        default=None,
        metavar=("LAT1", "LON1", "LAT2", "LON2"),
        help="Optional pit exit gate as 4 values: LAT1 LON1 LAT2 LON2.",
    )
    parser.add_argument(
        "--samples",
        dest="samples",
        type=int,
        default=200,
        metavar="N",
        help="Number of points in generated median line (default: 200).",
    )
    parser.add_argument(
        "--min-lap-points",
        dest="min_lap_points",
        type=int,
        default=20,
        metavar="N",
        help="Minimum points between finish crossings to consider a lap (default: 20).",
    )
    parser.add_argument(
        "--min-lap-length",
        dest="min_lap_length_m",
        type=float,
        default=50.0,
        metavar="METERS",
        help="Minimum lap length in meters to consider a lap (default: 50).",
    )
    parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        dest="accept",
        help="Accept questions (e.g. overwrite existing output file).",
    )



tool = Tool(
    name="track",
    description="Generate a .track file from .fit, .gpx, or .vbo activity data.",
    add_argparser=add_argparser,
    main=main,
)
