"""Statistiche e finestre temporali. Solo funzioni pure, facili da testare."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

Match = dict[str, Any]


def is_radiant(player_slot: int) -> bool:
    """Gli slot 0-127 sono Radiant, 128-255 Dire (convenzione di Valve/OpenDota)."""
    return player_slot < 128


def is_win(match: Match) -> bool:
    """Vittoria se la squadra del giocatore coincide con quella vincitrice."""
    return bool(match.get("radiant_win")) == is_radiant(int(match.get("player_slot") or 0))


def kda(match: Match) -> tuple[int, int, int]:
    """(kill, morti, assist) della partita, 0 se il dato manca."""
    return tuple(int(match.get(x) or 0) for x in ("kills", "deaths", "assists"))  # type: ignore[return-value]


def kda_ratio(match: Match) -> float:
    """Rapporto KDA classico: (kill + assist) / morti, con morti minimo 1."""
    k, d, a = kda(match)
    return (k + a) / max(d, 1)


def chronological(matches: list[Match]) -> list[Match]:
    """Partite ordinate dalla più vecchia alla più recente (a parità di orario, per ID)."""
    return sorted(matches, key=lambda m: (m.get("start_time") or 0, m["match_id"]))


def streak_until(matches: list[Match], match_id: int) -> int:
    """Serie di risultati uguali consecutivi che termina con match_id.

    Positivo = vittorie, negativo = sconfitte, 0 se la partita non è nella lista.
    Calcolata dalle partite recenti, così non serve salvarla nello stato.
    """
    ordered = chronological(matches)
    idx = next((i for i, m in enumerate(ordered) if m["match_id"] == match_id), None)
    if idx is None:
        return 0
    won = is_win(ordered[idx])
    count = 0
    for m in reversed(ordered[: idx + 1]):
        if is_win(m) != won:
            break
        count += 1
    return count if won else -count


def streak_before(matches: list[Match], match_id: int) -> int:
    """Serie che era in corso prima di match_id (0 se è la prima partita della lista)."""
    ordered = chronological(matches)
    idx = next((i for i, m in enumerate(ordered) if m["match_id"] == match_id), None)
    if not idx:
        return 0
    return streak_until(ordered, ordered[idx - 1]["match_id"])


@dataclass
class Summary:
    """Statistiche aggregate di un gruppo di partite (usate dai riepiloghi)."""

    games: int
    wins: int
    avg_kda: tuple[float, float, float]
    total_seconds: int
    top_heroes: list[tuple[int | None, int, int]] = field(default_factory=list)  # (eroe, partite, vittorie)
    best: Match | None = None

    @property
    def losses(self) -> int:
        """Numero di sconfitte."""
        return self.games - self.wins

    @property
    def winrate(self) -> float:
        """Percentuale di vittorie (0-100)."""
        return 100 * self.wins / self.games if self.games else 0.0


def summarize(matches: list[Match], top: int = 3) -> Summary | None:
    """Aggrega le partite: vittorie, K/D/A medio, tempo di gioco, eroi più usati, miglior partita.

    Restituisce None se la lista è vuota. La miglior partita è quella con il KDA più alto.
    """
    if not matches:
        return None
    n = len(matches)
    wins = sum(is_win(m) for m in matches)
    totals = [sum(kda(m)[i] for m in matches) for i in range(3)]
    played = Counter(m.get("hero_id") for m in matches)
    won = Counter(m.get("hero_id") for m in matches if is_win(m))
    # a parità di partite, prima l'eroe con più vittorie
    heroes = sorted(played, key=lambda h: (-played[h], -won[h], h or 0))[:top]
    return Summary(
        games=n,
        wins=wins,
        avg_kda=(totals[0] / n, totals[1] / n, totals[2] / n),
        total_seconds=sum(int(m.get("duration") or 0) for m in matches),
        top_heroes=[(h, played[h], won[h]) for h in heroes],
        best=max(matches, key=lambda m: (kda_ratio(m), kda(m)[0], is_win(m))),
    )


def end_time(match: Match) -> int:
    """Timestamp unix di fine partita (inizio + durata)."""
    return int(match.get("start_time") or 0) + int(match.get("duration") or 0)


def in_window(matches: list[Match], start: datetime, end: datetime) -> list[Match]:
    """Partite *terminate* in [start, end): una partita a cavallo delle 23 finisce nel giorno dopo."""
    lo, hi = start.timestamp(), end.timestamp()
    return [m for m in matches if lo <= end_time(m) < hi]


def summary_target(now: datetime, hour: int) -> date:
    """Il giorno il cui riepilogo è 'dovuto' adesso: oggi dopo l'ora X, altrimenti ieri."""
    return now.date() if now.hour >= hour else now.date() - timedelta(days=1)


def daily_window(day: date, hour: int, tz: ZoneInfo) -> tuple[datetime, datetime]:
    """Dalle `hour` del giorno prima alle `hour` di `day`: nessuna partita resta fuori."""
    end = datetime.combine(day, time(hour), tzinfo=tz)
    return end - timedelta(days=1), end


def start_of_day(now: datetime) -> datetime:
    """Mezzanotte dello stesso giorno, nello stesso fuso orario."""
    return now.replace(hour=0, minute=0, second=0, microsecond=0)
