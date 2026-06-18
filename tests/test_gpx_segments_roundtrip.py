from datetime import datetime, timedelta

from gpst.data.reader.gpx_reader import GpxReader
from gpst.data.track import SegmentType, Track
from gpst.data.writer.gpx_writer import GpxWriter


def test_gpx_roundtrip_preserves_lap_and_pitstop_segments(tmp_path):
    track = Track()

    start = datetime(2026, 1, 1, 12, 0, 0)
    end = start + timedelta(seconds=90)

    track.upsert_point(start, {
        "time": start,
        "lat": 50.0,
        "lon": 16.0,
        "timer": 0.0,
        "dist": 0.0,
    })
    track.upsert_point(end, {
        "time": end,
        "lat": 50.0005,
        "lon": 16.0005,
        "timer": 90.0,
        "dist": 1000.0,
    })

    lap_start = start + timedelta(seconds=5)
    lap_end = start + timedelta(seconds=65)
    pit_start = start + timedelta(seconds=30)
    pit_end = start + timedelta(seconds=45)

    track.add_segment({
        "name": "Lap 1",
        "source": "racetrack",
        "type": SegmentType.LAP,
        "start_time": lap_start,
        "end_time": lap_end,
        "start_timer": 5.0,
        "end_timer": 65.0,
        "start_distance": 50.0,
        "end_distance": 700.0,
        "total_elapsed_time": 60.0,
        "total_distance": 650.0,
        "avg_speed": 650.0 / 60.0,
    })

    track.add_segment({
        "name": "Pit stop 1",
        "source": "racetrack",
        "type": SegmentType.PITSTOP,
        "start_time": pit_start,
        "end_time": pit_end,
        "start_timer": 30.0,
        "end_timer": 45.0,
        "start_distance": 300.0,
        "end_distance": 320.0,
        "total_elapsed_time": 15.0,
        "total_distance": 20.0,
    })

    out_path = tmp_path / "segments_roundtrip.gpx"

    writer = GpxWriter()
    assert writer.write(track, out_path)

    xml = out_path.read_text(encoding="utf-8")
    assert "RaceTrackExtensionsv1.xsd" in xml
    assert "ActivitySegmentsExtension" in xml
    assert "<asx:type>lap</asx:type>" in xml
    assert "<asx:type>pitstop</asx:type>" in xml

    reader = GpxReader()
    parsed = reader.read(out_path)

    assert parsed is not None

    segments = [segment for _, segment in parsed.segments_iter]
    lap_segments = [segment for segment in segments if segment.get("type") == SegmentType.LAP]
    pit_segments = [segment for segment in segments if segment.get("type") == SegmentType.PITSTOP]

    assert len(lap_segments) == 1
    assert len(pit_segments) == 1

    lap = lap_segments[0]
    pit = pit_segments[0]

    assert lap["name"] == "Lap 1"
    assert lap["total_elapsed_time"] == 60.0
    assert lap["total_distance"] == 650.0

    assert pit["name"] == "Pit stop 1"
    assert pit["total_elapsed_time"] == 15.0
    assert pit["total_distance"] == 20.0


def test_gpx_roundtrip_preserves_racetrack_delta_fields(tmp_path):
    track = Track()

    t0 = datetime(2026, 1, 1, 12, 0, 0)
    t1 = t0 + timedelta(seconds=1)

    track.upsert_point(t0, {
        "time": t0,
        "lat": 50.0,
        "lon": 16.0,
        "rtx_lap": 2,
        "rtx_state": "on_track",
        "rtx_lap_distance": 100.0,
        "rtx_delta_to_best_lap": 0.25,
        "rtx_delta_to_best_so_far": -0.1,
    })
    track.upsert_point(t1, {
        "time": t1,
        "lat": 50.0001,
        "lon": 16.0001,
        "rtx_lap": 2,
        "rtx_state": "on_track",
        "rtx_lap_distance": 120.0,
        "rtx_delta_to_best_lap": 0.3,
        "rtx_delta_to_best_so_far": -0.05,
    })

    out_path = tmp_path / "racetrack_deltas_roundtrip.gpx"

    writer = GpxWriter()
    assert writer.write(track, out_path)

    xml = out_path.read_text(encoding="utf-8")
    assert "<rtx:rtx_delta_to_best_lap>" in xml
    assert "<rtx:rtx_delta_to_best_so_far>" in xml

    reader = GpxReader()
    parsed = reader.read(out_path)

    assert parsed is not None
    parsed_points = [point for _, point in parsed.points_iter]
    assert len(parsed_points) == 2

    assert parsed_points[0]["rtx_delta_to_best_lap"] == 0.25
    assert parsed_points[0]["rtx_delta_to_best_so_far"] == -0.1
    assert parsed_points[1]["rtx_delta_to_best_lap"] == 0.3
    assert parsed_points[1]["rtx_delta_to_best_so_far"] == -0.05
