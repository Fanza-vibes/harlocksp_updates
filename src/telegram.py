"""Invio dei messaggi via Bot API di Telegram. Il token non compare mai in log/eccezioni."""

from __future__ import annotations

import logging
import time
from typing import Callable, Protocol

import requests

log = logging.getLogger(__name__)

API_URL = "https://api.telegram.org"
TIMEOUT = (10, 20)
MAX_RETRY_AFTER = 60  # oltre questa attesa rinunciamo e riproviamo al giro dopo


class TelegramError(Exception):
    """Invio fallito."""


class Sender(Protocol):
    def send_message(self, text: str) -> None: ...


class TelegramClient:
    def __init__(
        self,
        token: str,
        chat_id: str,
        session: requests.Session | None = None,
        retries: int = 3,
        sleep: Callable[[float], None] = time.sleep,
        api_url: str = API_URL,
    ) -> None:
        self._token = token
        self.chat_id = chat_id
        self.session = session or requests.Session()
        self.retries = retries
        self.sleep = sleep
        self.api_url = api_url

    def __repr__(self) -> str:
        return f"TelegramClient(chat_id={self.chat_id!r})"

    def send_message(self, text: str) -> None:
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        self._call("sendMessage", payload)

    def _call(self, method: str, payload: dict) -> dict:
        url = f"{self.api_url}/bot{self._token}/{method}"
        for attempt in range(self.retries + 1):
            try:
                resp = self.session.post(url, json=payload, timeout=TIMEOUT)
            except requests.RequestException as exc:
                # non includere exc: il messaggio contiene l'URL con il token
                if attempt < self.retries:
                    self.sleep(2 ** attempt)
                    continue
                raise TelegramError(f"{method}: errore di rete ({type(exc).__name__})") from None

            body = _json_or_empty(resp)
            if resp.status_code == 429 and attempt < self.retries:
                wait = int(body.get("parameters", {}).get("retry_after", 5))
                if wait <= MAX_RETRY_AFTER:
                    log.warning("Telegram rate limit: attendo %ss", wait)
                    self.sleep(wait)
                    continue
            if resp.status_code >= 500 and attempt < self.retries:
                self.sleep(2 ** attempt)
                continue
            if not resp.ok or not body.get("ok"):
                desc = body.get("description", "risposta non valida")
                raise TelegramError(f"{method}: HTTP {resp.status_code} – {desc}")
            return body
        raise TelegramError(f"{method}: tentativi esauriti")  # pragma: no cover


class DryRunSender:
    """Stampa i messaggi invece di inviarli."""

    def __init__(self, out: Callable[[str], None] = print) -> None:
        self.out = out
        self.count = 0

    def send_message(self, text: str) -> None:
        self.count += 1
        self.out(f"----- messaggio {self.count} (dry-run) -----\n{text}\n")


def _json_or_empty(resp: requests.Response) -> dict:
    try:
        data = resp.json()
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}
