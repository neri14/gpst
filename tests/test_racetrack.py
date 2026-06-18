from datetime import datetime, timedelta

from gpst.data.processors.racetrack import GateType, Racetrack
from gpst.data.track import SegmentType, Track
from gpst.utils.helpers import geo_distance


def _build_three_lap_track_for_delta_test() -> Track:
    track = Track()
    base_time = datetime(2026, 1, 1, 12, 0, 0)

    points = [
        (0.0, -1.0),
        (0.0, 1.0),
        (0.0, 2.0),
        (0.0, 3.0),
        (0.0, -1.0),
        (0.0, -2.0),
        (0.0, -3.0),
        (0.0, 1.0),
        (0.0, 2.0),
        (0.0, 3.0),
        (0.0, -1.0),
    ]

    offsets = [0, 1, 11, 21, 31, 41, 51, 61, 70, 79, 89]

    for offset, (lat, lon) in zip(offsets, points):
        ts = base_time + timedelta(seconds=offset)
        track.upsert_point(ts, {"time": ts, "lat": lat, "lon": lon})

    return track


def _build_track_with_finish_line_oscillation() -> Track:
    track = Track()
    base_time = datetime(2026, 1, 1, 12, 0, 0)

    points = [
        (0.0, -0.00005),
        (0.0, 0.00005),
        (0.0, -0.00005),
        (0.0, 0.00005),
    ]

    for idx, (lat, lon) in enumerate(points):
        ts = base_time + timedelta(seconds=idx)
        track.upsert_point(ts, {"time": ts, "lat": lat, "lon": lon})

    return track


def _build_track_with_pitlane_crossing() -> Track:
    track = Track()
    base_time = datetime(2026, 1, 1, 12, 0, 0)

    points = [
        (0.0, -0.0005),
        (0.0, 0.0015),
        (0.0, 0.0025),
    ]

    for idx, (lat, lon) in enumerate(points):
        ts = base_time + timedelta(seconds=idx * 10)
        track.upsert_point(ts, {
            "time": ts,
            "lat": lat,
            "lon": lon,
            "timer": float(idx * 10),
            "dist": float(idx * 100),
        })

    return track


def _build_track_with_single_finish_crossing() -> Track:
    track = Track()
    base_time = datetime(2026, 1, 1, 12, 0, 0)

    points = [
        (0.0, -0.0010),
        (0.0, 0.0010),
    ]

    for idx, (lat, lon) in enumerate(points):
        ts = base_time + timedelta(seconds=idx * 10)
        track.upsert_point(ts, {"time": ts, "lat": lat, "lon": lon})

    return track


def _build_track_for_interpolated_lap_time() -> Track:
    track = Track()
    base_time = datetime(2026, 1, 1, 12, 0, 0)

    points = [
        (0.0, -0.0030),
        (0.0, 0.0010),
        (0.0, -0.0010),
    ]

    offsets = [0, 40, 80]
    for offset, (lat, lon) in zip(offsets, points):
        ts = base_time + timedelta(seconds=offset)
        track.upsert_point(ts, {"time": ts, "lat": lat, "lon": lon})

    return track


def test_finish_gate_crossings_are_debounced_by_distance():
    rt = Racetrack(gate_debounce_distance_m=30.0)
    rt.add_gate((-0.001, 0.0), (0.001, 0.0), GateType.FINISH)

    track = _build_track_with_finish_line_oscillation()
    out = rt.calculate_racetrack_data(track)

    laps = [point["rtx_lap"] for _, point in out.points_iter]
    states = [point["rtx_state"] for _, point in out.points_iter]

    assert laps == [0, 1, 1, 1]
    assert states == ["unknown", "on_track", "on_track", "on_track"]


def test_finish_gate_crossings_are_not_debounced_when_disabled():
    rt = Racetrack(gate_debounce_distance_m=0.0)
    rt.add_gate((-0.001, 0.0), (0.001, 0.0), GateType.FINISH)

    track = _build_track_with_finish_line_oscillation()
    out = rt.calculate_racetrack_data(track)

    laps = [point["rtx_lap"] for _, point in out.points_iter]

    assert laps == [0, 1, 2, 3]


def test_finish_gate_crossings_create_lap_segments():
    rt = Racetrack(gate_debounce_distance_m=0.0)
    rt.add_gate((-0.001, 0.0), (0.001, 0.0), GateType.FINISH)

    track = _build_track_with_finish_line_oscillation()
    out = rt.calculate_racetrack_data(track)

    lap_segments = [segment for _, segment in out.segments_iter if segment.get("type") == SegmentType.LAP]

    assert len(lap_segments) == 2
    assert lap_segments[0]["name"] == "Lap 1"
    assert lap_segments[1]["name"] == "Lap 2"
    assert lap_segments[0]["total_elapsed_time"] > 0.0
    assert lap_segments[1]["total_elapsed_time"] > 0.0


