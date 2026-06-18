from datetime import datetime, timedelta

from gpst.data.processors.racetrack import GateType, Racetrack
from gpst.data.track import Track


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
