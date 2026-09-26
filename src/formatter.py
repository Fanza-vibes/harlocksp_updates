"""Costruzione dei messaggi Telegram (HTML). Solo funzioni pure."""

from __future__ import annotations

from datetime import date
from html import escape
from typing import Any

from .stats import Summary, is_radiant, is_win, kda, kda_ratio

# https://github.com/odota/dotaconstants (game_mode / lobby_type)
GAME_MODES: dict[int, str] = {
    0: "Sconosciuta",
    1: "All Pick",
    2: "Captains Mode",
    3: "Random Draft",
    4: "Single Draft",
    5: "All Random",
    6: "Intro",
    7: "Diretide",
    8: "Reverse Captains Mode",
    9: "Greeviling",
    10: "Tutorial",
    11: "Solo Mid",
    12: "Least Played",
    13: "Eroi limitati",
    14: "Compendium",
    15: "Personalizzata",
    16: "Captains Draft",
    17: "Balanced Draft",
    18: "Ability Draft",
    19: "Evento",
    20: "All Random Deathmatch",
    21: "1v1 Mid",
    22: "All Pick",  # "All Draft" in OpenDota = l'All Pick attuale
    23: "Turbo",
    24: "Mutation",
    25: "Coaches Challenge",
}
LOBBY_TYPES: dict[int, str] = {
    0: "Normale",
    1: "Allenamento",
    2: "Torneo",
    3: "Tutorial",
    4: "Contro i bot",
    5: "Classificata a squadre",
    6: "Classificata solo",
    7: "Classificata",
    8: "1v1 Mid",
    9: "Battle Cup",
    12: "Evento",
}
WEEKDAYS = ["lunedì", "martedì", "mercoledì", "giovedì", "venerdì", "sabato", "domenica"]
MONTHS = [
    "gennaio",
    "febbraio",
    "marzo",
    "aprile",
    "maggio",
    "giugno",
    "luglio",
    "agosto",
    "settembre",
    "ottobre",
    "novembre",
    "dicembre",
]

STREAK_MIN = 3  # vittorie di fila da festeggiare
LOSS_STREAK_MIN = 2  # sconfitte di fila da sottolineare
CURSE_BROKEN_MIN = 3  # vittoria che interrompe almeno N sconfitte di fila
KDA_STELLAR = 10.0
KILLS_MANY = 20


