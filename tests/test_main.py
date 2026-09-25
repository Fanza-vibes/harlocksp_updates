import json
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from src.config import Config
from src.main import EXIT_OK, EXIT_SEND_FAILED, run, select_new_matches
from src.opendota import OpenDotaError
from src.state import State, load_state, save_state
from src.telegram import TelegramError
from tests.conftest import make_match

CONFIG = Config(player_id=1, display_name="HarlockSP")
ROME = ZoneInfo("Europe/Rome")
NOW_NOON = datetime(2026, 9, 25, 12, 0, tzinfo=ROME)


class FakeOpenDota:
    def __init__(self, matches=None, error=None, heroes=None):
        self.matches = matches or []
        self.error = error
        self.hero_map = heroes if heroes is not None else {1: "Anti-Mage", 2: "Axe"}
        self.hero_calls = 0

    def recent_matches(self, player_id):
        if self.error:
            raise self.error
        return self.matches

    def heroes(self):
        self.hero_calls += 1
        return self.hero_map


class FakeSender:
    def __init__(self, fail_on=None):
        self.sent = []
        self.fail_on = fail_on

    def send_message(self, text):
        if self.fail_on is not None and len(self.sent) == self.fail_on:
            raise TelegramError("boom")
        self.sent.append(text)


@pytest.fixture
def state_path(tmp_path):
    return str(tmp_path / "state.json")


def test_select_new_matches_sorted_chronologically():
    ms = [make_match(30, start_time=300), make_match(10, start_time=100), make_match(20, start_time=200)]
    assert [m["match_id"] for m in select_new_matches(ms, 10)] == [20, 30]


def test_first_run_saves_without_sending(state_path):
    sender = FakeSender()
    rc = run(CONFIG, state_path, FakeOpenDota([make_match(5), make_match(9)]), sender)
    assert rc == EXIT_OK and sender.sent == []
    assert load_state(state_path).last_match_id == 9


def test_sends_only_new_in_order(state_path):
    save_state(state_path, State(last_match_id=10))
    ms = [make_match(12, hero_id=2), make_match(8), make_match(11)]
    sender = FakeSender()
    assert run(CONFIG, state_path, FakeOpenDota(ms), sender) == EXIT_OK
    assert len(sender.sent) == 2
    assert "/matches/11" in sender.sent[0] and "/matches/12" in sender.sent[1]
    assert "Axe" in sender.sent[1]
    st = load_state(state_path)
    assert st.last_match_id == 12 and st.heroes[1] == "Anti-Mage"


def test_no_new_matches_leaves_file_untouched(state_path):
    save_state(state_path, State(last_match_id=10, last_summary_date="2000-01-01"))
    run(CONFIG, state_path, FakeOpenDota([make_match(10)]), FakeSender(), now=NOW_NOON)
    before = Path(state_path).read_text()
    sender = FakeSender()
    run(CONFIG, state_path, FakeOpenDota([make_match(10), make_match(9)]), sender, now=NOW_NOON)
    assert sender.sent == [] and Path(state_path).read_text() == before


def test_api_error_keeps_state(state_path):
    save_state(state_path, State(last_match_id=10))
    before = Path(state_path).read_text()
    rc = run(CONFIG, state_path, FakeOpenDota(error=OpenDotaError("down")), FakeSender())
    assert rc == EXIT_OK and Path(state_path).read_text() == before


def test_api_error_on_first_run_creates_nothing(state_path):
    run(CONFIG, state_path, FakeOpenDota(error=OpenDotaError("down")), FakeSender())
    assert load_state(state_path).last_match_id is None


def test_send_failure_midway_saves_progress(state_path):
    save_state(state_path, State(last_match_id=10))
    ms = [make_match(11), make_match(12), make_match(13)]
    sender = FakeSender(fail_on=1)
    assert run(CONFIG, state_path, FakeOpenDota(ms), sender) == EXIT_SEND_FAILED
    assert len(sender.sent) == 1
    assert load_state(state_path).last_match_id == 11


