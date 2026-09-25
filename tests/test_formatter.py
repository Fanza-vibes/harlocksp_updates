import pytest

from src.formatter import format_duration, format_match, is_radiant, is_win, mode_name
from tests.conftest import make_match


@pytest.mark.parametrize("slot,radiant", [(0, True), (4, True), (127, True), (128, False), (132, False)])
def test_is_radiant(slot, radiant):
    assert is_radiant(slot) is radiant


@pytest.mark.parametrize(
    "slot,radiant_win,expected",
    [(0, True, True), (0, False, False), (128, True, False), (128, False, True)],
)
def test_is_win(slot, radiant_win, expected):
    assert is_win(make_match(1, player_slot=slot, radiant_win=radiant_win)) is expected


@pytest.mark.parametrize("secs,text", [(0, "0:00"), (59, "0:59"), (2301, "38:21"), (3725, "1:02:05")])
def test_format_duration(secs, text):
    assert format_duration(secs) == text


def test_mode_name():
    assert mode_name(22, 7) == "Ranked All Pick"
    assert mode_name(23, 0) == "Turbo"
    assert mode_name(999, 0) == "Modalità 999"


def test_format_win_radiant():
    text = format_match(make_match(123), "Anti-Mage", "HarlockSP")
    assert "VITTORIA" in text and "SCONFITTA" not in text
    assert "Anti-Mage</b> (Radiant)" in text
    assert "12/3/8" in text
    assert "650/720" in text and "LH: 312" in text
    assert "38:21" in text and "Ranked All Pick" in text
    assert "https://www.dotabuff.com/matches/123" in text
    assert "https://www.opendota.com/matches/123" in text


def test_format_loss_dire():
    text = format_match(make_match(5, player_slot=130, radiant_win=True), "Pudge", "HarlockSP")
    assert "SCONFITTA" in text and "(Dire)" in text


def test_format_escapes_html():
    text = format_match(make_match(1), "<Hero&>", "<b>x</b>")
    assert "&lt;Hero&amp;&gt;" in text
    assert "&lt;b&gt;x&lt;/b&gt;" in text


def test_format_tolerates_missing_fields():
    text = format_match({"match_id": 9, "player_slot": 0, "radiant_win": None}, "X", "Y")
    assert "SCONFITTA" in text and "0/0/0" in text
