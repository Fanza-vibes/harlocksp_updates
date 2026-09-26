"""Dati di OpenDota per un singolo giro, con cache: ogni chiamata si fa al massimo una volta."""

from __future__ import annotations

import logging
import math
from datetime import UTC, datetime, timedelta
from typing import Protocol

from .opendota import OpenDotaError
from .state import State
from .stats import Match, chronological, in_window

log = logging.getLogger(__name__)

RECENT_LIMIT = 20  # recentMatches restituisce al massimo 20 partite
HEROES_MAX_AGE = timedelta(days=7)


class OpenDotaAPI(Protocol):
    """Ciò che `MatchData` usa di OpenDota (in produzione: `OpenDotaClient`; nei test: fake)."""

    def recent_matches(self, player_id: int) -> list[Match]: ...
    def player_matches(self, player_id: int, days: int) -> list[Match]: ...
    def heroes(self) -> dict[int, str]: ...


class MatchData:
    """Accesso ai dati delle partite durante un giro.

    Parte dalle partite recenti (già scaricate) e fa altre chiamate solo se servono, al massimo una
    volta per periodo. Gestisce anche la cache dei nomi degli eroi salvata in `state.json`.
    """

    def __init__(
        self,
        client: OpenDotaAPI,
        player_id: int,
        recent: list[Match],
        state: State,
        now: datetime | None = None,
    ) -> None:
        self.now = now or datetime.now(UTC)
        self.client = client
        self.player_id = player_id
        self.recent = chronological(recent)
        self.state = state
        self._periods: dict[int, list[Match]] = {}
        self._heroes_checked = False

    def between(self, start: datetime, end: datetime) -> list[Match]:
        """Partite terminate in [start, end). Usa le recenti se bastano, altrimenti una chiamata in più.

        Può sollevare OpenDotaError.
        """
        if self._recent_covers(start):
            source = self.recent
        else:
            days = math.ceil((self.now - start).total_seconds() / 86400) + 1
            source = self._period(days)
        return chronological(in_window(source, start, end))

    def _recent_covers(self, start: datetime) -> bool:
        if len(self.recent) < RECENT_LIMIT:
            return True  # meno di 20 partite in totale: le recenti sono tutto lo storico disponibile
        oldest = self.recent[0].get("start_time") or 0
        return oldest < start.timestamp()

    def _period(self, days: int) -> list[Match]:
        if days not in self._periods:
            self._periods[days] = self.client.player_matches(self.player_id, days)
        return self._periods[days]

    def heroes(self, needed: set[int]) -> dict[int, str]:
        """Nomi degli eroi. Aggiorna la cache se manca un eroe o ha più di 7 giorni. Mai fatale."""
        if not self._heroes_checked and (self._heroes_stale() or not needed <= self.state.heroes.keys()):
            self._heroes_checked = True  # al massimo un tentativo per giro
            try:
                self.state.heroes = self.client.heroes()
                self.state.heroes_updated_at = self.now.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
            except OpenDotaError as exc:
                log.warning("Impossibile aggiornare gli eroi (%s): uso i nomi di riserva", exc)
        return self.state.heroes

    def hero_name(self, hero_id: int | None) -> str:
        """Nome visualizzato di un eroe, con 'Eroe #id' come riserva se l'eroe è sconosciuto."""
        return self.heroes({hero_id or 0}).get(hero_id or 0, f"Eroe #{hero_id}")

    def _heroes_stale(self) -> bool:
        if not self.state.heroes or not self.state.heroes_updated_at:
            return True
        try:
            updated = datetime.strptime(self.state.heroes_updated_at, "%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            return True
        return self.now - updated.replace(tzinfo=UTC) > HEROES_MAX_AGE