def test_heroes_cache_reused(state_path):
    save_state(
        state_path, State(last_match_id=10, heroes={1: "Anti-Mage"}, heroes_updated_at="2026-09-24T00:00:00Z")
    )
    od = FakeOpenDota([make_match(11, hero_id=1)])
    run(CONFIG, state_path, od, FakeSender(), now=NOW_NOON)
    assert od.hero_calls == 0


def test_heroes_cache_refreshed_weekly(state_path):
    save_state(
        state_path, State(last_match_id=10, heroes={1: "Vecchio"}, heroes_updated_at="2026-09-01T00:00:00Z")
    )
    od = FakeOpenDota([make_match(11, hero_id=1)])
    sender = FakeSender()
    run(CONFIG, state_path, od, sender, now=NOW_NOON)
    assert od.hero_calls == 1 and "Anti-Mage" in sender.sent[0]


def test_heroes_failure_uses_fallback_name(state_path):
    save_state(state_path, State(last_match_id=10))

    class Broken(FakeOpenDota):
        def heroes(self):
            raise OpenDotaError("down")

    sender = FakeSender()
    run(CONFIG, state_path, Broken([make_match(11, hero_id=77)]), sender)
    assert "Eroe #77" in sender.sent[0]


def test_corrupted_state_is_first_run(state_path):
    Path(state_path).write_text("{broken")
    sender = FakeSender()
    run(CONFIG, state_path, FakeOpenDota([make_match(50)]), sender)
    assert sender.sent == [] and json.loads(Path(state_path).read_text())["last_match_id"] == 50


def test_dry_run_never_writes(state_path):
    sender = FakeSender()
    run(CONFIG, state_path, FakeOpenDota([make_match(1), make_match(2)]), sender, dry_run=True, last=5)
    assert len(sender.sent) == 2
    assert not Path(state_path).exists()


def test_main_silences_urllib3_debug(tmp_path, monkeypatch):
    import logging

    from src import main as main_mod

    cfg = tmp_path / "config.yaml"
    cfg.write_text("player_id: 1\n")
    monkeypatch.setattr(main_mod, "run", lambda *a, **k: 0)
    logging.getLogger("urllib3").setLevel(logging.DEBUG)
    assert main_mod.main(["--dry-run", "--config", str(cfg), "--state", str(tmp_path / "s.json")]) == 0
    assert logging.getLogger("urllib3").getEffectiveLevel() >= logging.WARNING


# --- riepilogo giornaliero -------------------------------------------------


def ts(y, mo, d, h, mi=0):
    return int(datetime(y, mo, d, h, mi, tzinfo=ROME).timestamp())


def test_daily_summary_first_run_only_initializes(state_path):
    save_state(state_path, State(last_match_id=10))
    sender = FakeSender()
    late = datetime(2026, 9, 25, 23, 5, tzinfo=ROME)
    run(CONFIG, state_path, FakeOpenDota([make_match(10)]), sender, now=late)
    assert sender.sent == [] and load_state(state_path).last_summary_date == "2026-09-25"


def test_daily_summary_sent_after_23_once(state_path):
    save_state(state_path, State(last_match_id=12, last_summary_date="2026-09-24"))
    ms = [
        make_match(10, start_time=ts(2026, 9, 24, 22), duration=1800),  # finita ieri sera prima delle 23
        make_match(11, start_time=ts(2026, 9, 25, 15), hero_id=2),
        make_match(12, start_time=ts(2026, 9, 25, 18), radiant_win=False),
    ]
    sender = FakeSender()
    late = datetime(2026, 9, 25, 23, 10, tzinfo=ROME)
    assert run(CONFIG, state_path, FakeOpenDota(ms), sender, now=late) == EXIT_OK
    assert len(sender.sent) == 1
    text = sender.sent[0]
    assert "Riepilogo di venerdì 25 settembre" in text and "Partite: <b>2</b> (1V – 1S)" in text
    assert load_state(state_path).last_summary_date == "2026-09-25"
    run(CONFIG, state_path, FakeOpenDota(ms), sender, now=late + timedelta(minutes=15))
    assert len(sender.sent) == 1  # non si ripete


