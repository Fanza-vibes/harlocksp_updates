"""Lettura/scrittura di state.json. Uno stato illeggibile equivale al primo avvio."""

from __future__ import annotations

import json
import logging
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)


@dataclass
class State:
    last_match_id: int | None = None
    heroes: dict[int, str] = field(default_factory=dict)
    heroes_updated_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {}
        if self.last_match_id is not None:
            data["last_match_id"] = self.last_match_id
        if self.heroes:
            # chiavi JSON sempre stringa, ordinate numericamente per diff stabili
            data["heroes"] = {str(k): self.heroes[k] for k in sorted(self.heroes)}
        if self.heroes_updated_at:
            data["heroes_updated_at"] = self.heroes_updated_at
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

    last = data.get("last_match_id")
    if last is not None and (isinstance(last, bool) or not isinstance(last, int) or last <= 0):
        log.warning("%s: last_match_id non valido (%r), ignorato", path, last)
        last = None

    heroes: dict[int, str] = {}
    raw_heroes = data.get("heroes")
    if isinstance(raw_heroes, dict):
        for k, v in raw_heroes.items():
            try:
                heroes[int(k)] = str(v)
            except (TypeError, ValueError):
                continue
    updated = data.get("heroes_updated_at")
    return State(
        last_match_id=last,
        heroes=heroes,
        heroes_updated_at=updated if isinstance(updated, str) and heroes else None,
    )


def save_state(path: str | Path, state: State) -> None:
    """Scrittura atomica: file temporaneo nella stessa cartella + os.replace."""
    path = Path(path)
    text = json.dumps(state.to_dict(), indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    fd, tmp = tempfile.mkstemp(dir=path.parent or ".", prefix=".state-", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
