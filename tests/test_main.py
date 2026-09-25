import json

import pytest

from src.config import Config
from src.main import EXIT_OK, EXIT_SEND_FAILED, run, select_new_matches
from src.opendota import OpenDotaError
from src.state import State, load_state, save_state
from src.telegram import TelegramError
from tests.conftest import make_match

CONFIG = Config(player_id=1, display_name="HarlockSP")


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
    save_state(state_path, State(last_match_id=10))
    before = open(state_path).read()
    sender = FakeSender()
    run(CONFIG, state_path, FakeOpenDota([make_match(10), make_match(9)]), sender)
    assert sender.sent == [] and open(state_path).read() == before


def test_api_error_keeps_state(state_path):
    save_state(state_path, State(last_match_id=10))
    before = open(state_path).read()
    rc = run(CONFIG, state_path, FakeOpenDota(error=OpenDotaError("down")), FakeSender())
    assert rc == EXIT_OK and open(state_path).read() == before


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
    save_state(state_path, State(last_match_id=10, heroes={1: "Anti-Mage"}, heroes_updated_at="x"))
    od = FakeOpenDota([make_match(11, hero_id=1)])
    run(CONFIG, state_path, od, FakeSender())
    assert od.hero_calls == 0


def test_heroes_failure_uses_fallback_name(state_path):
    save_state(state_path, State(last_match_id=10))

    class Broken(FakeOpenDota):
        def heroes(self):
            raise OpenDotaError("down")

    sender = FakeSender()
    run(CONFIG, state_path, Broken([make_match(11, hero_id=77)]), sender)
    assert "Eroe #77" in sender.sent[0]


def test_corrupted_state_is_first_run(state_path):
    open(state_path, "w").write("{broken")
    sender = FakeSender()
    run(CONFIG, state_path, FakeOpenDota([make_match(50)]), sender)
    assert sender.sent == [] and json.load(open(state_path))["last_match_id"] == 50


def test_dry_run_never_writes(state_path):
    sender = FakeSender()
    run(CONFIG, state_path, FakeOpenDota([make_match(1), make_match(2)]), sender, dry_run=True, last=5)
    assert len(sender.sent) == 2
    with pytest.raises(FileNotFoundError):
        open(state_path)
