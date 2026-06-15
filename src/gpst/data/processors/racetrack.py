
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from gpst.utils.logger import logger

from gpst.utils.helpers import geo_distance, find_closest_point_on_line


@dataclass
class Point:
    point: tuple[float, float] #latitude, longitude
    distance: float #meters


class GateType(StrEnum):
    FINISH = "finish"
    SECTOR = "sector"
    PIT_ENTRY = "pit_entry"
    PIT_EXIT = "pit_exit"



@dataclass
class Gate:
    p1: tuple[float, float] #latitude, longitude
    p2: tuple[float, float] #latitude, longitude
    type: GateType


class Racetrack:
    def __init__(self):
        self.gates: list[Gate] = []
        self.track_points: list[Point] = []

        self._last_point: Point | None = None


    def add_gate(self, p1: tuple[float, float], p2: tuple[float, float], gate_type: GateType):
        self.gates.append(Gate(p1, p2, gate_type))


    def add_point(self, p: tuple[float, float]):
        if self._last_point is None:
            finish_line = self.find_gate(GateType.FINISH)
            if not finish_line:
                raise ValueError("No finish line gate found in racetrack.")

            p0 = find_closest_point_on_line(p[0], p[1], finish_line.p1, finish_line.p2)
            self.track_points.append(Point(p0, 0.0))
            self._last_point = self.track_points[-1]

        distance = self._last_point.distance + geo_distance(self._last_point.point[0], self._last_point.point[1], p[0], p[1])
        self.track_points.append(Point(p, distance))
        self._last_point = self.track_points[-1]


    def close_track(self):
        if self._last_point is None:
            return

        finish_line = self.find_gate(GateType.FINISH)
        if not finish_line:
            raise ValueError("No finish line gate found in racetrack.")

        p0 = find_closest_point_on_line(self._last_point.point[0], self._last_point.point[1], finish_line.p1, finish_line.p2)
        distance = self._last_point.distance + geo_distance(self._last_point.point[0], self._last_point.point[1], p0[0], p0[1])
        self.track_points.append(Point(p0, distance))
        self._last_point = self.track_points[-1]

        self.debug()


    def calculate_racetrack_data(self, track):
        # TODO Implement the logic to calculate racetrack data based on the provided track
        # This is a placeholder implementation; replace it with actual logic
        return track  # Return the modified track with racetrack data


    def find_gate(self, gate_type: GateType) -> Gate | None:
        for gate in self.gates:
            if gate.type == gate_type:
                return gate
        return None


    def find_gates(self, gate_type: GateType) -> list[Gate]:
        return [gate for gate in self.gates if gate.type == gate_type]


    def debug(self):
        for gate in self.gates:
            logger.debug(f"Gate: {gate.type} - P1: {gate.p1}, P2: {gate.p2}")
        
        for point in self.track_points:
            logger.debug(f"{point.distance:.2f}m: Track Point: {point.point}")


def load_racetrack(racetrack_path):
    rt = Racetrack()

    valid_sections = {
        "finish_line",
        "sector_lines",
        "pit_entry",
        "pit_exit",
        "track",
    }
    section_counts: dict[str, int] = {name: 0 for name in valid_sections}
    section_lines: dict[str, list[tuple[int, str]]] = {name: [] for name in valid_sections}
    current_section: str | None = None

    path = Path(racetrack_path)

    with open(path, "r", encoding="utf-8") as f:
        for line_number, raw_line in enumerate(f, start=1):
            line = raw_line.strip()

            if not line:
                continue

            if line.startswith("[") and line.endswith("]"):
                section_name = line[1:-1].strip()
                if section_name not in valid_sections:
                    raise ValueError(f"Unknown section '{section_name}' at line {line_number}.")

                section_counts[section_name] += 1
                if section_counts[section_name] > 1:
                    raise ValueError(f"Section '{section_name}' is defined multiple times.")

                current_section = section_name
                continue

            if current_section is None:
                raise ValueError(f"Data line outside of section at line {line_number}.")

            section_lines[current_section].append((line_number, line))

    if section_counts["finish_line"] == 0:
        raise ValueError("Missing mandatory section 'finish_line'.")
    if section_counts["track"] == 0:
        raise ValueError("Missing mandatory section 'track'.")

    finish_lines = section_lines["finish_line"]
    if len(finish_lines) != 1:
        raise ValueError("Section 'finish_line' must contain exactly one line.")

    pit_entry_lines = section_lines["pit_entry"]
    pit_exit_lines = section_lines["pit_exit"]
    if section_counts["pit_entry"] == 1 and len(pit_entry_lines) != 1:
        raise ValueError("Section 'pit_entry' must contain exactly one line when present.")
    if section_counts["pit_exit"] == 1 and len(pit_exit_lines) != 1:
        raise ValueError("Section 'pit_exit' must contain exactly one line when present.")

    track_lines = section_lines["track"]
    if len(track_lines) < 3:
        raise ValueError("Section 'track' must contain at least three points.")

    def parse_gate(line_number: int, line: str, section_name: str) -> tuple[tuple[float, float], tuple[float, float]]:
        parts = line.split()
        if len(parts) != 4:
            raise ValueError(
                f"Invalid gate line in section '{section_name}' at line {line_number}: expected 4 values."
            )

        try:
            lat1, lon1, lat2, lon2 = (float(value) for value in parts)
        except ValueError as exc:
            raise ValueError(
                f"Invalid numeric value in section '{section_name}' at line {line_number}."
            ) from exc

        return (lat1, lon1), (lat2, lon2)

    def parse_track_point(line_number: int, line: str) -> tuple[float, float]:
        parts = line.split()
        if len(parts) != 2:
            raise ValueError(f"Invalid track point at line {line_number}: expected 2 values.")

        try:
            lat, lon = (float(value) for value in parts)
        except ValueError as exc:
            raise ValueError(f"Invalid numeric value in track section at line {line_number}.") from exc

        return lat, lon

    finish_p1, finish_p2 = parse_gate(*finish_lines[0], "finish_line")
    rt.add_gate(finish_p1, finish_p2, GateType.FINISH)

    for line_number, line in section_lines["sector_lines"]:
        p1, p2 = parse_gate(line_number, line, "sector_lines")
        rt.add_gate(p1, p2, GateType.SECTOR)

    if section_counts["pit_entry"] == 1:
        pit_entry_p1, pit_entry_p2 = parse_gate(*pit_entry_lines[0], "pit_entry")
        rt.add_gate(pit_entry_p1, pit_entry_p2, GateType.PIT_ENTRY)

    if section_counts["pit_exit"] == 1:
        pit_exit_p1, pit_exit_p2 = parse_gate(*pit_exit_lines[0], "pit_exit")
        rt.add_gate(pit_exit_p1, pit_exit_p2, GateType.PIT_EXIT)

    for line_number, line in track_lines:
        rt.add_point(parse_track_point(line_number, line))

    rt.close_track()
    return rt
