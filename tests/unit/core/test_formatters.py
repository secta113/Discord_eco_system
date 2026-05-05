import pytest

from core.utils.formatters import f_bold_pts, f_commas, f_pts


def test_f_commas():
    assert f_commas(1000) == "1,000"
    assert f_commas(1234567) == "1,234,567"
    assert f_commas(0) == "0"
    assert f_commas(-1000) == "-1,000"
    assert f_commas(1000.5) == "1,000.5"
    assert f_commas("1000") == "1,000"
    assert f_commas("invalid") == "invalid"


def test_f_pts():
    assert f_pts(1000) == "1,000 pts"
    assert f_pts(0) == "0 pts"
    assert f_pts("5000") == "5,000 pts"


def test_f_bold_pts():
    assert f_bold_pts(1000) == "**1,000** pts"
    assert f_bold_pts(0) == "**0** pts"
    assert f_bold_pts("5000") == "**5,000** pts"
