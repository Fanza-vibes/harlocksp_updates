"""Costruzione dei messaggi Telegram (HTML). Solo funzioni pure."""

from __future__ import annotations

from html import escape
from typing import Any

# Mappa minima; la Fase 2 la estende a tutte le modalità.
GAME_MODES: dict[int, str] = {
    1: "All Pick",
    2: "Captains Mode",
    3: "Random Draft",
    4: "Single Draft",
    5: "All Random",
    22: "All Pick",  # "All Draft" in OpenDota = l'All Pick attuale
    23: "Turbo",
}
LOBBY_RANKED = 7


def is_radiant(player_slot: int) -> bool:
    return player_slot < 128


def is_win(match: dict[str, Any]) -> bool:
    return bool(match.get("radiant_win")) == is_radiant(int(match.get("player_slot", 0)))


def format_duration(seconds: int) -> str:
    h, rem = divmod(max(int(seconds), 0), 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def mode_name(game_mode: int | None, lobby_type: int | None) -> str:
    mode = GAME_MODES.get(game_mode or 0, f"Modalità {game_mode}")
    return f"Ranked {mode}" if lobby_type == LOBBY_RANKED else mode


def match_links(match_id: int) -> str:
    return (
        f'<a href="https://www.dotabuff.com/matches/{match_id}">Dotabuff</a> · '
        f'<a href="https://www.opendota.com/matches/{match_id}">OpenDota</a>'
    )


def format_match(match: dict[str, Any], hero_name: str, display_name: str) -> str:
    win = is_win(match)
    side = "Radiant" if is_radiant(int(match.get("player_slot", 0))) else "Dire"
    header = "✅ <b>VITTORIA</b>" if win else "❌ <b>SCONFITTA</b>"
    k, d, a = (int(match.get(x) or 0) for x in ("kills", "deaths", "assists"))
    lines = [
        f"{header} – {escape(display_name)}",
        f"🦸 Eroe: <b>{escape(hero_name)}</b> ({side})",
        f"⚔️ K/D/A: <b>{k}/{d}/{a}</b>",
        f"💰 GPM/XPM: {int(match.get('gold_per_min') or 0)}/{int(match.get('xp_per_min') or 0)}"
        f" · 🗡 LH: {int(match.get('last_hits') or 0)}",
        f"⏱ Durata: {format_duration(match.get('duration') or 0)}"
        f" · 🎮 {escape(mode_name(match.get('game_mode'), match.get('lobby_type')))}",
        f"🔗 {match_links(int(match['match_id']))}",
    ]
    return "\n".join(lines)
