from datetime import datetime
from zoneinfo import ZoneInfo

from src.data import MatchData
from src.followup import TRIVIA_MAX_AGE, TRIVIA_PER_ROUND, send_pending_trivia, trivia_text
from src.opendota import OpenDotaError
from src.state import Pending, State
from src.telegram import TelegramError
from tests.fixtures_match import HERO_KEYS, PLAYER_ID, parsed_match

NOW = datetime(2026, 9, 25, 21, 0, tzinfo=ZoneInfo("Europe/Rome"))
NOW_TS = int(NOW.timestamp())


class FakeOpenDota:
    def __init__(self, matches=None, fail=False, fail_keys=False):
        self.matches = matches or {}
        self.fail = fail
        self.fail_keys = fail_keys
        self.requested = []
        self.fetched = []

    def match(self, match_id):
        self.fetched.append(match_id)
        if self.fail:
            raise OpenDotaError("down")
        return self.matches.get(match_id, parsed_match(match_id=match_id, version=None))

    def request_parse(self, match_id):
        self.requested.append(match_id)

    def hero_keys(self):
        if self.fail_keys:
            raise OpenDotaError("down")
        return HERO_KEYS

    def heroes(self):
        return {1: "Anti-Mage"}


class FakeSender:
    def __init__(self, fail=False):
        self.sent = []
        self.fail = fail

    def send_message(self, text, chat_id=None, reply_to=None):
        if self.fail:
            raise TelegramError("boom")
        self.sent.append((reply_to, text))
        return 999


def setup(pending, client):
    state = State(pending_trivia=pending)
    return state, MatchData(client, PLAYER_ID, [], state, NOW)


def test_not_parsed_requests_once_then_waits():
    client = FakeOpenDota()
    state, data = setup([Pending(1, 10, NOW_TS - 60)], client)
    sender = FakeSender()
    send_pending_trivia(state, client, sender, PLAYER_ID, data, NOW)
    send_pending_trivia(state, client, sender, PLAYER_ID, data, NOW)
    assert client.requested == [1]  # l'analisi si chiede una volta sola
    assert sender.sent == []
    assert state.pending_trivia[0].requested


def test_parsed_sends_reply_and_clears():
    client = FakeOpenDota({1: parsed_match(match_id=1)})
    state, data = setup([Pending(1, 10, NOW_TS - 600)], client)
    sender = FakeSender()
    send_pending_trivia(state, client, sender, PLAYER_ID, data, NOW)
    assert len(sender.sent) == 1
    reply_to, text = sender.sent[0]
    assert reply_to == 10 and "Curiosità della partita" in text and "ULTRA KILL" in text
    assert state.pending_trivia == []
    assert client.requested == []  # già analizzata: nessuna richiesta


def test_expired_is_dropped_silently():
    client = FakeOpenDota()
    state, data = setup([Pending(1, 10, NOW_TS - TRIVIA_MAX_AGE - 1)], client)
    send_pending_trivia(state, client, FakeSender(), PLAYER_ID, data, NOW)
    assert state.pending_trivia == [] and client.fetched == []


def test_limit_per_round():
    client = FakeOpenDota()
    pending = [Pending(i, 10 + i, NOW_TS) for i in range(1, 6)]
    state, data = setup(pending, client)
    send_pending_trivia(state, client, FakeSender(), PLAYER_ID, data, NOW)
    assert client.fetched == [1, 2, 3][:TRIVIA_PER_ROUND]
    assert len(state.pending_trivia) == 5


def test_opendota_error_keeps_pending():
    client = FakeOpenDota(fail=True)
    state, data = setup([Pending(1, 10, NOW_TS)], client)
    send_pending_trivia(state, client, FakeSender(), PLAYER_ID, data, NOW)
    assert len(state.pending_trivia) == 1


def test_telegram_error_keeps_pending():
    client = FakeOpenDota({1: parsed_match(match_id=1)})
    state, data = setup([Pending(1, 10, NOW_TS)], client)
    send_pending_trivia(state, client, FakeSender(fail=True), PLAYER_ID, data, NOW)
    assert len(state.pending_trivia) == 1


def test_nothing_notable_is_dropped_without_message():
    boring = {"match_id": 1, "version": 22, "players": [{"player_slot": 0, "account_id": PLAYER_ID}]}
    client = FakeOpenDota({1: boring})
    state, data = setup([Pending(1, 10, NOW_TS)], client)
    sender = FakeSender()
    send_pending_trivia(state, client, sender, PLAYER_ID, data, NOW)
    assert sender.sent == [] and state.pending_trivia == []


def test_trivia_text_player_missing_and_hero_keys_down():
    client = FakeOpenDota(fail_keys=True)
    _, data = setup([], client)
    assert trivia_text(parsed_match(), 42, client, data) is None
    text = trivia_text(parsed_match(), PLAYER_ID, client, data)
    assert "Pudge" in text  # nome ricavato da "npc_dota_hero_pudge" anche senza /heroes
