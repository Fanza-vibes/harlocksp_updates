"""Client minimale per l'API pubblica di OpenDota (senza chiave)."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Any

import requests

log = logging.getLogger(__name__)

BASE_URL = "https://api.opendota.com/api"
TIMEOUT = (10, 20)  # connessione, lettura
RETRY_STATUS = {429, 500, 502, 503, 504}


class OpenDotaError(Exception):
    """L'API non ha risposto correttamente neanche dopo i retry."""


class OpenDotaClient:
    """Client HTTP per l'API pubblica di OpenDota (senza chiave).

    Ogni chiamata ha un timeout e fino a `retries` nuovi tentativi con attesa esponenziale sugli
    errori temporanei (rete, 429, 5xx). Se non riesce solleva `OpenDotaError`.
    Limiti gratuiti di OpenDota: circa 60 chiamate/minuto e 2000/giorno.
    """

    def __init__(
        self,
        base_url: str = BASE_URL,
        session: requests.Session | None = None,
        retries: int = 3,
        backoff: float = 1.0,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.session = session or requests.Session()
        self.session.headers.setdefault("User-Agent", "harlocksp-updates-bot")
        self.retries = retries
        self.backoff = backoff
        self.sleep = sleep
        self._heroes_cache: list[dict[str, Any]] | None = None  # /heroes al massimo una volta per giro

    def recent_matches(self, player_id: int) -> list[dict[str, Any]]:
        """Ultime 20 partite del giocatore (una sola chiamata, usata a ogni giro)."""
        data = self._request("GET", f"/players/{player_id}/recentMatches")
        if not isinstance(data, list):
            raise OpenDotaError("recentMatches: risposta inattesa (non è una lista)")
        return [m for m in data if isinstance(m, dict) and isinstance(m.get("match_id"), int)]

    def player_matches(self, player_id: int, days: int) -> list[dict[str, Any]]:
        """Partite degli ultimi `days` giorni (una sola chiamata, anche per un mese)."""
        data = self._request("GET", f"/players/{player_id}/matches?date={int(days)}")
        if not isinstance(data, list):
            raise OpenDotaError("matches: risposta inattesa (non è una lista)")
        return [m for m in data if isinstance(m, dict) and isinstance(m.get("match_id"), int)]

    def heroes(self) -> dict[int, str]:
        """{hero_id: nome visualizzato}."""
        return {
            h["id"]: h.get("localized_name") or h.get("name") or f"Hero {h['id']}" for h in self._heroes()
        }

    def hero_keys(self) -> dict[str, str]:
        """{'npc_dota_hero_pudge': 'Pudge'}: i nomi interni usati da killed/killed_by."""
        return {h["name"]: h.get("localized_name") or h["name"] for h in self._heroes() if h.get("name")}

    def match(self, match_id: int) -> dict[str, Any]:
        """Dettaglio di una partita. I dati avanzati ci sono solo se il replay è stato analizzato."""
        data = self._request("GET", f"/matches/{int(match_id)}")
        if not isinstance(data, dict) or not isinstance(data.get("players"), list):
            raise OpenDotaError("matches: risposta inattesa")
        return data

    def request_parse(self, match_id: int) -> None:
        """Chiede a OpenDota di analizzare il replay (gratis; vale 10 chiamate nel limite)."""
        self._request("POST", f"/request/{int(match_id)}")

    def _heroes(self) -> list[dict[str, Any]]:
        if self._heroes_cache is None:
            data = self._request("GET", "/heroes")
            if not isinstance(data, list):
                raise OpenDotaError("heroes: risposta inattesa (non è una lista)")
            self._heroes_cache = [h for h in data if isinstance(h, dict) and isinstance(h.get("id"), int)]
        return self._heroes_cache

    def _request(self, method: str, path: str) -> Any:
        url = self.base_url + path
        last_error = "errore sconosciuto"
        for attempt in range(self.retries + 1):
            if attempt:
                delay = self.backoff * 2 ** (attempt - 1)
                log.info("OpenDota %s: nuovo tentativo tra %.0fs (%s)", path, delay, last_error)
                self.sleep(delay)
            try:
                resp = self.session.request(method, url, timeout=TIMEOUT)
            except requests.RequestException as exc:
                last_error = f"errore di rete: {type(exc).__name__}"
                continue
            if resp.status_code in RETRY_STATUS:
                last_error = f"HTTP {resp.status_code}"
                continue
            if not resp.ok:
                raise OpenDotaError(f"OpenDota {path}: HTTP {resp.status_code}")
            try:
                return resp.json()
            except ValueError as exc:
                raise OpenDotaError(f"OpenDota {path}: JSON non valido") from exc
        raise OpenDotaError(f"OpenDota {path}: {last_error} dopo {self.retries + 1} tentativi")
