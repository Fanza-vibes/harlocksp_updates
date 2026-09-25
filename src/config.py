"""Configurazione: config.yaml per le opzioni, variabili d'ambiente per i segreti."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

import yaml


class ConfigError(Exception):
    """Configurazione mancante o non valida."""


@dataclass(frozen=True)
class Config:
    player_id: int
    display_name: str
    language: str = "it"
    telegram_token: str | None = field(default=None, repr=False)
    telegram_chat_id: str | None = None

    def __repr__(self) -> str:  # il token non deve mai finire nei log
        token = "***" if self.telegram_token else None
        return (
            f"Config(player_id={self.player_id}, display_name={self.display_name!r}, "
            f"language={self.language!r}, telegram_token={token}, "
            f"telegram_chat_id={self.telegram_chat_id!r})"
        )

    __str__ = __repr__


def load_config(
    path: str | Path = "config.yaml",
    env: Mapping[str, str] | None = None,
    require_secrets: bool = True,
) -> Config:
    """Carica la configurazione. Con require_secrets=False (dry-run) i segreti sono opzionali."""
    env = os.environ if env is None else env
    data = _read_yaml(Path(path))

    try:
        player_id = int(data["player_id"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ConfigError(f"{path}: 'player_id' mancante o non numerico") from exc

    token = env.get("TELEGRAM_TOKEN") or None
    chat_id = env.get("TELEGRAM_CHAT_ID") or None
    if require_secrets:
        missing = [n for n, v in (("TELEGRAM_TOKEN", token), ("TELEGRAM_CHAT_ID", chat_id)) if not v]
        if missing:
            raise ConfigError("Variabili d'ambiente mancanti: " + ", ".join(missing))

    return Config(
        player_id=player_id,
        display_name=str(data.get("display_name") or player_id),
        language=str(data.get("language") or "it"),
        telegram_token=token,
        telegram_chat_id=chat_id,
    )


def _read_yaml(path: Path) -> dict[str, Any]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"File di configurazione non trovato: {path}") from exc
    except yaml.YAMLError as exc:
        raise ConfigError(f"{path}: YAML non valido: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError(f"{path}: deve contenere una mappa chiave/valore")
    return data
