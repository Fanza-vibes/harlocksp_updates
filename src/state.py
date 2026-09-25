"""Lettura/scrittura di state.json. Uno stato illeggibile equivale al primo avvio."""

from __future__ import annotations

import json
import logging
import os
import tempfile
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, TypeGuard

log = logging.getLogger(__name__)

MAX_PENDING = 10


@dataclass
class Pending:
    """Partita pubblicata nel canale in attesa dell'analisi del replay per le curiosità."""

    match_id: int
    message_id: int  # messaggio del canale a cui rispondere
    since: int  # timestamp unix della pubblicazione
    requested: bool = False  # analisi già chiesta a OpenDota

    def to_dict(self) -> dict[str, Any]:
        return {
            "match_id": self.match_id,
            "message_id": self.message_id,
            "since": self.since,
            "requested": self.requested,
        }


@dataclass
class State:
    last_match_id: int | None = None
    heroes: dict[int, str] = field(default_factory=dict)
    heroes_updated_at: str | None = None
    telegram_offset: int | None = None  # prossimo update_id da leggere con getUpdates
    last_summary_date: str | None = None  # giorno (ISO) dell'ultimo riepilogo nel canale
    commands_version: int | None = None  # versione del menu comandi già inviata a Telegram
    pending_trivia: list[Pending] = field(default_factory=list)

    def add_pending(self, item: Pending) -> None:
        self.pending_trivia = [*self.pending_trivia, item][-MAX_PENDING:]

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {}
        if self.last_match_id is not None:
            data["last_match_id"] = self.last_match_id
        if self.heroes:
            # chiavi JSON sempre stringa, ordinate numericamente per diff stabili
            data["heroes"] = {str(k): self.heroes[k] for k in sorted(self.heroes)}
        if self.heroes_updated_at:
            data["heroes_updated_at"] = self.heroes_updated_at
        for key in ("telegram_offset", "last_summary_date", "commands_version"):
            if getattr(self, key) is not None:
                data[key] = getattr(self, key)
        if self.pending_trivia:
            data["pending_trivia"] = [p.to_dict() for p in self.pending_trivia]
        return data


def load_state(path: str | Path) -> State:
    path = Path(path)
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        log.info("%s non trovato: primo avvio", path)
        return State()
    if not raw.strip():
        return State()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        log.warning("%s corrotto (%s): lo tratto come primo avvio", path, exc)
        return State()
    return _parse(data, path)


def _parse(data: Any, path: Path) -> State:
    if not isinstance(data, dict):
        log.warning("%s non è un oggetto JSON: lo tratto come primo avvio", path)
        return State()

    last = _positive_int(data, "last_match_id", path)

    heroes: dict[int, str] = {}
    raw_heroes = data.get("heroes")
    if isinstance(raw_heroes, dict):
        for k, v in raw_heroes.items():
            try:
                heroes[int(k)] = str(v)
            except (TypeError, ValueError):
                continue
    updated = data.get("heroes_updated_at")
    summary_date = data.get("last_summary_date")
    if not _is_iso_date(summary_date):
        summary_date = None
    return State(
        last_match_id=last,
        heroes=heroes,
        heroes_updated_at=updated if isinstance(updated, str) and heroes else None,
        telegram_offset=_positive_int(data, "telegram_offset", path),
        last_summary_date=summary_date,
        commands_version=_positive_int(data, "commands_version", path),
        pending_trivia=_parse_pending(data.get("pending_trivia")),
    )


def _parse_pending(raw: Any) -> list[Pending]:
    if not isinstance(raw, list):
        return []
    out = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        match_id, message_id, since = (item.get(k) for k in ("match_id", "message_id", "since"))
        if _is_pos_int(match_id) and _is_pos_int(message_id) and _is_pos_int(since):
            out.append(Pending(match_id, message_id, since, requested=item.get("requested") is True))
    return out[-MAX_PENDING:]


def _is_pos_int(value: Any) -> TypeGuard[int]:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _is_iso_date(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _positive_int(data: dict, key: str, path: Path) -> int | None:
    value = data.get(key)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        log.warning("%s: %s non valido (%r), ignorato", path, key, value)
        return None
    return value


def save_state(path: str | Path, state: State) -> None:
    """Scrittura atomica: file temporaneo nella stessa cartella + os.replace."""
    path = Path(path)
    text = json.dumps(state.to_dict(), indent=2, ensure_ascii=False) + "\n"
    fd, tmp = tempfile.mkstemp(dir=path.parent or ".", prefix=".state-", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
