"""Entrypoint: controlla le nuove partite e le pubblica su Telegram.

Uso: python -m src.main [--dry-run] [--last N] [--config config.yaml] [--state state.json]
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timezone
from typing import Any

from .config import Config, ConfigError, load_config
from .formatter import format_match
from .opendota import OpenDotaClient, OpenDotaError
from .state import State, load_state, save_state
from .telegram import DryRunSender, Sender, TelegramClient, TelegramError

log = logging.getLogger("harlocksp")

EXIT_OK = 0
EXIT_SEND_FAILED = 1
EXIT_CONFIG = 2


def select_new_matches(matches: list[dict[str, Any]], last_match_id: int) -> list[dict[str, Any]]:
    """Partite con match_id > last_match_id, in ordine cronologico."""
    new = [m for m in matches if m["match_id"] > last_match_id]
    return sorted(new, key=lambda m: (m.get("start_time") or 0, m["match_id"]))


def ensure_heroes(state: State, client: OpenDotaClient, hero_ids: set[int]) -> None:
    """Aggiorna la cache degli eroi se è vuota o manca qualche eroe. Mai fatale."""
    if state.heroes and hero_ids <= state.heroes.keys():
        return
    try:
        state.heroes = client.heroes()
        state.heroes_updated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except OpenDotaError as exc:
        log.warning("Impossibile aggiornare gli eroi (%s): uso i nomi di riserva", exc)


def hero_name(state: State, hero_id: int | None) -> str:
    return state.heroes.get(hero_id or 0, f"Eroe #{hero_id}")


def run(
    config: Config,
    state_path: str,
    client: OpenDotaClient,
    sender: Sender,
    dry_run: bool = False,
    last: int = 0,
) -> int:
    state = load_state(state_path)

    try:
        matches = client.recent_matches(config.player_id)
    except OpenDotaError as exc:
        log.error("%s – stato invariato, riprovo al prossimo giro", exc)
        return EXIT_OK
    if not matches:
        log.info("Nessuna partita restituita da OpenDota")
        return EXIT_OK

    newest_id = max(m["match_id"] for m in matches)

    if dry_run and last > 0:
        to_send = select_new_matches(matches, 0)[-last:]
    elif state.last_match_id is None:
        log.info("Primo avvio: salvo l'ultima partita (%s) senza inviare nulla", newest_id)
        state.last_match_id = newest_id
        if not dry_run:
            save_state(state_path, state)
        return EXIT_OK
    else:
        to_send = select_new_matches(matches, state.last_match_id)

    if not to_send:
        log.info("Nessuna nuova partita (ultima: %s)", state.last_match_id)
        return EXIT_OK

    log.info("%d nuove partite da inviare", len(to_send))
    ensure_heroes(state, client, {m.get("hero_id") or 0 for m in to_send})

    for match in to_send:
        text = format_match(match, hero_name(state, match.get("hero_id")), config.display_name)
        try:
            sender.send_message(text)
        except TelegramError as exc:
            # lo stato su disco è già aggiornato all'ultima partita inviata con successo
            log.error("Invio della partita %s fallito: %s", match["match_id"], exc)
            return EXIT_SEND_FAILED
        state.last_match_id = max(state.last_match_id or 0, match["match_id"])
        if not dry_run:
            save_state(state_path, state)
        log.info("Inviata partita %s", match["match_id"])
    return EXIT_OK


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Aggiornamenti Dota 2 su Telegram")
    p.add_argument("--dry-run", action="store_true", help="stampa i messaggi, non invia e non salva")
    p.add_argument("--last", type=int, default=0, help="con --dry-run: mostra le ultime N partite")
    p.add_argument("--config", default="config.yaml")
    p.add_argument("--state", default="state.json")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = parse_args(argv)
    try:
        config = load_config(args.config, require_secrets=not args.dry_run)
    except ConfigError as exc:
        log.error("Configurazione: %s", exc)
        return EXIT_CONFIG

    sender: Sender
    if args.dry_run:
        sender = DryRunSender()
    else:
        assert config.telegram_token and config.telegram_chat_id
        sender = TelegramClient(config.telegram_token, config.telegram_chat_id)
    return run(config, args.state, OpenDotaClient(), sender, dry_run=args.dry_run, last=args.last)


if __name__ == "__main__":
    sys.exit(main())
