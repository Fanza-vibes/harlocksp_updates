"""Client minimale per l'API pubblica di OpenDota (senza chiave)."""

from __future__ import annotations

import logging
import time
from typing import Any, Callable

import requests

log = logging.getLogger(__name__)

BASE_URL = "https://api.opendota.com/api"
TIMEOUT = (10, 20)  # connessione, lettura
RETRY_STATUS = {429, 500, 502, 503, 504}


class OpenDotaError(Exception):
    """L'API non ha risposto correttamente neanche dopo i retry."""


class OpenDotaClient:
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

    def recent_matches(self, player_id: int) -> list[dict[str, Any]]:
        data = self._get(f"/players/{player_id}/recentMatches")
        if not isinstance(data, list):
            raise OpenDotaError("recentMatches: risposta inattesa (non è una lista)")
        return [m for m in data if isinstance(m, dict) and isinstance(m.get("match_id"), int)]

    def heroes(self) -> dict[int, str]:
        data = self._get("/heroes")
        if not isinstance(data, list):
            raise OpenDotaError("heroes: risposta inattesa (non è una lista)")
        return {
            h["id"]: h.get("localized_name") or h.get("name") or f"Hero {h['id']}"
            for h in data
            if isinstance(h, dict) and isinstance(h.get("id"), int)
        }

    def _get(self, path: str) -> Any:
        url = self.base_url + path
        last_error = "errore sconosciuto"
        for attempt in range(self.retries + 1):
            if attempt:
                delay = self.backoff * 2 ** (attempt - 1)
                log.info("OpenDota %s: nuovo tentativo tra %.0fs (%s)", path, delay, last_error)
                self.sleep(delay)
            try:
                resp = self.session.get(url, timeout=TIMEOUT)
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
