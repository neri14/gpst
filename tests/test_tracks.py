import logging
import pytest
import os
from datetime import datetime
from pathlib import Path

from gpst.data.track import Track


def compare_dicts(d1: dict, d2: dict) -> bool:
    if d1.keys() != d2.keys():
        return False
    for key in d1.keys():
        if d1[key] != d2[key]:
            return False
    return True


def test_ok_empty_track():
    track = Track()

    assert len(track.points) == 0, "Empty track shall have zero points."
    assert len(list(track.points_iter)) == 0, "Empty track points iterator should yield no points."
    assert len(track.metadata) == 0, "Empty track shall have no metadata."

    assert track.get_point(datetime(2024, 1, 1)) is None, "Getting a point from an empty track should return None." 


def test_ok_upsert_point():
    track = Track()

    timestamp_in = datetime(2024, 1, 1, 12, 0, 0)
    point_in = {
        "timestamp": timestamp_in,
        "latitude": 1.0,
        "longitude": 2.0
    }
    track.upsert_point(timestamp_in, point_in)

    point_out = track.get_point(timestamp_in)
    assert point_out is not None, "Point should exist after upsert."
    assert compare_dicts(point_out, point_in), "Retrieved point should match the upserted point."

    assert len(track.points) == 1, "Track should have one point after upsert."
    assert len(list(track.points_iter)) == 1, "Track points iterator should yield one point after upsert."

    timestamp_out, point_out = next(track.points_iter)
    assert timestamp_out == timestamp_in, "Iterator timestamp should match the upserted value."
    assert point_out is not None, "Point should exist after upsert."
    assert compare_dicts(point_out, point_in), "Iterator point should match the upserted point."


def test_ok_upsert_multiple_points():
    track = Track()
    
    timestamps_in = [
        datetime(2024, 1, 1, 12, 0, 0),
        datetime(2024, 1, 1, 14, 0, 0),
        datetime(2024, 1, 1, 13, 0, 0)
    ]
    points_in = [
        {"timestamp": timestamps_in[0], "latitude": 1.0, "longitude": 2.0},
        {"timestamp": timestamps_in[1], "latitude": 3.0, "longitude": 4.0},
        {"timestamp": timestamps_in[2], "latitude": 5.0, "longitude": 6.0}
    ]

    for ts, pt in zip(timestamps_in, points_in):
        track.upsert_point(ts, pt)

    assert len(track.points) == 3, "Track should have three points after three upserts."
    assert len(list(track.points_iter)) == 3, "Track points iterator should yield three points after three upserts."

    # Verify points are returned by iterator in sorted order

    sorted_timestamps_in = sorted(timestamps_in)
    for i, (timestamp_out, point_out) in enumerate(track.points_iter):
        assert timestamp_out == sorted_timestamps_in[i], f"Iterator timestamp at index {i} should match the sorted timestamp."
        assert point_out is not None, f"Point at index {i} should exist after upsert."

        index_in = timestamps_in.index(timestamp_out)
        assert compare_dicts(point_out, points_in[index_in]), f"Iterator point at index {i} should match the upserted point."


def test_ok_upser_point_update():
    track = Track()

    timestamp_in = datetime(2024, 1, 1, 12, 0, 0)
    point_in_1 = {
        "timestamp": timestamp_in,
        "latitude": 1.0,
        "longitude": 2.0,
        "speed": 50.0
    }
    track.upsert_point(timestamp_in, point_in_1)

    point_in_2 = {
        "speed": 60.0,
        "elevation": 100.0
    }
    track.upsert_point(timestamp_in, point_in_2)

    point_out = track.get_point(timestamp_in)
    assert point_out is not None, "Point should exist after upsert."

    expected_point = {
        "timestamp": timestamp_in,
        "latitude": 1.0,
        "longitude": 2.0,
        "speed": 60.0,
        "elevation": 100.0
    }
    assert compare_dicts(point_out, expected_point), "Retrieved point should reflect the updates."

    assert len(track.points) == 1, "Track should still have one point after update."
    assert len(list(track.points_iter)) == 1, "Track points iterator should yield one point after update."


