import pytest

from src.formatter import (
    format_date,
    format_duration,
    format_match,
    format_summary,
    highlights,
    is_radiant,
    is_win,
    mode_name,
)
from src.stats import summarize
from tests.conftest import make_match


@pytest.mark.parametrize(("slot", "radiant"), [(0, True), (4, True), (127, True), (128, False), (132, False)])
def test_is_radiant(slot, radiant):
    assert is_radiant(slot) is radiant


@pytest.mark.parametrize(
    ("slot", "radiant_win", "expected"),
    [(0, True, True), (0, False, False), (128, True, False), (128, False, True)],
)
def test_is_win(slot, radiant_win, expected):
    assert is_win(make_match(1, player_slot=slot, radiant_win=radiant_win)) is expected


@pytest.mark.parametrize(("secs", "text"), [(0, "0:00"), (59, "0:59"), (2301, "38:21"), (3725, "1:02:05")])
def test_format_duration(secs, text):
    assert format_duration(secs) == text


def test_mode_name():
    assert mode_name(22, 7) == "Classificata · All Pick"
    assert mode_name(23, 0) == "Turbo"
    assert mode_name(22, 0) == "All Pick"
    assert mode_name(2, 9) == "Battle Cup · Captains Mode"
    assert mode_name(999, None) == "Modalità 999"
    assert mode_name(1, 99) == "All Pick"


def test_format_win_radiant():
    text = format_match(make_match(123), "Anti-Mage", "HarlockSP")
    assert "VITTORIA" in text and "SCONFITTA" not in text
    assert "Anti-Mage</b> (Radiant)" in text
    assert "12/3/8" in text
    assert "650/720" in text and "LH: 312" in text
    assert "38:21" in text and "Classificata · All Pick" in text
    assert "KDA 6.7" in text and "🌟" not in text
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


def test_highlights_perfect_game():
    text = format_match(make_match(1, kills=5, deaths=0, assists=10), "Axe", "H")
    assert text.startswith("🌟 ") and "0 morti" in text


def test_highlights_stellar_kda_and_massacre():
    lines = highlights(make_match(1, kills=22, deaths=2, assists=10))
    assert any("KDA stellare" in line for line in lines) and any("22 kill" in line for line in lines)


def test_highlights_streaks():
    assert any("3 vittorie di fila" in line for line in highlights(make_match(1, deaths=5), streak=3))
    assert any("4 sconfitte di fila" in line for line in highlights(make_match(1, deaths=5), streak=-4))
    assert highlights(make_match(1, deaths=5), streak=2) == []


def test_format_summary():
    s = summarize(
        [
            make_match(1, hero_id=1, kills=10, deaths=2, assists=5, duration=1800),
            make_match(2, hero_id=1, radiant_win=False, kills=2, deaths=8, assists=3, duration=2400),
            make_match(3, hero_id=2, kills=15, deaths=1, assists=9, duration=1500),
        ]
    )
    text = format_summary("Riepilogo di oggi", s, {1: "Anti-Mage", 2: "Axe"}, "HarlockSP")
    assert "Partite: <b>3</b> (2V – 1S)" in text
    assert "Win rate: <b>67%</b>" in text
    assert "• Anti-Mage: 2 partite (1V)" in text and "• Axe: 1 partita (1V)" in text
    assert "Miglior partita</b>: Axe 15/1/9" in text
    assert "1h 35m" in text


def test_format_summary_empty():
    assert "Nessuna partita" in format_summary("Oggi", None, {}, "H")


def test_format_date_italian():
    from datetime import date

    assert format_date(date(2026, 9, 25)) == "venerdì 25 settembre"
