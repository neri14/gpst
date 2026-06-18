from datetime import datetime, timedelta

from gpst.data.processors.racetrack import GateType, Racetrack
from gpst.data.track import SegmentType, Track


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


def test_finish_gate_crossings_are_debounced_by_distance():
    rt = Racetrack(gate_debounce_distance_m=30.0)
    rt.add_gate((-0.001, 0.0), (0.001, 0.0), GateType.FINISH)

    track = _build_track_with_finish_line_oscillation()
    out = rt.calculate_racetrack_data(track)

    laps = [point["rt_lap"] for _, point in out.points_iter]
    states = [point["rt_state"] for _, point in out.points_iter]

    assert laps == [0, 1, 1, 1]
    assert states == ["unknown", "on_track", "on_track", "on_track"]


def test_finish_gate_crossings_are_not_debounced_when_disabled():
    rt = Racetrack(gate_debounce_distance_m=0.0)
    rt.add_gate((-0.001, 0.0), (0.001, 0.0), GateType.FINISH)

    track = _build_track_with_finish_line_oscillation()
    out = rt.calculate_racetrack_data(track)

    laps = [point["rt_lap"] for _, point in out.points_iter]

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