def test_daily_summary_not_before_hour(state_path):
    save_state(state_path, State(last_match_id=11, last_summary_date="2026-09-24"))
    sender = FakeSender()
    ms = [make_match(11, start_time=ts(2026, 9, 25, 15))]
    run(CONFIG, state_path, FakeOpenDota(ms), sender, now=datetime(2026, 9, 25, 22, 50, tzinfo=ROME))
    assert sender.sent == []


def test_daily_summary_skipped_when_no_games(state_path):
    save_state(state_path, State(last_match_id=10, last_summary_date="2026-09-24"))
    sender = FakeSender()
    ms = [make_match(10, start_time=ts(2026, 9, 20, 15))]
    run(CONFIG, state_path, FakeOpenDota(ms), sender, now=datetime(2026, 9, 25, 23, 5, tzinfo=ROME))
    assert sender.sent == [] and load_state(state_path).last_summary_date == "2026-09-25"


def test_daily_summary_late_cron_after_midnight(state_path):
    # il cron delle 23 è saltato: all'1:00 si manda comunque il riepilogo del giorno prima
    save_state(state_path, State(last_match_id=11, last_summary_date="2026-09-24"))
    sender = FakeSender()
    ms = [make_match(11, start_time=ts(2026, 9, 25, 15))]
    run(CONFIG, state_path, FakeOpenDota(ms), sender, now=datetime(2026, 9, 26, 1, 0, tzinfo=ROME))
    assert len(sender.sent) == 1 and "25 settembre" in sender.sent[0]


def test_daily_summary_disabled(state_path):
    save_state(state_path, State(last_match_id=11, last_summary_date="2026-09-24"))
    sender = FakeSender()
    cfg = Config(player_id=1, display_name="H", daily_summary_hour=None)
    ms = [make_match(11, start_time=ts(2026, 9, 25, 15))]
    run(cfg, state_path, FakeOpenDota(ms), sender, now=datetime(2026, 9, 25, 23, 5, tzinfo=ROME))
    assert sender.sent == []


# --- giro completo con il bot ----------------------------------------------


class FakeBot(FakeSender):
    def __init__(self, updates):
        super().__init__()
        self.updates = updates
        self.private = []
        self.commands = None

    def send_message(self, text, chat_id=None):
        if chat_id is None:
            super().send_message(text)
        else:
            self.private.append((chat_id, text))

    def get_updates(self, offset, limit=50):
        return [u for u in self.updates if offset is None or u["update_id"] >= offset]

    def set_my_commands(self, commands):
        self.commands = commands


def test_full_round_with_commands(state_path):
    save_state(state_path, State(last_match_id=10, last_summary_date="2026-09-24"))
    msg = {"update_id": 500, "message": {"chat": {"id": 42, "type": "private"}, "text": "/ultima"}}
    bot = FakeBot([msg])
    run(CONFIG, state_path, FakeOpenDota([make_match(11)]), bot, bot=bot, now=NOW_NOON)
    assert len(bot.sent) == 1  # la partita nuova nel canale
    assert bot.private and bot.private[0][0] == 42 and "/matches/11" in bot.private[0][1]
    st = load_state(state_path)
    assert st.telegram_offset == 501 and st.commands_version == 1
    run(CONFIG, state_path, FakeOpenDota([make_match(11)]), bot, bot=bot, now=NOW_NOON)
    assert len(bot.private) == 1  # stesso messaggio non riletto


def test_opendota_down_leaves_commands_for_next_round(state_path):
    save_state(state_path, State(last_match_id=10))
    msg = {"update_id": 500, "message": {"chat": {"id": 42, "type": "private"}, "text": "/ultima"}}
    bot = FakeBot([msg])
    run(CONFIG, state_path, FakeOpenDota(error=OpenDotaError("down")), bot, bot=bot, now=NOW_NOON)
    assert bot.private == [] and load_state(state_path).telegram_offset is None


def test_dry_run_command(state_path, capsys):
    from src.telegram import DryRunSender

    run(
        CONFIG,
        state_path,
        FakeOpenDota([make_match(11)]),
        DryRunSender(),
        dry_run=True,
        command="/riepilogo oggi",
        now=NOW_NOON,
    )
    out = capsys.readouterr().out
    assert "chat prova" in out and "Riepilogo di oggi" in out
