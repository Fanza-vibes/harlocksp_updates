"""Entrypoint di un giro del bot.

1. nuove partite → messaggio nel canale
2. messaggi privati al bot → risposte ai comandi
3. dopo le 23 (ora italiana) → riepilogo giornaliero nel canale, se ha giocato

Uso: python -m src.main [--dry-run] [--last N] [--comando "/riepilogo oggi"]
                        [--config config.yaml] [--state state.json]
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

from .commands import Bot, ensure_bot_commands, process_updates, reply_for
from .config import Config, ConfigError, load_config
from .data import MatchData, OpenDotaAPI
from .formatter import format_date, format_match, format_summary
from .opendota import OpenDotaClient, OpenDotaError
from .state import State, load_state, save_state
from .stats import chronological, daily_window, streak_until, summarize, summary_target
from .telegram import DryRunSender, Sender, TelegramClient, TelegramError

log = logging.getLogger("harlocksp")

EXIT_OK = 0
EXIT_SEND_FAILED = 1
EXIT_CONFIG = 2


def select_new_matches(matches: list[dict], last_match_id: int) -> list[dict]:
    """Partite con match_id > last_match_id, in ordine cronologico."""
    return chronological([m for m in matches if m["match_id"] > last_match_id])


def notify_new_matches(
    state: State, data: MatchData, sender: Sender, config: Config, save, dry_run: bool, last: int
) -> int:
    if not data.recent:
        log.info("Nessuna partita restituita da OpenDota")
        return EXIT_OK
    newest_id = max(m["match_id"] for m in data.recent)

    if dry_run and last > 0:
        to_send = data.recent[-last:]
    elif state.last_match_id is None:
        log.info("Primo avvio: salvo l'ultima partita (%s) senza inviare nulla", newest_id)
        state.last_match_id = newest_id
        save()
        return EXIT_OK
    else:
        to_send = select_new_matches(data.recent, state.last_match_id)

    if not to_send:
        log.info("Nessuna nuova partita (ultima: %s)", state.last_match_id)
        return EXIT_OK

    log.info("%d nuove partite da inviare", len(to_send))
    data.heroes({m.get("hero_id") or 0 for m in to_send})
    for match in to_send:
        streak = streak_until(data.recent, match["match_id"])
        text = format_match(match, data.hero_name(match.get("hero_id")), config.display_name, streak)
        try:
            sender.send_message(text)
        except TelegramError as exc:
            # lo stato su disco è già aggiornato all'ultima partita inviata con successo
            log.error("Invio della partita %s fallito: %s", match["match_id"], exc)
            return EXIT_SEND_FAILED
        state.last_match_id = max(state.last_match_id or 0, match["match_id"])
        save()
        log.info("Inviata partita %s", match["match_id"])
    return EXIT_OK


def send_daily_summary(state: State, data: MatchData, sender: Sender, config: Config, now: datetime) -> int:
    """Riepilogo nel canale una volta al giorno dopo l'ora configurata, solo se ha giocato."""
    hour = config.daily_summary_hour
    if hour is None:
        return EXIT_OK
    target = summary_target(now, hour)
    if state.last_summary_date is None:
        state.last_summary_date = target.isoformat()  # primo avvio: si parte dal prossimo
        return EXIT_OK
    if state.last_summary_date >= target.isoformat():
        return EXIT_OK

    start, end = daily_window(target, hour, ZoneInfo(config.timezone))
    try:
        matches = data.between(start, end)
    except OpenDotaError as exc:
        log.warning("Riepilogo giornaliero rimandato: %s", exc)
        return EXIT_OK
    if matches:
        heroes = data.heroes({m.get("hero_id") or 0 for m in matches})
        text = format_summary(f"Riepilogo di {format_date(target)}", summarize(matches), heroes, config.display_name)
        try:
            sender.send_message(text)
        except TelegramError as exc:
            log.error("Invio del riepilogo giornaliero fallito: %s", exc)
            return EXIT_SEND_FAILED
        log.info("Inviato il riepilogo di %s (%d partite)", target, len(matches))
    else:
        log.info("Nessuna partita il %s: niente riepilogo", target)
    state.last_summary_date = target.isoformat()
    return EXIT_OK


def run(
    config: Config,
    state_path: str,
    client: OpenDotaAPI,
    sender: Sender,
    *,
    bot: Bot | None = None,
    dry_run: bool = False,
    last: int = 0,
    command: str | None = None,
    now: datetime | None = None,
) -> int:
    now = now or datetime.now(ZoneInfo(config.timezone))
    state = load_state(state_path)

    def save() -> None:
        if not dry_run:
            save_state(state_path, state)

    try:
        recent = client.recent_matches(config.player_id)
    except OpenDotaError as exc:
        log.error("%s – stato invariato, riprovo al prossimo giro", exc)
        return EXIT_OK
    data = MatchData(client, config.player_id, recent, state, now)

    if command is not None:  # prova locale di un comando, senza Telegram
        sender.send_message(reply_for(command, data, config.display_name, now), chat_id="prova")
        return EXIT_OK

    rc = notify_new_matches(state, data, sender, config, save, dry_run, last)
    if rc != EXIT_OK:
        return rc
    if bot is not None:
        ensure_bot_commands(bot, state)
        process_updates(bot, state, data, config.display_name, now)
        save()  # l'offset va salvato subito: evita risposte doppie se il seguito fallisce
    rc = send_daily_summary(state, data, sender, config, now)
    save()
    return rc


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Aggiornamenti Dota 2 su Telegram")
    p.add_argument("--dry-run", action="store_true", help="stampa i messaggi, non invia e non salva")
    p.add_argument("--last", type=int, default=0, help="con --dry-run: mostra le ultime N partite")
    p.add_argument("--comando", dest="command", help='con --dry-run: prova un comando, es. "/riepilogo oggi"')
    p.add_argument("--config", default="config.yaml")
    p.add_argument("--state", default="state.json")
    args = p.parse_args(argv)
    if args.command is not None and not args.dry_run:
        p.error("--comando si usa solo insieme a --dry-run")
    return args


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    # urllib3 a livello DEBUG logga il percorso delle richieste, che per Telegram contiene il token
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    args = parse_args(argv)
    try:
        config = load_config(args.config, require_secrets=not args.dry_run)
    except ConfigError as exc:
        log.error("Configurazione: %s", exc)
        return EXIT_CONFIG

    sender: Sender
    bot: Bot | None = None
    if args.dry_run:
        sender = DryRunSender()
    else:
        assert config.telegram_token and config.telegram_chat_id
        sender = bot = TelegramClient(config.telegram_token, config.telegram_chat_id)
    return run(
        config, args.state, OpenDotaClient(), sender,
        bot=bot, dry_run=args.dry_run, last=args.last, command=args.command,
    )


if __name__ == "__main__":
    sys.exit(main())
