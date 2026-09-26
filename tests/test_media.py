import random

import pytest

from src.media import CAPTION_LIMIT, match_kinds, pick, send_with_media
from src.telegram import TelegramError


def add(root, kind, *names):
    folder = root / kind
    folder.mkdir(parents=True, exist_ok=True)
    for name in names:
        (folder / name).write_bytes(b"x")
    return folder


@pytest.mark.parametrize(
    ("win", "streak", "previous", "expected"),
    [
        (True, 1, 0, ["vittoria"]),
        (True, 3, 2, ["serie_vittorie", "vittoria"]),
        (True, 1, -3, ["maledizione_spezzata", "vittoria"]),
        (True, 1, -2, ["vittoria"]),
        (False, -1, 2, ["sconfitta"]),
        (False, -2, -1, ["sconfitta"]),
        (False, -3, -2, ["serie_sconfitte", "sconfitta"]),
    ],
)
def test_match_kinds(win, streak, previous, expected):
    assert match_kinds(win, streak, previous) == expected


def test_pick_first_non_empty_folder(tmp_path):
    add(tmp_path, "serie_sconfitte")  # vuota
    add(tmp_path, "sconfitta", "triste.gif")
    assert pick(["serie_sconfitte", "sconfitta"], tmp_path).name == "triste.gif"
    add(tmp_path, "serie_sconfitte", "disastro.mp4")
    assert pick(["serie_sconfitte", "sconfitta"], tmp_path).name == "disastro.mp4"


def test_pick_ignores_other_files_and_missing_folders(tmp_path):
    add(tmp_path, "vittoria", "LEGGIMI.md", ".gitkeep", "nota.txt")
    assert pick(["vittoria", "non_esiste"], tmp_path) is None


def test_pick_is_random_among_files(tmp_path):
    add(tmp_path, "vittoria", "a.png", "b.JPG", "c.webp")
    chosen = {pick(["vittoria"], tmp_path, random.Random(seed)).name for seed in range(30)}
    assert chosen == {"a.png", "b.JPG", "c.webp"}


def test_pick_uses_media_dir_by_default(empty_media_dir):
    add(empty_media_dir, "riepilogo", "sera.png")
    assert pick(["riepilogo"]).name == "sera.png"


class FakeSender:
    def __init__(self, media_error=None):
        self.media_error = media_error
        self.calls = []

    def send_message(self, text, chat_id=None, reply_to=None):
        self.calls.append(("text", text, reply_to))
        return 1

    def send_media(self, path, caption, reply_to=None):
        if self.media_error:
            raise self.media_error
        self.calls.append(("media", path.name, caption, reply_to))
        return 2


def test_send_without_file_is_text_only(tmp_path):
    sender = FakeSender()
    assert send_with_media(sender, "ciao", ["vittoria"], tmp_path) == 1
    assert sender.calls == [("text", "ciao", None)]


def test_send_with_file_uses_caption(tmp_path):
    add(tmp_path, "vittoria", "gg.gif")
    sender = FakeSender()
    assert send_with_media(sender, "ciao", ["vittoria"], tmp_path, reply_to=7) == 2
    assert sender.calls == [("media", "gg.gif", "ciao", 7)]


@pytest.mark.parametrize("error", [TelegramError("file troppo grande"), OSError("illeggibile")])
def test_media_failure_falls_back_to_text(tmp_path, error):
    add(tmp_path, "vittoria", "gg.gif")
    sender = FakeSender(media_error=error)
    assert send_with_media(sender, "ciao", ["vittoria"], tmp_path) == 1
    assert sender.calls == [("text", "ciao", None)]


def test_text_too_long_for_caption_is_sent_as_text(tmp_path):
    add(tmp_path, "riepilogo", "sera.png")
    sender = FakeSender()
    send_with_media(sender, "x" * (CAPTION_LIMIT + 1), ["riepilogo"], tmp_path)
    assert sender.calls[0][0] == "text"
