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