def format_duration(seconds: int) -> str:
    h, rem = divmod(max(int(seconds), 0), 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def format_hours(seconds: int) -> str:
    h, rem = divmod(max(int(seconds), 0), 3600)
    return f"{h}h {rem // 60:02d}m" if h else f"{rem // 60}m"


def format_date(d: date) -> str:
    return f"{WEEKDAYS[d.weekday()]} {d.day} {MONTHS[d.month - 1]}"


def mode_name(game_mode: int | None, lobby_type: int | None) -> str:
    mode = GAME_MODES.get(game_mode or 0, f"Modalità {game_mode}")
    lobby = LOBBY_TYPES.get(lobby_type) if lobby_type is not None else None
    if not lobby or lobby in ("Normale", mode):
        return mode
    return f"{lobby} · {mode}"


def match_links(match_id: int) -> str:
    return (
        f'<a href="https://www.dotabuff.com/matches/{match_id}">Dotabuff</a> · '
        f'<a href="https://www.opendota.com/matches/{match_id}">OpenDota</a>'
    )


def result_header(win: bool, streak: int = 0) -> str:
    """Titolo del messaggio: più sconfitte di fila = più pallini rossi."""
    if win:
        return "✅ <b>IL MAESTRO HA VINTO!</b> 🏆"
    losses = max(1, -streak)
    verb = "HA PERSO ANCORA" if losses >= LOSS_STREAK_MIN else "HA PERSO"
    return f"{'🔴' * min(losses, 5)} <b>IL MAESTRO {verb}!</b>"


def streak_lines(streak: int, previous: int = 0) -> list[str]:
    """Righe sulla serie in corso, subito sotto il titolo. Le sconfitte di fila vengono enfatizzate."""
    if streak >= STREAK_MIN:
        return [f"🔥 <b>{streak} vittorie di fila!</b> Il maestro è inarrestabile!"]
    if streak == 1 and previous <= -CURSE_BROKEN_MIN:
        return [f"💪 <b>Maledizione spezzata</b> dopo {-previous} sconfitte di fila!"]
    losses = -streak
    if losses < LOSS_STREAK_MIN:
        return []
    if losses == 2:
        return ["😬 <b>2 sconfitte di fila</b>… niente panico."]
    if losses == 3:
        return ["💀 <b>3 SCONFITTE DI FILA!</b> Qualcuno lo consoli…"]
    if losses == 4:
        return ["🚨 <b>4 SCONFITTE DI FILA!</b> Il maestro è in crisi!"]
    return [f"🆘 <b>{losses} SCONFITTE DI FILA!</b> Allarme rosso: togliete il mouse al maestro!"]


def highlights(match: dict[str, Any]) -> list[str]:
    """Le righe speciali per le prestazioni notevoli (vuota = partita normale)."""
    k, d, a = kda(match)
    out = []
    if d == 0 and k + a >= 5:
        out.append("🛡 Partita perfetta: <b>0 morti</b>!")
    elif kda_ratio(match) >= KDA_STELLAR:
        out.append(f"🌟 KDA stellare: <b>{kda_ratio(match):.1f}</b>")
    if k >= KILLS_MANY:
        out.append(f"🩸 Massacro: <b>{k} kill</b>")
    return out


def format_match(
    match: dict[str, Any], hero_name: str, display_name: str, streak: int = 0, previous_streak: int = 0
) -> str:
    win = is_win(match)
    side = "Radiant" if is_radiant(int(match.get("player_slot") or 0)) else "Dire"
    header = result_header(win, streak)
    special = highlights(match)
    if special:
        header = "🌟 " + header
    k, d, a = kda(match)
    lines = [
        header,
        *streak_lines(streak, previous_streak),
        f"👤 {escape(display_name)}",
        f"🦸 Eroe: <b>{escape(hero_name)}</b> ({side})",
        f"⚔️ K/D/A: <b>{k}/{d}/{a}</b> (KDA {kda_ratio(match):.1f})",
        f"💰 GPM/XPM: {int(match.get('gold_per_min') or 0)}/{int(match.get('xp_per_min') or 0)}"
        f" · 🗡 LH: {int(match.get('last_hits') or 0)}",
        f"⏱ Durata: {format_duration(match.get('duration') or 0)}"
        f" · 🎮 {escape(mode_name(match.get('game_mode'), match.get('lobby_type')))}",
        *special,
        f"🔗 {match_links(int(match['match_id']))}",
    ]
    return "\n".join(lines)


def format_summary(title: str, summary: Summary | None, heroes: dict[int, str], display_name: str) -> str:
    head = f"📊 <b>{escape(title)}</b> – {escape(display_name)}"
    if summary is None:
        return f"{head}\n\nNessuna partita giocata in questo periodo. 😴"
    k, d, a = summary.avg_kda
    lines = [
        head,
        "",
        f"🎮 Partite: <b>{summary.games}</b> ({summary.wins}V – {summary.losses}S)",
        f"📈 Win rate: <b>{summary.winrate:.0f}%</b>",
        f"⚔️ K/D/A medio: {k:.1f}/{d:.1f}/{a:.1f}",
        f"⏱ Tempo di gioco: {format_hours(summary.total_seconds)}",
    ]
    if summary.top_heroes:
        lines += ["", "🦸 <b>Eroi più usati</b>"]
        for hero_id, games, wins in summary.top_heroes:
            name = escape(heroes.get(hero_id or 0, f"Eroe #{hero_id}"))
            lines.append(f"• {name}: {games} {'partita' if games == 1 else 'partite'} ({wins}V)")
    if summary.best:
        b = summary.best
        bk, bd, ba = kda(b)
        name = escape(heroes.get(b.get("hero_id") or 0, f"Eroe #{b.get('hero_id')}"))
        esito = "vittoria" if is_win(b) else "sconfitta"
        lines += [
            "",
            f"🏆 <b>Miglior partita</b>: {name} {bk}/{bd}/{ba} ({esito})",
            f"🔗 {match_links(int(b['match_id']))}",
        ]
    return "\n".join(lines)
