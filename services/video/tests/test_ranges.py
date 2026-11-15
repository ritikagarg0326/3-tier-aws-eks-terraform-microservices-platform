import pytest

from app.ranges import RangeNotSatisfiable, parse_range


@pytest.mark.parametrize("hdr,expected", [(None, None), ("bytes=0-9", (0, 9)), ("bytes=5-", (5, 99)), ("bytes=-10", (90, 99)), ("bytes=90-500", (90, 99)), ("bytes=0-1,5-9", (0, 1)), ("items=1-2", None), ("bytes=abc-", None)])
def test_parse(hdr, expected):
    assert parse_range(hdr, 100) == expected


@pytest.mark.parametrize("hdr", ["bytes=100-", "bytes=50-10", "bytes=-0"])
def test_unsatisfiable(hdr):
    with pytest.raises(RangeNotSatisfiable):
        parse_range(hdr, 100)
