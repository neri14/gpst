import pytest
import os
from datetime import datetime
from pathlib import Path

from gpst.data.track import Track


def test_empty_track():
    track = Track()

    assert len(track.points) == 0, "Empty track shall have zero points."
    assert len(list(track.points_iter)) == 0, "Empty track points iterator should yield no points."
    assert len(track.metadata) == 0, "Empty track shall have no metadata."

    assert track.get_point(datetime(2024, 1, 1)) is None, "Getting a point from an empty track should return None." 