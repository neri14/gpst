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


def _build_three_lap_track_with_timer_and_dist() -> Track:
    """Same as _build_three_lap_track_for_delta_test but with timer and dist fields
    that are consistent with the mocked _calculate_distance_along_track (abs(lon))."""
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
    cumulative_dist = 0.0

    for i, (offset, (lat, lon)) in enumerate(zip(offsets, points)):
        ts = base_time + timedelta(seconds=offset)
        if i > 0:
            cumulative_dist += abs(lon - points[i - 1][1])
        track.upsert_point(ts, {
            "time": ts,
            "lat": lat,
            "lon": lon,
            "timer": float(offset),
            "dist": cumulative_dist,
        })

    return track


def _build_three_lap_track_with_speed() -> Track:
    """Same layout as _build_three_lap_track_for_delta_test, with a constant per-point
    'speed' field so reference-speed delta math can be asserted precisely."""
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
        track.upsert_point(ts, {"time": ts, "lat": lat, "lon": lon, "speed": 50.0})

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

    assert any("rtx_overall_best_lap_delta" in point for point in lap1_points)
    assert any("rtx_overall_best_lap" in point for point in lap1_points)
    assert all("rtx_best_lap_delta" not in point for point in lap1_points)
    assert all("rtx_best_lap" not in point for point in lap1_points)
    assert any("rtx_overall_best_lap_delta" in point for point in lap2_points)
    assert any("rtx_overall_best_lap" in point for point in lap2_points)
    assert any("rtx_best_lap_delta" in point for point in lap2_points)
    assert any("rtx_best_lap" in point for point in lap2_points)
    assert any("rtx_overall_best_lap_delta" in point for point in lap3_points)
    assert any("rtx_overall_best_lap" in point for point in lap3_points)
    assert any("rtx_best_lap_delta" in point for point in lap3_points)
    assert any("rtx_best_lap" in point for point in lap3_points)


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


def test_extract_best_lap_progress_returns_correct_data():
    rt = Racetrack(gate_debounce_distance_m=0.0)
    rt.add_gate((-1.0, 0.0), (1.0, 0.0), GateType.FINISH)
    rt._calculate_distance_along_track = lambda point: abs(point[1])

    track = _build_three_lap_track_with_timer_and_dist()
    out = rt.calculate_racetrack_data(track)

    result = Racetrack.extract_best_lap_progress(out)
    assert result is not None

    best_time, progress, speed_progress = result
    assert best_time > 0.0
    assert len(progress) >= 2
    # Verify we got valid (distance, elapsed) pairs for the best lap.
    assert all(isinstance(d, float) and isinstance(t, float) for d, t in progress)
    # The builder doesn't set a 'speed' field, so speed samples should be empty (graceful degradation).
    assert speed_progress == []


def test_extract_best_lap_progress_returns_none_for_no_laps():
    track = Track()
    base_time = datetime(2026, 1, 1, 12, 0, 0)
    track.upsert_point(base_time, {"time": base_time, "lat": 0.0, "lon": 0.0})

    result = Racetrack.extract_best_lap_progress(track)
    assert result is None


def test_reference_delta_is_computed_with_reference_data():
    rt = Racetrack(gate_debounce_distance_m=0.0)
    rt.add_gate((-1.0, 0.0), (1.0, 0.0), GateType.FINISH)
    rt._calculate_distance_along_track = lambda point: abs(point[1])

    track = _build_three_lap_track_for_delta_test()

    # Build a synthetic reference that is 5s faster at every distance.
    ref_time = 25.0
    ref_progress = [(0.0, 0.0), (1.0, 10.0), (2.0, 18.0), (3.0, 25.0)]

    out = rt.calculate_racetrack_data(track,
                                      reference_lap_time=ref_time,
                                      reference_lap_progress=ref_progress)

    points = [point for _, point in out.points_iter]
    lap1_points = [point for point in points if point.get("rtx_lap") == 1]

    assert any("rtx_reference_lap_delta" in point for point in lap1_points)
    assert any("rtx_reference_lap" in point for point in lap1_points)

    # All points should have the same reference lap time.
    ref_lap_values = [point["rtx_reference_lap"] for point in lap1_points if "rtx_reference_lap" in point]
    assert all(v == ref_time for v in ref_lap_values)


