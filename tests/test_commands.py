from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from src.commands import (
    BOT_COMMANDS, COMMANDS_VERSION, MAX_REPLIES_PER_CHAT, ensure_bot_commands, parse_command,
    private_messages, process_updates, reply_for,
)
from src.data import MatchData
from src.opendota import OpenDotaError
from src.state import State
from src.telegram import TelegramError
from tests.conftest import make_match

ROME = ZoneInfo("Europe/Rome")
NOW = datetime(2026, 9, 25, 21, 0, tzinfo=ROME)
TODAY_10 = int(datetime(2026, 9, 25, 10, 0, tzinfo=ROME).timestamp())
DAY = 86400


class FakeOpenDota:
    def __init__(self, period=None, fail=False):
        self.period = period or []
        self.fail = fail
        self.period_calls = []

    def player_matches(self, player_id, days):
        self.period_calls.append(days)
        if self.fail:
            raise OpenDotaError("down")
        return self.period

    def heroes(self):
        return {1: "Anti-Mage", 2: "Axe"}


class FakeBot:
    def __init__(self, updates=None, fail_get=False, fail_send_to=()):
        self.updates = updates or []
        self.fail_get = fail_get
        self.fail_send_to = set(fail_send_to)
        self.sent = []
        self.offsets = []
        self.commands = None

    def get_updates(self, offset, limit=50):
        self.offsets.append(offset)
        if self.fail_get:
            raise TelegramError("401")
        return self.updates

    def send_message(self, text, chat_id=None):
        if chat_id in self.fail_send_to:
            raise TelegramError("403 blocked")
        self.sent.append((chat_id, text))

    def set_my_commands(self, commands):
        self.commands = commands


def upd(update_id, text, chat_id=100, chat_type="private"):
    return {"update_id": update_id, "message": {"chat": {"id": chat_id, "type": chat_type}, "text": text}}


def data_with(recent, client=None):
    return MatchData(client or FakeOpenDota(), 1, recent, State(), NOW)


@pytest.mark.parametrize("text,expected", [
    ("/ultima", ("ultima", "")),
    ("/riepilogo@Harlocksp_updatesbot  Settimana ", ("riepilogo", "settimana")),
    ("/START", ("start", "")),
    ("ciao", None),
    ("  ", None),
])
def test_parse_command(text, expected):
    assert parse_command(text) == expected


def test_private_messages_filters_groups_and_non_text():
    updates = [
        upd(1, "/ultima"),
        upd(2, "/ultima", chat_type="group"),
        {"update_id": 3, "message": {"chat": {"id": 5, "type": "private"}, "sticker": {}}},
        {"update_id": 4, "edited_message": {}},
        {"message": {}},
    ]
    assert [m.update_id for m in private_messages(updates)] == [1]


def test_help_on_start_and_free_text():
    d = data_with([])
    for text in ("/start", "/aiuto", "ciao bot"):
        assert "/riepilogo settimana" in reply_for(text, d, "HarlockSP", NOW)


def test_unknown_command():
    assert "sconosciuto" in reply_for("/boh", data_with([]), "H", NOW)


def test_user_text_is_never_echoed():
    reply = reply_for("/<script>", data_with([]), "H", NOW)
    assert "<script>" not in reply


def test_ultima_includes_streak():
    recent = [make_match(i, start_time=TODAY_10 + i, hero_id=2) for i in (1, 2, 3)]
    reply = reply_for("/ultima", data_with(recent), "HarlockSP", NOW)
    assert "/matches/3" in reply and "Axe" in reply and "3 vittorie di fila" in reply


def test_ultima_without_matches():
    assert "Nessuna partita" in reply_for("/ultima", data_with([]), "H", NOW)


def test_riepilogo_oggi_uses_recent_only():
    client = FakeOpenDota()
    recent = [make_match(1, start_time=TODAY_10 - DAY), make_match(2, start_time=TODAY_10)]
    reply = reply_for("/riepilogo", data_with(recent, client), "H", NOW)
    assert "Riepilogo di oggi" in reply and "Partite: <b>1</b>" in reply
    assert client.period_calls == []  # meno di 20 recenti: nessuna chiamata in più


def test_riepilogo_mese_fetches_period_when_recent_not_enough():
    recent = [make_match(100 + i, start_time=TODAY_10 - i * 600) for i in range(20)]  # 20 partite oggi
    old = [make_match(1, start_time=TODAY_10 - 10 * DAY, hero_id=2)]
    client = FakeOpenDota(period=recent + old)
    reply = reply_for("/riepilogo mese", data_with(recent, client), "H", NOW)
    assert "Ultimi 30 giorni" in reply and "Partite: <b>21</b>" in reply
    assert client.period_calls == [31]


def test_riepilogo_bad_period():
    assert "Uso:" in reply_for("/riepilogo anno", data_with([]), "H", NOW)


def test_riepilogo_opendota_down():
    recent = [make_match(100 + i, start_time=TODAY_10 - i * 600) for i in range(20)]
    reply = reply_for("/riepilogo settimana", data_with(recent, FakeOpenDota(fail=True)), "H", NOW)
    assert "Riprova" in reply


def test_process_updates_replies_and_advances_offset():
    bot = FakeBot([upd(10, "/aiuto", chat_id=1), upd(11, "/ultima", chat_id=2), upd(12, "x", chat_type="group")])
    state = State(telegram_offset=10)
    process_updates(bot, state, data_with([make_match(5)]), "H", NOW)
    assert bot.offsets == [10]
    assert [c for c, _ in bot.sent] == [1, 2]
    assert state.telegram_offset == 13


def test_process_updates_rate_limit_per_chat():
    bot = FakeBot([upd(i, "/aiuto", chat_id=1) for i in range(1, 10)] + [upd(20, "/aiuto", chat_id=2)])
    state = State()
    process_updates(bot, state, data_with([]), "H", NOW)
    assert sum(1 for c, _ in bot.sent if c == 1) == MAX_REPLIES_PER_CHAT
    assert sum(1 for c, _ in bot.sent if c == 2) == 1
    assert state.telegram_offset == 21


def test_process_updates_send_failure_is_not_fatal():
    bot = FakeBot([upd(1, "/aiuto", chat_id=1), upd(2, "/aiuto", chat_id=2)], fail_send_to={1})
    state = State()
    process_updates(bot, state, data_with([]), "H", NOW)
    assert [c for c, _ in bot.sent] == [2] and state.telegram_offset == 3


def test_process_updates_get_failure_keeps_offset():
    state = State(telegram_offset=7)
    process_updates(FakeBot(fail_get=True), state, data_with([]), "H", NOW)
    assert state.telegram_offset == 7


def test_process_updates_logs_no_personal_data(caplog):
    bot = FakeBot([upd(1, "/aiuto segreto", chat_id=987654321)])
    with caplog.at_level("DEBUG"):
        process_updates(bot, State(), data_with([]), "H", NOW)
    assert "987654321" not in caplog.text and "segreto" not in caplog.text


def test_ensure_bot_commands_once():
    bot, state = FakeBot(), State()
    ensure_bot_commands(bot, state)
    assert bot.commands == BOT_COMMANDS and state.commands_version == COMMANDS_VERSION
    bot.commands = None
    ensure_bot_commands(bot, state)
    assert bot.commands is None
