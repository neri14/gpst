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


def test_empty_track():
    track = Track()

    assert len(track.points) == 0, "Empty track shall have zero points."
    assert len(list(track.points_iter)) == 0, "Empty track points iterator should yield no points."
    assert len(track.metadata) == 0, "Empty track shall have no metadata."

    assert track.get_point(datetime(2024, 1, 1)) is None, "Getting a point from an empty track should return None." 


def test_upsert_point():
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


#TODO def test_upsert_point_update():

#TODO def test_metadata():

#TODO def test_metadata_update():

#TODO def test_multiple_points():

#TODO def test_points_iter_order():

#TODO def test_type_warnings():