def test_reference_fields_not_set_without_reference_data():
    rt = Racetrack(gate_debounce_distance_m=0.0)
    rt.add_gate((-1.0, 0.0), (1.0, 0.0), GateType.FINISH)
    rt._calculate_distance_along_track = lambda point: abs(point[1])

    track = _build_three_lap_track_for_delta_test()
    out = rt.calculate_racetrack_data(track)

    points = [point for _, point in out.points_iter]
    assert all("rtx_reference_lap_delta" not in point for point in points)
    assert all("rtx_reference_lap" not in point for point in points)


def test_reference_best_progressive_switches_to_better_lap():
    """With --reference-best, a faster current lap replaces the file reference
    only for points after that lap completes."""
    rt = Racetrack(gate_debounce_distance_m=0.0)
    rt.add_gate((-1.0, 0.0), (1.0, 0.0), GateType.FINISH)
    rt._calculate_distance_along_track = lambda point: abs(point[1])

    track = _build_three_lap_track_for_delta_test()

    # First, compute laps without any reference to find actual lap times.
    out_no_ref = rt.calculate_racetrack_data(track)
    lap_segments = sorted(
        [(ts, seg) for ts, seg in out_no_ref.segments_iter if seg.get('type') == SegmentType.LAP],
        key=lambda item: item[1].get('start_time', datetime.min),
    )
    assert len(lap_segments) >= 2, "Need at least 2 laps for this test"

    lap_times = [seg['total_elapsed_time'] for _, seg in lap_segments]
    # Set reference time to be better than some laps but worse than others.
    ref_time = sorted(lap_times)[1] + 0.001  # between best and second-best

    ref_progress = [(0.0, 0.0), (1.0, ref_time * 0.4), (2.0, ref_time * 0.75), (3.0, ref_time)]

    out = rt.calculate_racetrack_data(track,
                                      reference_lap_time=ref_time,
                                      reference_lap_progress=ref_progress,
                                      reference_best=True)

    points = [point for _, point in out.points_iter]
    laps_with_ref = {}
    for p in points:
        lap = p.get('rtx_lap')
        if lap and isinstance(lap, int) and lap > 0:
            if lap not in laps_with_ref:
                laps_with_ref[lap] = set()
            if 'rtx_reference_lap' in p:
                laps_with_ref[lap].add(p['rtx_reference_lap'])

    # Every lap should have at least some reference lap value.
    for lap_num in laps_with_ref:
        assert len(laps_with_ref[lap_num]) > 0, f"Lap {lap_num} has no reference values"

    # If the first lap is slower than reference, it should reference the file.
    if lap_times[0] >= ref_time:
        first_lap_refs = laps_with_ref.get(1, set())
        assert all(r == ref_time for r in first_lap_refs), \
            f"Lap 1 should reference file time {ref_time}, got {first_lap_refs}"


def test_reference_best_without_flag_always_uses_file_reference():
    """Without --reference-best, the reference never changes even if current laps are faster."""
    rt = Racetrack(gate_debounce_distance_m=0.0)
    rt.add_gate((-1.0, 0.0), (1.0, 0.0), GateType.FINISH)
    rt._calculate_distance_along_track = lambda point: abs(point[1])

    track = _build_three_lap_track_for_delta_test()
    ref_time = 999.0  # Very slow reference, all laps should beat it
    ref_progress = [(0.0, 0.0), (1.0, 400.0), (2.0, 750.0), (3.0, 999.0)]

    out = rt.calculate_racetrack_data(track,
                                      reference_lap_time=ref_time,
                                      reference_lap_progress=ref_progress,
                                      reference_best=False)

    points = [point for _, point in out.points_iter]
    for point in points:
        if 'rtx_reference_lap' in point:
            assert point['rtx_reference_lap'] == ref_time, \
                f"Without --reference-best, all points should reference {ref_time}"


