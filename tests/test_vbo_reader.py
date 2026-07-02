from datetime import datetime, timezone

from gpst.data.reader.vbo_reader import VboReader


def test_vbo_reader_parses_racebox_with_header_schema(tmp_path):
    vbo_content = """File created on 02/07/2026 @ 16:14

[header]
time
latitude
longitude
velocity kmh
heading
height
LongAcc
VertAcc
x-rotation-gyroscope
y-rotation-gyroscope
z-rotation-gyroscope
lean-angle
satellites

[column names]
time lat lng velocity heading height LongAcc VertAcc x-rotation-gyroscope y-rotation-gyroscope z-rotation-gyroscope lean-angle sats

[data]
161426.00 +03066.65306 -001013.28202 001.120 007.15 +00125.29 -0.022 +0.974 +0.000 +0.130 -0.190 -1.2 16
"""

    path = tmp_path / "racebox.vbo"
    path.write_text(vbo_content, encoding="utf-8")

    track = VboReader().read(path)

    assert track is not None
    assert len(track.points) == 1

    ts = datetime(2026, 7, 2, 16, 14, 26, tzinfo=timezone.utc)
    point = track.get_point(ts)

    assert point is not None
    assert point["lat"] == 3066.65306 / 60.0
    assert point["lon"] == -1013.28202 / -60.0
    assert point["speed"] == 1.120 / 3.6
    assert point["velocity"] == 1.120
    assert point["satellites"] == 16.0
    assert "sats" not in point


def test_vbo_reader_parses_racechrono_with_header_schema(tmp_path):
    vbo_content = """File created on 04/06/2026 at 08:52:04

[header]
satellites
time
latitude
longitude
velocity kmh
heading
height
long accel g
lat accel g

[column names]
sats time lat long velocity heading height longacc latacc

[data]
036 085208.10 +3063.149130 -01018.466808 000.000 000.00 +00171.00 +000.000 +000.000
"""

    path = tmp_path / "racechrono.vbo"
    path.write_text(vbo_content, encoding="utf-8")

    track = VboReader().read(path)

    assert track is not None
    assert len(track.points) == 1

    ts = datetime(2026, 6, 4, 8, 52, 8, 100000, tzinfo=timezone.utc)
    point = track.get_point(ts)

    assert point is not None
    assert point["satellites"] == 36.0
    assert point["lat"] == 3063.149130 / 60.0
    assert point["lon"] == -1018.466808 / -60.0
    assert point["velocity"] == 0.0
    assert point["speed"] == 0.0
    assert "sats" not in point
    assert "long" not in point
