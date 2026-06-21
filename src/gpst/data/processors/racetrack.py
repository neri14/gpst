
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
import math
from pathlib import Path

from gpst.utils.logger import logger
from gpst.utils.helpers import geo_distance, find_closest_point_on_line, lines_intersect

from ..track import SegmentType, Track

@dataclass
class Point:
    point: tuple[float, float] #latitude, longitude
    distance: float #meters


class GateType(StrEnum):
    FINISH = "finish"
    PIT_ENTRY = "pit_entry"
    PIT_EXIT = "pit_exit"



@dataclass
class Gate:
    p1: tuple[float, float] #latitude, longitude
    p2: tuple[float, float] #latitude, longitude
    type: GateType


class Racetrack:
    def __init__(self, gate_debounce_distance_m: float = 30.0):
        self.gates: list[Gate] = []
        self.track_points: list[Point] = []

        if gate_debounce_distance_m < 0.0:
            raise ValueError("Gate debounce distance must be non-negative.")

        self.gate_debounce_distance_m = gate_debounce_distance_m
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


    def calculate_racetrack_data(self, track: Track):

        class State(StrEnum):
            UNKNOWN = "unknown"
            ON_TRACK = "on_track"
            IN_PITLANE = "in_pitlane"

        state = State.UNKNOWN
        lap = 0

        lap_start_time = None
        lap_start_timer: float | None = None
        lap_start_distance: float | None = None

        pit_entry_time = None
        pit_entry_timer: float | None = None
        pit_entry_distance: float | None = None

        lap_times: list[float] = []
        lap_total_times: dict[int, float] = {}
        lap_progress_samples: dict[int, list[tuple[float, float]]] = defaultdict(list)
        lap_points_for_delta: list[tuple[int, float, float, dict]] = []
        pit_times: list[float] = []

        last_ts: datetime | None = None
        last_tp: tuple[float, float] | None = None
        last_point_data: dict | None = None
        distance_since_last_gate_crossing: dict[GateType, float] = {
            gate_type: float("inf") for gate_type in GateType
        }

        for ts, tp in track.points_iter:
            current_tp = self._extract_point_coords(tp)
            if current_tp is None:
                continue

            lat, lon = current_tp

            if last_tp is not None:
                segment_distance = geo_distance(last_tp[0], last_tp[1], lat, lon)
                finish_crossing_proportion_for_point: float | None = None
                for gate_type in distance_since_last_gate_crossing:
                    distance_since_last_gate_crossing[gate_type] += segment_distance

                gates_crossed = self._detect_gates_crossed(last_tp[0], last_tp[1], lat, lon)
                if gates_crossed:
                    logger.debug(f"Gates crossed between {last_tp} and {(lat, lon)}: {[g.type for g in gates_crossed]}")

                # Process gates in the order they are crossed along the current segment.
                gates_crossed_with_proportion = [
                    (gate, self._gate_crossing_proportion(last_tp, current_tp, gate))
                    for gate in gates_crossed
                ]
                gates_crossed_with_proportion.sort(key=lambda item: item[1])

                for gate, crossing_proportion in gates_crossed_with_proportion:
                    if (
                        self.gate_debounce_distance_m > 0.0
                        and distance_since_last_gate_crossing[gate.type] < self.gate_debounce_distance_m
                    ):
                        logger.debug(
                            f"Ignoring debounced gate crossing for {gate.type}: "
                            f"distance {distance_since_last_gate_crossing[gate.type]:.2f}m "
                            f"< {self.gate_debounce_distance_m:.2f}m."
                        )
                        continue

                    distance_since_last_gate_crossing[gate.type] = 0.0
                    gate_ts = self._interpolate_gate_crossing_time(
                        last_tp,
                        last_ts,
                        current_tp,
                        ts,
                        gate,
                        crossing_proportion,
                    )
                    gate_timer = self._interpolate_gate_crossing_metric(last_tp, current_tp,
                                                                        self._extract_numeric(last_point_data, 'timer'),
                                                                        self._extract_numeric(tp, 'timer'),
                                                                        gate,
                                                                        crossing_proportion)
                    gate_distance = self._interpolate_gate_crossing_metric(last_tp, current_tp,
                                                                           self._extract_numeric(last_point_data, 'dist'),
                                                                           self._extract_numeric(tp, 'dist'),
                                                                           gate,
                                                                           crossing_proportion)

                    if gate.type == GateType.PIT_EXIT:
                        state = State.ON_TRACK

                        if pit_entry_time is not None:
                            pit_time = (gate_ts - pit_entry_time).total_seconds()
                            pit_times.append(pit_time)
                            logger.info(f"Pit stop completed in {pit_time:.3f}s.")

                            pit_segment = {
                                'name': f"Pit stop {len(pit_times)}",
                                'source': "racetrack",
                                'type': SegmentType.PITSTOP,
                                'start_time': pit_entry_time,
                                'end_time': gate_ts,
                                'total_elapsed_time': pit_time,
                            }

                            if pit_entry_timer is not None:
                                pit_segment['start_timer'] = pit_entry_timer
                            if gate_timer is not None:
                                pit_segment['end_timer'] = gate_timer
                            if pit_entry_distance is not None:
                                pit_segment['start_distance'] = pit_entry_distance
                            if gate_distance is not None:
                                pit_segment['end_distance'] = gate_distance
                            if pit_entry_distance is not None and gate_distance is not None:
                                pit_distance = gate_distance - pit_entry_distance
                                if pit_distance >= 0.0:
                                    pit_segment['total_distance'] = pit_distance

                            track.add_segment(pit_segment)

                        lap_start_time = None #invalidate lap time
                        lap_start_timer = None
                        lap_start_distance = None

                        pit_entry_time = None #invalidate pit entry time
                        pit_entry_timer = None
                        pit_entry_distance = None

                    if gate.type == GateType.PIT_ENTRY:
                        state = State.IN_PITLANE

                        lap_start_time = None #invalidate lap time
                        lap_start_timer = None
                        lap_start_distance = None

                        pit_entry_time = gate_ts #store pit entry time
                        pit_entry_timer = gate_timer
                        pit_entry_distance = gate_distance

                    if gate.type == GateType.FINISH:
                        if state == State.UNKNOWN:
                            state = State.ON_TRACK # only if state was unknown update to on_track

                        if lap_start_time is not None:
                            lap_time = (gate_ts - lap_start_time).total_seconds()
                            lap_times.append(lap_time)
                            lap_total_times[lap] = lap_time
                            logger.info(f"Lap {lap} completed in {lap_time:.3f}s.")

                            lap_segment = {
                                'name': f"Lap {lap}",
                                'source': "racetrack",
                                'type': SegmentType.LAP,
                                'start_time': lap_start_time,
                                'end_time': gate_ts,
                                'total_elapsed_time': lap_time,
                            }

                            if lap_start_timer is not None:
                                lap_segment['start_timer'] = lap_start_timer
                            if gate_timer is not None:
                                lap_segment['end_timer'] = gate_timer
                            if lap_start_distance is not None:
                                lap_segment['start_distance'] = lap_start_distance
                            if gate_distance is not None:
                                lap_segment['end_distance'] = gate_distance
                            if lap_start_distance is not None and gate_distance is not None:
                                lap_distance = gate_distance - lap_start_distance
                                if lap_distance >= 0.0:
                                    lap_segment['total_distance'] = lap_distance
                                    if lap_time > 0.0:
                                        lap_segment['avg_speed'] = lap_distance / lap_time
                                    lap_progress_samples[lap].append((lap_distance, lap_time))

                            track.add_segment(lap_segment)
                        
                        if state == State.ON_TRACK:
                            lap_start_time = gate_ts #start new lap time when crossing finish line on track
                            lap_start_timer = gate_timer
                            lap_start_distance = gate_distance
                            finish_crossing_proportion_for_point = crossing_proportion

                        lap += 1

                        if state == State.ON_TRACK:
                            lap_progress_samples[lap].append((0.0, 0.0))

                if state == State.ON_TRACK:
                    if finish_crossing_proportion_for_point is not None:
                        # Keep lap/distance consistent on the exact sample where lap increments.
                        tp['rtx_lap_distance'] = segment_distance * (1.0 - finish_crossing_proportion_for_point)
                    else:
                        tp['rtx_lap_distance'] = self._calculate_distance_along_track(current_tp)

                lap_distance_value = tp.get('rtx_lap_distance')
                if (
                    state == State.ON_TRACK
                    and lap > 0
                    and lap_start_time is not None
                    and isinstance(lap_distance_value, (int, float))
                ):
                    lap_distance = float(lap_distance_value)
                    elapsed_in_lap = (ts - lap_start_time).total_seconds()
                    if elapsed_in_lap >= 0.0:
                        lap_progress_samples[lap].append((lap_distance, elapsed_in_lap))
                        lap_points_for_delta.append((lap, lap_distance, elapsed_in_lap, tp))


            tp['rtx_lap'] = lap
            tp['rtx_state'] = state.value

            last_ts = ts
            last_tp = current_tp
            last_point_data = tp

        if lap_total_times:
            best_lap = min(lap_total_times, key=lambda lap_idx: lap_total_times[lap_idx])

            for point_lap, point_lap_distance, point_elapsed, point_data in lap_points_for_delta:
                best_lap_time_at_distance = self._interpolate_lap_time_at_distance(
                    lap_progress_samples,
                    best_lap,
                    point_lap_distance,
                )
                if best_lap_time_at_distance is not None:
                    point_data['rtx_overall_best_lap_delta'] = point_elapsed - best_lap_time_at_distance
                    point_data['rtx_overall_best_lap'] = lap_total_times[best_lap]

                best_so_far_candidates = [
                    lap_idx for lap_idx in lap_total_times.keys() if lap_idx < point_lap
                ]
                if not best_so_far_candidates:
                    continue

                best_so_far_lap = min(best_so_far_candidates, key=lambda lap_idx: lap_total_times[lap_idx])
                best_so_far_time_at_distance = self._interpolate_lap_time_at_distance(
                    lap_progress_samples,
                    best_so_far_lap,
                    point_lap_distance,
                )
                if best_so_far_time_at_distance is not None:
                    point_data['rtx_best_lap_delta'] = point_elapsed - best_so_far_time_at_distance
                    point_data['rtx_best_lap'] = lap_total_times[best_so_far_lap]

        return track


    def find_gate(self, gate_type: GateType) -> Gate | None:
        for gate in self.gates:
            if gate.type == gate_type:
                return gate
        return None


    def find_gates(self, gate_type: GateType) -> list[Gate]:
        return [gate for gate in self.gates if gate.type == gate_type]


    def _detect_gates_crossed(self, lat1: float, lon1: float, lat2: float, lon2: float) -> list[Gate]:
        crossed_gates = []
        for gate in self.gates:
            if lines_intersect(lat1, lon1, lat2, lon2, gate.p1[0], gate.p1[1], gate.p2[0], gate.p2[1]):
                crossed_gates.append(gate)
        return crossed_gates


    def _interpolate_gate_crossing_time(self,
                                        p1: tuple[float, float],
                                        t1,
                                        p2: tuple[float, float],
                                        t2,
                                        gate: Gate,
                                        crossing_proportion: float | None = None):
        proportion = crossing_proportion
        if proportion is None:
            proportion = self._gate_crossing_proportion(p1, p2, gate)

        return t1 + (t2 - t1) * proportion


    def _gate_crossing_proportion(self, p1: tuple[float, float], p2: tuple[float, float], gate: Gate) -> float:
        # Estimate crossing location using local planar line-line intersection.
        earth_radius = 6372797.5605
        deg_to_rad = math.pi / 180.0

        def to_local_xy(lat: float, lon: float, ref_lat: float, ref_lon: float) -> tuple[float, float]:
            x = (lon - ref_lon) * math.cos(ref_lat * deg_to_rad) * earth_radius * deg_to_rad
            y = (lat - ref_lat) * earth_radius * deg_to_rad
            return x, y

        ref_lat = (p1[0] + p2[0] + gate.p1[0] + gate.p2[0]) / 4.0
        ref_lon = (p1[1] + p2[1] + gate.p1[1] + gate.p2[1]) / 4.0

        x1, y1 = to_local_xy(p1[0], p1[1], ref_lat, ref_lon)
        x2, y2 = to_local_xy(p2[0], p2[1], ref_lat, ref_lon)
        gx1, gy1 = to_local_xy(gate.p1[0], gate.p1[1], ref_lat, ref_lon)
        gx2, gy2 = to_local_xy(gate.p2[0], gate.p2[1], ref_lat, ref_lon)

        rx = x2 - x1
        ry = y2 - y1
        sx = gx2 - gx1
        sy = gy2 - gy1

        denom = rx * sy - ry * sx
        if not math.isclose(denom, 0.0, abs_tol=1e-12):
            qpx = gx1 - x1
            qpy = gy1 - y1
            t = (qpx * sy - qpy * sx) / denom
            u = (qpx * ry - qpy * rx) / denom

            if 0.0 <= t <= 1.0 and 0.0 <= u <= 1.0:
                return t

        # Fallback for nearly parallel lines: keep previous heuristic and clamp.
        d1 = geo_distance(p1[0], p1[1], gate.p1[0], gate.p1[1]) + geo_distance(p1[0], p1[1], gate.p2[0], gate.p2[1])
        d2 = geo_distance(p2[0], p2[1], gate.p1[0], gate.p1[1]) + geo_distance(p2[0], p2[1], gate.p2[0], gate.p2[1])

        total_distance = d1 + d2
        if total_distance == 0.0:
            return 0.0

        return max(0.0, min(1.0, d1 / total_distance))


    def _interpolate_gate_crossing_metric(self,
                                          p1: tuple[float, float],
                                          p2: tuple[float, float],
                                          v1: float | None,
                                          v2: float | None,
                                          gate: Gate,
                                          crossing_proportion: float | None = None) -> float | None:
        if v1 is None or v2 is None:
            return None

        proportion = crossing_proportion
        if proportion is None:
            proportion = self._gate_crossing_proportion(p1, p2, gate)

        return v1 + (v2 - v1) * proportion


    def _extract_point_coords(self, data: dict[str, int | float | str | datetime]) -> tuple[float, float] | None:
        lat = data.get('lat')
        lon = data.get('lon')

        if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
            return None

        return float(lat), float(lon)


    def _extract_numeric(self, data: dict | None, key: str) -> float | None:
        if data is None:
            return None

        value = data.get(key)
        if isinstance(value, (int, float)):
            return float(value)
        return None


    def _interpolate_lap_time_at_distance(self,
                                          lap_progress_samples: dict[int, list[tuple[float, float]]],
                                          lap: int,
                                          lap_distance: float) -> float | None:
        samples = lap_progress_samples.get(lap)
        if not samples or len(samples) < 2:
            return None

        sorted_samples = sorted(samples, key=lambda item: item[0])

        prev_distance, prev_elapsed = sorted_samples[0]
        if math.isclose(lap_distance, prev_distance, rel_tol=1e-9, abs_tol=1e-6):
            return prev_elapsed

        for current_distance, current_elapsed in sorted_samples[1:]:
            if math.isclose(lap_distance, current_distance, rel_tol=1e-9, abs_tol=1e-6):
                return current_elapsed

            # Skip duplicate or non-increasing distance samples to avoid unstable interpolation.
            if current_distance <= prev_distance:
                if current_elapsed < prev_elapsed:
                    prev_elapsed = current_elapsed
                continue

            if prev_distance <= lap_distance <= current_distance:
                ratio = (lap_distance - prev_distance) / (current_distance - prev_distance)
                return prev_elapsed + (current_elapsed - prev_elapsed) * ratio

            prev_distance, prev_elapsed = current_distance, current_elapsed

        return None

    def _calculate_distance_along_track(self, point: tuple[float, float]) -> float:
        if len(self.track_points) < 2:
            return 0.0

        # Project the point onto each polyline segment and take the closest projection.
        # This avoids pairing unrelated points from opposite sides of the finish line.
        earth_radius = 6372797.5605
        deg_to_rad = math.pi / 180.0

        def to_local_xy(lat: float, lon: float, ref_lat: float, ref_lon: float) -> tuple[float, float]:
            x = (lon - ref_lon) * math.cos(ref_lat * deg_to_rad) * earth_radius * deg_to_rad
            y = (lat - ref_lat) * earth_radius * deg_to_rad
            return x, y

        best_perpendicular_distance = float('inf')
        best_distance_along_track = 0.0

        for p1, p2 in zip(self.track_points, self.track_points[1:]):
            lat1, lon1 = p1.point
            lat2, lon2 = p2.point

            # Use a local tangent plane around the segment for stable projection math.
            ref_lat = (lat1 + lat2 + point[0]) / 3.0
            ref_lon = (lon1 + lon2 + point[1]) / 3.0

            ax, ay = to_local_xy(lat1, lon1, ref_lat, ref_lon)
            bx, by = to_local_xy(lat2, lon2, ref_lat, ref_lon)
            px, py = to_local_xy(point[0], point[1], ref_lat, ref_lon)

            vx = bx - ax
            vy = by - ay
            wx = px - ax
            wy = py - ay
            segment_len_sq = vx * vx + vy * vy

            if segment_len_sq == 0.0:
                t = 0.0
                proj_x, proj_y = ax, ay
            else:
                t = (wx * vx + wy * vy) / segment_len_sq
                t = max(0.0, min(1.0, t))
                proj_x = ax + t * vx
                proj_y = ay + t * vy

            perpendicular_distance = math.hypot(px - proj_x, py - proj_y)
            if perpendicular_distance >= best_perpendicular_distance:
                continue

            best_perpendicular_distance = perpendicular_distance
            best_distance_along_track = p1.distance + (p2.distance - p1.distance) * t

        return best_distance_along_track


    def debug(self):
        for gate in self.gates:
            logger.debug(f"RACETRACK Gate: {gate.type} - P1: {gate.p1}, P2: {gate.p2}")
        
        for point in self.track_points:
            logger.debug(f"RACETRACK {point.distance:.2f}m: Track Point: {point.point}")

def load_racetrack(racetrack_path) -> Racetrack:
    rt = Racetrack()

    valid_sections = {
        "finish_line",
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

            if line.startswith("#"):
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