def test_ok_metadata():
    track = Track()

    assert len(track.metadata) == 0, "New track should have empty metadata."

    track.metadata["name"] = "Test Track"
    track.metadata["description"] = "This is a test track."

    assert len(track.metadata) == 2, "Track metadata should have two entries after setting."

    assert track.metadata["name"] == "Test Track", "Metadata 'name' should be set correctly."
    assert track.metadata["description"] == "This is a test track.", "Metadata 'description' should be set correctly."


def test_ok_metadata_update():
    track = Track()

    track.metadata["name"] = "Initial Name"
    assert track.metadata["name"] == "Initial Name", "Metadata 'name' should be set correctly."

    track.metadata["name"] = "Updated Name"
    assert track.metadata["name"] == "Updated Name", "Metadata 'name' should be updated correctly."


LOGGER = logging.getLogger(__name__)

def test_nok_point_type_verification_warnings(caplog):
    track = Track()

    timestamp_in = datetime(2024, 1, 1, 12, 0, 0)

    with caplog.at_level(logging.WARNING):
        track.upsert_point(timestamp_in, {"latitude": "not-a-float"})
    assert any("Incorrect type" in record.message for record in caplog.records), "A incorrect type warning should be logged."

    with caplog.at_level(logging.WARNING):
        track.upsert_point(timestamp_in, {"longitude": 190.0})
    assert any("above maximum" in record.message for record in caplog.records), "An above maximum warning should be logged."

    with caplog.at_level(logging.WARNING):
        track.upsert_point(timestamp_in, {"speed": -1.0})
    assert any("below minimum" in record.message for record in caplog.records), "A below minimum warning should be logged."

    point_out = track.get_point(timestamp_in)
    assert point_out is not None, "Point should exist after upsert."
    assert point_out["latitude"] == "not-a-float", "Latitude should be stored as provided despite type warning."
    assert point_out["longitude"] == 190.0, "Longitude should be stored as provided despite range warning."
    assert point_out["speed"] == -1.0, "Speed should be stored as provided despite range warning."


def test_nok_metadata_type_verification_warnings(caplog):
    track = Track()

    with caplog.at_level(logging.WARNING):
        track.set_metadata("start_time", "not-a-datetime")
    assert any("Incorrect type" in record.message for record in caplog.records), "A incorrect type warning should be logged for metadata."

    with caplog.at_level(logging.WARNING):
        track.set_metadata("minlat", -100.0)
    assert any("below minimum" in record.message for record in caplog.records), "A below minimum warning should be logged for metadata."

    with caplog.at_level(logging.WARNING):
        track.set_metadata("maxlon", 200.0)
    assert any("above maximum" in record.message for record in caplog.records), "An above maximum warning should be logged for metadata."

    assert track.metadata["start_time"] == "not-a-datetime", "Metadata 'start_time' should be stored as provided despite type warning."
    assert track.metadata["minlat"] == -100.0, "Metadata 'minlat' should be stored as provided despite range warning."
    assert track.metadata["maxlon"] == 200.0, "Metadata 'maxlon' should be stored as provided despite range warning."


def test_nok_upsert_point_no_timestamp():
    track = Track()

    point_in = {
        "latitude": 1.0,
        "longitude": 2.0
    }

    with pytest.raises(ValueError, match="Timestamp must be provided"):
        track.upsert_point(None, point_in)


def test_nok_upsert_point_invalid_timestamp():
    track = Track()

    point_in = {
        "timestamp": "invalid-timestamp",
        "latitude": 1.0,
        "longitude": 2.0
    }

    with pytest.raises(TypeError, match="Timestamp must be a datetime object"):
        track.upsert_point(point_in["timestamp"], point_in)

def test_nok_upsert_point_invalid_data():
    track = Track()

    timestamp_in = datetime(2024, 1, 1, 12, 0, 0)
    invalid_data = ["not", "a", "dict"]

    with pytest.raises(TypeError, match="Data must be a dictionary"):
        track.upsert_point(timestamp_in, invalid_data)