def test_extract_best_lap_progress_includes_speed_samples():
    rt = Racetrack(gate_debounce_distance_m=0.0)
    rt.add_gate((-1.0, 0.0), (1.0, 0.0), GateType.FINISH)
    rt._calculate_distance_along_track = lambda point: abs(point[1])

    track = _build_three_lap_track_with_speed()
    out = rt.calculate_racetrack_data(track)

    result = Racetrack.extract_best_lap_progress(out)
    assert result is not None

    best_time, progress, speed_progress = result
    assert len(speed_progress) >= 2
    assert all(isinstance(d, float) and isinstance(s, float) for d, s in speed_progress)
    assert all(s == 50.0 for _, s in speed_progress)


def test_extract_best_lap_progress_uses_custom_speed_field():
    rt = Racetrack(gate_debounce_distance_m=0.0)
    rt.add_gate((-1.0, 0.0), (1.0, 0.0), GateType.FINISH)
    rt._calculate_distance_along_track = lambda point: abs(point[1])

    track = _build_three_lap_track_with_speed()
    for _, point in track.points_iter:
        point["velocity"] = 999.0

    out = rt.calculate_racetrack_data(track)

    result = Racetrack.extract_best_lap_progress(out, speed_field="velocity")
    assert result is not None

    _, _, speed_progress = result
    assert len(speed_progress) >= 2
    assert all(s == 999.0 for _, s in speed_progress)


def test_reference_speed_delta_is_computed_with_reference_speed_data():
    rt = Racetrack(gate_debounce_distance_m=0.0)
    rt.add_gate((-1.0, 0.0), (1.0, 0.0), GateType.FINISH)
    rt._calculate_distance_along_track = lambda point: abs(point[1])

    track = _build_three_lap_track_with_speed()

    ref_time = 25.0
    ref_progress = [(0.0, 0.0), (1.0, 10.0), (2.0, 18.0), (3.0, 25.0)]
    # Linear: speed = 20.0 + 2.0 * distance, so the formula holds at any interpolated point too.
    ref_speed_progress = [(0.0, 20.0), (1.0, 22.0), (2.0, 24.0), (3.0, 26.0)]

    out = rt.calculate_racetrack_data(track,
                                      reference_lap_time=ref_time,
                                      reference_lap_progress=ref_progress,
                                      reference_lap_speed_progress=ref_speed_progress)

    points = [point for _, point in out.points_iter]
    lap1_points = [point for point in points if point.get("rtx_lap") == 1]

    assert any("rtx_reference_lap_speed" in point for point in lap1_points)
    assert any("rtx_reference_lap_speed_delta" in point for point in lap1_points)

    for point in lap1_points:
        if "rtx_reference_lap_speed" in point:
            expected_ref_speed = 20.0 + 2.0 * point["rtx_lap_distance"]
            assert abs(point["rtx_reference_lap_speed"] - expected_ref_speed) < 1e-6
            assert point["rtx_reference_lap_speed_delta"] == point["speed"] - point["rtx_reference_lap_speed"]


def test_reference_speed_fields_not_set_without_reference_speed_progress():
    rt = Racetrack(gate_debounce_distance_m=0.0)
    rt.add_gate((-1.0, 0.0), (1.0, 0.0), GateType.FINISH)
    rt._calculate_distance_along_track = lambda point: abs(point[1])

    track = _build_three_lap_track_with_speed()

    ref_time = 25.0
    ref_progress = [(0.0, 0.0), (1.0, 10.0), (2.0, 18.0), (3.0, 25.0)]

    out = rt.calculate_racetrack_data(track,
                                      reference_lap_time=ref_time,
                                      reference_lap_progress=ref_progress)
    # reference_lap_speed_progress intentionally omitted (defaults to None).

    points = [point for _, point in out.points_iter]
    assert all("rtx_reference_lap_speed" not in point for point in points)
    assert all("rtx_reference_lap_speed_delta" not in point for point in points)
    # Time-based reference fields should still be set though - the two are independent.
    assert any("rtx_reference_lap_delta" in point for point in points)


