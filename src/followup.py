"""Secondo messaggio con le curiosità, quando OpenDota ha analizzato il replay.

Flusso: la scheda della partita entra in `state.pending_trivia`; a ogni giro si controlla se il
replay è stato analizzato (chiedendo l'analisi se serve) e, quando è pronto, si risponde alla
scheda con le curiosità. Dopo TRIVIA_MAX_AGE senza analisi si rinuncia in silenzio.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Protocol

from .data import MatchData
from .opendota import OpenDotaError
from .state import Pending, State
from .telegram import Sender, TelegramError
from .trivia import facts, find_player, format_trivia, is_parsed, pick

log = logging.getLogger(__name__)

TRIVIA_MAX_AGE = 3 * 3600  # secondi
TRIVIA_PER_ROUND = 3  # partite controllate al massimo per giro (limite chiamate OpenDota)


class TriviaAPI(Protocol):
    """Ciò che le curiosità usano di OpenDota (in produzione: `OpenDotaClient`)."""

    def match(self, match_id: int) -> dict[str, Any]: ...
    def request_parse(self, match_id: int) -> None: ...
    def hero_keys(self) -> dict[str, str]: ...


def trivia_text(match: dict[str, Any], player_id: int, client: TriviaAPI, data: MatchData) -> str | None:
    """Testo delle curiosità, oppure None se il giocatore non c'è o non c'è niente di notevole."""
    player = find_player(match, player_id)
    if player is None:
        return None
    hero_name = data.hero_name(player.get("hero_id"))
    try:
        hero_keys = client.hero_keys()
    except OpenDotaError:
        hero_keys = {}  # nomi ricavati dal nome interno ("npc_dota_hero_pudge" → "Pudge")
    chosen = pick(facts(match, player, hero_name, hero_keys))
    return format_trivia(hero_name, chosen) if chosen else None


def send_pending_trivia(
    state: State, client: TriviaAPI, sender: Sender, player_id: int, data: MatchData, now: datetime
) -> None:
    """Controlla le partite in attesa e pubblica le curiosità pronte. Gli errori non sono mai fatali."""
    now_ts = int(now.timestamp())
    keep: list[Pending] = []
    checked = 0
    for item in state.pending_trivia:
        if now_ts - item.since > TRIVIA_MAX_AGE:
            log.info("Curiosità della partita %s: analisi non arrivata, rinuncio", item.match_id)
            continue
        if checked >= TRIVIA_PER_ROUND:
            keep.append(item)
            continue
        checked += 1
        if not _process(item, client, sender, player_id, data):
            keep.append(item)
    state.pending_trivia = keep


def _process(item: Pending, client: TriviaAPI, sender: Sender, player_id: int, data: MatchData) -> bool:
    """True se la partita è conclusa (curiosità inviate o niente da dire), False se va ricontrollata."""
    try:
        match = client.match(item.match_id)
        if not is_parsed(match):
            if not item.requested:
                client.request_parse(item.match_id)
                item.requested = True
                log.info("Curiosità della partita %s: analisi del replay richiesta", item.match_id)
            return False
    except OpenDotaError as exc:
        log.warning("Curiosità della partita %s rimandate: %s", item.match_id, exc)
        return False

    text = trivia_text(match, player_id, client, data)
    if text is None:
        log.info("Curiosità della partita %s: niente di notevole", item.match_id)
        return True
    try:
        sender.send_message(text, reply_to=item.message_id)
    except TelegramError as exc:
        log.warning("Invio delle curiosità della partita %s fallito: %s", item.match_id, exc)
        return False
    log.info("Inviate le curiosità della partita %s", item.match_id)
    return True
