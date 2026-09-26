"""Comandi in chat privata con il bot (/ultima, /riepilogo, /aiuto).

Il bot non ha un server: i messaggi vengono letti a ogni giro del workflow (getUpdates),
quindi le risposte arrivano con qualche minuto di ritardo.
Privacy: nei log (pubblici su GitHub) non finiscono mai chat ID né testi degli utenti.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from html import escape
from typing import Any, Protocol

from .data import MatchData
from .formatter import format_match, format_summary
from .opendota import OpenDotaError
from .state import State
from .stats import start_of_day, streak_before, streak_until, summarize
from .telegram import TelegramError

log = logging.getLogger(__name__)

COMMANDS_VERSION = 1  # incrementare quando cambia BOT_COMMANDS
BOT_COMMANDS = [
    ("ultima", "Scheda dell'ultima partita"),
    ("riepilogo", "Riepilogo: oggi, settimana o mese"),
    ("aiuto", "Come funziona il bot"),
]
PERIODS = {"oggi": None, "settimana": 7, "mese": 30}
PERIOD_TITLES = {"oggi": "Riepilogo di oggi", "settimana": "Ultimi 7 giorni", "mese": "Ultimi 30 giorni"}
MAX_REPLIES_PER_CHAT = 3  # per giro: evita spam e troppe chiamate a OpenDota


class Bot(Protocol):
    def get_updates(self, offset: int | None, limit: int = 50) -> list[dict]: ...
    def send_message(
        self, text: str, chat_id: str | int | None = None, reply_to: int | None = None
    ) -> int | None: ...
    def set_my_commands(self, commands: list[tuple[str, str]]) -> None: ...


@dataclass(frozen=True)
class Incoming:
    update_id: int
    chat_id: int
    text: str


def private_messages(updates: list[dict[str, Any]]) -> list[Incoming]:
    """Solo messaggi di testo in chat privata; gruppi e altri tipi vengono ignorati."""
    out = []
    for u in updates:
        msg = u.get("message")
        if not isinstance(msg, dict) or not isinstance(u.get("update_id"), int):
            continue
        chat = msg.get("chat") or {}
        text = msg.get("text")
        if chat.get("type") == "private" and isinstance(chat.get("id"), int) and isinstance(text, str):
            out.append(Incoming(u["update_id"], chat["id"], text))
    return out


def parse_command(text: str) -> tuple[str, str] | None:
    """'/riepilogo@MioBot  Settimana' → ('riepilogo', 'settimana'). None se non è un comando."""
    text = text.strip()
    if not text.startswith("/"):
        return None
    head, _, rest = text.partition(" ")
    name = head[1:].split("@", 1)[0].lower()
    return name, rest.strip().lower()


def help_text(display_name: str) -> str:
    name = escape(display_name)
    return "\n".join(
        [
            f"👋 Ciao! Sono il bot degli aggiornamenti Dota 2 di <b>{name}</b>.",
            "",
            "Comandi disponibili:",
            "• /ultima – scheda dell'ultima partita",
            "• /riepilogo oggi – le partite di oggi",
            "• /riepilogo settimana – ultimi 7 giorni",
            "• /riepilogo mese – ultimi 30 giorni",
            "",
            "⏳ Non sono sempre online: leggo i messaggi ogni 5-10 minuti circa, "
            "quindi la risposta può arrivare con qualche minuto di ritardo.",
            "",
            "Gli aggiornamenti di ogni partita e il riepilogo delle 23 arrivano nel canale.",
        ]
    )


def reply_for(text: str, data: MatchData, display_name: str, now: datetime) -> str:
    cmd = parse_command(text)
    if cmd is None or cmd[0] in ("start", "aiuto", "help"):
        return help_text(display_name)
    name, arg = cmd
    try:
        if name == "ultima":
            return _last_match(data, display_name)
        if name == "riepilogo":
            return _summary(arg or "oggi", data, display_name, now)
    except OpenDotaError:
        return "⚠️ Non riesco a leggere i dati da OpenDota in questo momento. Riprova tra un po'."
    return "🤔 Comando sconosciuto.\n\n" + help_text(display_name)


def _last_match(data: MatchData, display_name: str) -> str:
    if not data.recent:
        return "Nessuna partita trovata."
    last = data.recent[-1]
    streak = streak_until(data.recent, last["match_id"])
    previous = streak_before(data.recent, last["match_id"])
    return format_match(last, data.hero_name(last.get("hero_id")), display_name, streak, previous)


def _summary(period: str, data: MatchData, display_name: str, now: datetime) -> str:
    if period not in PERIODS:
        return "Uso: /riepilogo oggi · /riepilogo settimana · /riepilogo mese"
    days = PERIODS[period]
    start = start_of_day(now) if days is None else now - timedelta(days=days)
    matches = data.between(start, now)
    heroes = data.heroes({m.get("hero_id") or 0 for m in matches})
    return format_summary(PERIOD_TITLES[period], summarize(matches), heroes, display_name)


def process_updates(bot: Bot, state: State, data: MatchData, display_name: str, now: datetime) -> None:
    """Legge i messaggi nuovi e risponde. Gli errori non fermano il resto del giro."""
    try:
        updates = bot.get_updates(state.telegram_offset)
    except TelegramError as exc:
        log.warning("Lettura dei messaggi al bot non riuscita: %s", exc)
        return
    if not updates:
        return

    replies_per_chat: dict[int, int] = {}
    sent = skipped = failed = 0
    for msg in private_messages(updates):
        if replies_per_chat.get(msg.chat_id, 0) >= MAX_REPLIES_PER_CHAT:
            skipped += 1
            continue
        replies_per_chat[msg.chat_id] = replies_per_chat.get(msg.chat_id, 0) + 1
        try:
            bot.send_message(reply_for(msg.text, data, display_name, now), chat_id=msg.chat_id)
            sent += 1
        except TelegramError:
            failed += 1  # es. utente che ha bloccato il bot: non si ritenta

    # i messaggi letti vengono confermati anche se ignorati, così non si rileggono all'infinito
    last_id = max((u["update_id"] for u in updates if isinstance(u.get("update_id"), int)), default=None)
    if last_id is not None:
        state.telegram_offset = last_id + 1
    log.info("Comandi: %d risposte, %d ignorati per limite, %d invii falliti", sent, skipped, failed)


def ensure_bot_commands(bot: Bot, state: State) -> None:
    """Pubblica il menu '/' del bot una sola volta (o quando cambia versione)."""
    if state.commands_version == COMMANDS_VERSION:
        return
    try:
        bot.set_my_commands(BOT_COMMANDS)
        state.commands_version = COMMANDS_VERSION
    except TelegramError as exc:
        log.warning("Impostazione del menu comandi non riuscita: %s", exc)