def test_reference_best_speed_switches_to_session_lap_speed_samples():
    """With --reference-best, once a session lap beats a (deliberately very slow) file
    reference, rtx_reference_lap_speed for later points should come from that session
    lap's own recorded speed (~50.0), not the file reference's speed trace (20.0-26.0)."""
    rt = Racetrack(gate_debounce_distance_m=0.0)
    rt.add_gate((-1.0, 0.0), (1.0, 0.0), GateType.FINISH)
    rt._calculate_distance_along_track = lambda point: abs(point[1])

    out_no_ref = rt.calculate_racetrack_data(_build_three_lap_track_with_speed())
    lap_times = sorted(
        seg['total_elapsed_time'] for _, seg in out_no_ref.segments_iter
        if seg.get('type') == SegmentType.LAP
    )
    assert len(lap_times) >= 2, "Need at least 2 laps for this test"

    ref_time = lap_times[-1] + 0.001  # slower than every session lap
    ref_progress = [(0.0, 0.0), (1.0, ref_time * 0.4), (2.0, ref_time * 0.75), (3.0, ref_time)]
    ref_speed_progress = [(0.0, 20.0), (1.0, 22.0), (2.0, 24.0), (3.0, 26.0)]

    out = rt.calculate_racetrack_data(_build_three_lap_track_with_speed(),
                                      reference_lap_time=ref_time,
                                      reference_lap_progress=ref_progress,
                                      reference_lap_speed_progress=ref_speed_progress,
                                      reference_best=True)

    ref_speed_values = [
        point['rtx_reference_lap_speed'] for _, point in out.points_iter
        if 'rtx_reference_lap_speed' in point
    ]
    assert ref_speed_values, "Expected some rtx_reference_lap_speed values"

    # Lap 1 (before any lap has completed) must still use the file reference.
    assert any(20.0 <= v <= 26.0 for v in ref_speed_values)
    # Later laps, after reference_best switches to a faster same-session lap, must use
    # that lap's own recorded speed instead.
    assert any(abs(v - 50.0) < 1.0 for v in ref_speed_values)


def test_interpolate_reference_time_at_distance_returns_correct_value():
    rt = Racetrack()
    progress = [(0.0, 0.0), (100.0, 10.0), (200.0, 20.0)]

    assert rt._interpolate_reference_time_at_distance(progress, 150.0) == 15.0
    assert rt._interpolate_reference_time_at_distance(progress, 0.0) == 0.0
    assert rt._interpolate_reference_time_at_distance(progress, 200.0) == 20.0
    assert rt._interpolate_reference_time_at_distance(progress, 250.0) is None
    assert rt._interpolate_reference_time_at_distance([], 50.0) is None
    assert rt._interpolate_reference_time_at_distance([(0.0, 0.0)], 50.0) is None


def test_find_fastest_lap_segment_returns_quickest_lap():
    track = Track()
    base_time = datetime(2026, 1, 1, 12, 0, 0)

    track.add_segment({
        "name": "Lap 1", "source": "racetrack", "type": SegmentType.LAP,
        "start_time": base_time, "end_time": base_time + timedelta(seconds=30),
        "total_elapsed_time": 30.0,
    })
    track.add_segment({
        "name": "Lap 2", "source": "racetrack", "type": SegmentType.LAP,
        "start_time": base_time + timedelta(seconds=30), "end_time": base_time + timedelta(seconds=52),
        "total_elapsed_time": 22.0,
    })
    track.add_segment({
        "name": "Lap 3", "source": "racetrack", "type": SegmentType.LAP,
        "start_time": base_time + timedelta(seconds=52), "end_time": base_time + timedelta(seconds=80),
        "total_elapsed_time": 28.0,
    })
    track.add_segment({
        "name": "Pit stop 1", "source": "racetrack", "type": SegmentType.PITSTOP,
        "start_time": base_time + timedelta(seconds=80), "end_time": base_time + timedelta(seconds=200),
        "total_elapsed_time": 120.0,
    })

    fastest = Racetrack.find_fastest_lap_segment(track)
    assert fastest is not None
    assert fastest["name"] == "Lap 2"
    assert fastest["total_elapsed_time"] == 22.0


def test_find_fastest_lap_segment_returns_none_without_lap_segments():
    track = Track()
    assert Racetrack.find_fastest_lap_segment(track) is None

    base_time = datetime(2026, 1, 1, 12, 0, 0)
    track.add_segment({
        "name": "Pit stop 1", "source": "racetrack", "type": SegmentType.PITSTOP,
        "start_time": base_time, "end_time": base_time + timedelta(seconds=60),
        "total_elapsed_time": 60.0,
    })
    assert Racetrack.find_fastest_lap_segment(track) is None