def test_pit_entry_and_exit_create_pitstop_segment():
    rt = Racetrack(gate_debounce_distance_m=0.0)
    rt.add_gate((-0.001, 0.01), (0.001, 0.01), GateType.FINISH)
    rt.add_gate((-0.001, 0.001), (0.001, 0.001), GateType.PIT_ENTRY)
    rt.add_gate((-0.001, 0.002), (0.001, 0.002), GateType.PIT_EXIT)

    track = _build_track_with_pitlane_crossing()
    out = rt.calculate_racetrack_data(track)

    pit_segments = [segment for _, segment in out.segments_iter if segment.get("type") == SegmentType.PITSTOP]

    assert len(pit_segments) == 1
    assert pit_segments[0]["name"] == "Pit stop 1"
    assert pit_segments[0]["total_elapsed_time"] > 0.0
    assert pit_segments[0]["start_timer"] < pit_segments[0]["end_timer"]
    assert pit_segments[0]["start_distance"] < pit_segments[0]["end_distance"]


def test_interpolate_lap_time_at_distance_returns_linear_result():
    rt = Racetrack()
    lap_progress_samples = {
        1: [(0.0, 0.0), (100.0, 10.0), (200.0, 20.0)],
    }

    interpolated = rt._interpolate_lap_time_at_distance(lap_progress_samples, 1, 150.0)

    assert interpolated is not None
    assert interpolated == 15.0
    assert rt._interpolate_lap_time_at_distance(lap_progress_samples, 1, 250.0) is None


def test_lap_deltas_are_added_after_first_completed_lap():
    rt = Racetrack(gate_debounce_distance_m=0.0)
    rt.add_gate((-1.0, 0.0), (1.0, 0.0), GateType.FINISH)

    # Keep the test focused on delta math by using a deterministic lap distance.
    rt._calculate_distance_along_track = lambda point: abs(point[1])

    track = _build_three_lap_track_for_delta_test()
    out = rt.calculate_racetrack_data(track)

    points = [point for _, point in out.points_iter]
    lap1_points = [point for point in points if point.get("rtx_lap") == 1]
    lap2_points = [point for point in points if point.get("rtx_lap") == 2]
    lap3_points = [point for point in points if point.get("rtx_lap") == 3]

    assert any("rtx_delta_to_best_lap" in point for point in lap1_points)
    assert all("rtx_delta_to_best_so_far" not in point for point in lap1_points)
    assert any("rtx_delta_to_best_lap" in point for point in lap2_points)
    assert any("rtx_delta_to_best_so_far" in point for point in lap2_points)
    assert any("rtx_delta_to_best_lap" in point for point in lap3_points)
    assert any("rtx_delta_to_best_so_far" in point for point in lap3_points)


def test_lap_distance_resets_on_same_sample_where_lap_increments():
    rt = Racetrack(gate_debounce_distance_m=0.0)
    rt.add_gate((-0.001, 0.0), (0.001, 0.0), GateType.FINISH)

    # Simulate a stale projection result from the previous lap side.
    rt._calculate_distance_along_track = lambda point: 999.0

    track = _build_track_with_single_finish_crossing()
    out = rt.calculate_racetrack_data(track)

    points = [point for _, point in out.points_iter]
    assert points[1]["rtx_lap"] == 1

    segment_distance = geo_distance(0.0, -0.0010, 0.0, 0.0010)
    expected_distance_after_finish = segment_distance * 0.5
    assert abs(points[1]["rtx_lap_distance"] - expected_distance_after_finish) < 0.01


def test_lap_time_uses_interpolated_finish_crossing_proportion():
    rt = Racetrack(gate_debounce_distance_m=0.0)
    rt.add_gate((-0.001, 0.0), (0.001, 0.0), GateType.FINISH)

    track = _build_track_for_interpolated_lap_time()
    out = rt.calculate_racetrack_data(track)

    lap_segments = [segment for _, segment in out.segments_iter if segment.get("type") == SegmentType.LAP]
    assert len(lap_segments) == 1

    # First crossing at 75% of [0s,40s] => 30s, second at 50% of [40s,80s] => 60s.
    assert abs(lap_segments[0]["total_elapsed_time"] - 30.0) < 1e-6
