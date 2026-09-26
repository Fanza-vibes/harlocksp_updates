"""Immagini e GIF da allegare ai messaggi del canale, scelte dalle cartelle in `media/`.

Ogni situazione ha una cartella (es. `media/vittoria/`); se contiene più file se ne sceglie uno a
caso. Le situazioni sono elencate dalla più specifica alla più generica: si usa la prima cartella
che contiene almeno un file (es. alla terza sconfitta di fila `serie_sconfitte/`, altrimenti
`sconfitta/`). Nessun file = messaggio di solo testo. Un errore nell'invio del file non fa mai
perdere il messaggio: si ripiega sul solo testo.
"""

from __future__ import annotations

import logging
import random
from pathlib import Path

from .formatter import CURSE_BROKEN_MIN, STREAK_MIN
from .telegram import Sender, TelegramError

log = logging.getLogger(__name__)

MEDIA_DIR = Path("media")
PHOTO_EXT = {".jpg", ".jpeg", ".png", ".webp"}
ANIMATION_EXT = {".gif", ".mp4"}
CAPTION_LIMIT = 1024  # limite di Telegram per la didascalia di un file

VICTORY = "vittoria"
DEFEAT = "sconfitta"
WIN_STREAK = "serie_vittorie"
LOSS_STREAK = "serie_sconfitte"
CURSE_BROKEN = "maledizione_spezzata"
SPECIAL_PLAY = "giocate_speciali"
DAILY_SUMMARY = "riepilogo"
ALL_KINDS = (VICTORY, DEFEAT, WIN_STREAK, LOSS_STREAK, CURSE_BROKEN, SPECIAL_PLAY, DAILY_SUMMARY)


def match_kinds(win: bool, streak: int, previous_streak: int = 0) -> list[str]:
    """Cartelle da provare per la scheda di una partita, dalla più specifica alla più generica."""
    if win:
        if streak == 1 and previous_streak <= -CURSE_BROKEN_MIN:
            return [CURSE_BROKEN, VICTORY]
        if streak >= STREAK_MIN:
            return [WIN_STREAK, VICTORY]
        return [VICTORY]
    if -streak >= STREAK_MIN:
        return [LOSS_STREAK, DEFEAT]
    return [DEFEAT]


def pick(kinds: list[str], root: Path | None = None, rng: random.Random | None = None) -> Path | None:
    """Un file a caso dalla prima cartella non vuota tra `kinds`, oppure None.

    `root` di default è MEDIA_DIR, letta al momento della chiamata (i test la sostituiscono).
    """
    base = root if root is not None else MEDIA_DIR
    for kind in kinds:
        folder = base / kind
        if not folder.is_dir():
            continue
        files = sorted(
            p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in PHOTO_EXT | ANIMATION_EXT
        )
        if files:
            return (rng or random).choice(files)
    return None


def is_animation(path: Path) -> bool:
    """GIF e video si inviano come animazione, il resto come foto."""
    return path.suffix.lower() in ANIMATION_EXT


def send_with_media(
    sender: Sender,
    text: str,
    kinds: list[str],
    root: Path | None = None,
    reply_to: int | None = None,
    rng: random.Random | None = None,
) -> int | None:
    """Invia `text` al canale con un'immagine/GIF adatta, se c'è; restituisce il message_id.

    Se non c'è un file, se il testo supera il limite della didascalia o se l'invio del file fallisce,
    invia il solo testo. Un errore nell'invio del testo viene propagato come `TelegramError`.
    """
    path = pick(kinds, root, rng)
    if path is not None and len(text) <= CAPTION_LIMIT:
        try:
            return sender.send_media(path, text, reply_to=reply_to)
        except (TelegramError, OSError) as exc:
            log.warning("Invio di %s non riuscito (%s): mando solo il testo", path.name, exc)
    return sender.send_message(text, reply_to=reply_to)
