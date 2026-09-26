from datetime import date, datetime
from zoneinfo import ZoneInfo

from src.stats import daily_window, in_window, streak_until, summarize, summary_target
from tests.conftest import make_match

ROME = ZoneInfo("Europe/Rome")


def results(*wins):
    """Partite in ordine cronologico con gli esiti indicati (slot Radiant)."""
    return [make_match(i + 1, start_time=1000 * (i + 1), radiant_win=w) for i, w in enumerate(wins)]


def test_streak_wins_and_losses():
    ms = results(False, True, True, True)
    assert streak_until(ms, 4) == 3
    assert streak_until(ms, 2) == 1
    assert streak_until(ms, 1) == -1
    assert streak_until(results(True, False, False), 3) == -2


def test_streak_unordered_input_and_missing():
    ms = list(reversed(results(True, True)))
    assert streak_until(ms, 2) == 2
    assert streak_until(ms, 99) == 0


def test_summarize_empty():
    assert summarize([]) is None


def test_summarize_ties_prefer_more_wins():
    s = summarize(
        [
            make_match(1, hero_id=5, radiant_win=False),
            make_match(2, hero_id=7, radiant_win=True),
        ]
    )
    assert [h for h, _, _ in s.top_heroes] == [7, 5]
    assert s.winrate == 50


def test_summary_target():
    assert summary_target(datetime(2026, 9, 25, 22, 59, tzinfo=ROME), 23) == date(2026, 9, 24)
    assert summary_target(datetime(2026, 9, 25, 23, 0, tzinfo=ROME), 23) == date(2026, 9, 25)


def test_daily_window_handles_dst():
    # 25 ottobre 2026: in Italia finisce l'ora legale (giornata di 25 ore)
    start, end = daily_window(date(2026, 10, 25), 23, ROME)
    assert start == datetime(2026, 10, 24, 23, tzinfo=ROME)
    assert end.timestamp() - start.timestamp() == 25 * 3600


def test_in_window_uses_end_time():
    start, end = daily_window(date(2026, 9, 25), 23, ROME)
    late = int(end.timestamp()) - 600  # inizia 10 minuti prima delle 23…
    ms = [
        make_match(1, start_time=late, duration=300),  # …e finisce prima: dentro
        make_match(2, start_time=late, duration=1200),  # …e finisce dopo: giorno dopo
        make_match(3, start_time=int(start.timestamp()) - 100, duration=200),  # finisce dopo l'inizio
    ]
    assert [m["match_id"] for m in in_window(ms, start, end)] == [1, 3]
