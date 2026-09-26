import pytest
import requests
import responses

from src.telegram import DryRunSender, TelegramClient, TelegramError

TOKEN = "123456:SUPERSECRET"
URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"


def client(sleeps=None):
    return TelegramClient(TOKEN, "@canale", sleep=(sleeps.append if sleeps is not None else lambda s: None))


@responses.activate
def test_send_ok():
    responses.post(URL, json={"ok": True, "result": {}})
    client().send_message("<b>ciao</b>")
    body = responses.calls[0].request.body
    assert b'"parse_mode": "HTML"' in body and b"@canale" in body


@responses.activate
def test_rate_limit_retry_after():
    sleeps = []
    responses.post(URL, status=429, json={"ok": False, "parameters": {"retry_after": 7}})
    responses.post(URL, json={"ok": True})
    client(sleeps).send_message("x")
    assert sleeps == [7]


@responses.activate
def test_error_does_not_leak_token():
    responses.post(URL, status=400, json={"ok": False, "description": "Bad Request: chat not found"})
    with pytest.raises(TelegramError) as exc:
        client().send_message("x")
    assert "chat not found" in str(exc.value)
    assert "SUPERSECRET" not in str(exc.value)


@responses.activate
def test_network_error_does_not_leak_token():
    responses.post(URL, body=requests.ConnectionError(f"failed {URL}"))
    with pytest.raises(TelegramError) as exc:
        client().send_message("x")
    assert "SUPERSECRET" not in str(exc.value)
    assert exc.value.__cause__ is None and exc.value.__suppress_context__
    assert "SUPERSECRET" not in repr(client())


def test_dry_run_sender():
    out = []
    s = DryRunSender(out=out.append)
    s.send_message("ciao")
    assert s.count == 1 and "ciao" in out[0]


@responses.activate
def test_send_to_specific_chat():
    responses.post(URL, json={"ok": True})
    client().send_message("x", chat_id=42)
    assert b'"chat_id": 42' in responses.calls[0].request.body


@responses.activate
def test_get_updates():
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    responses.post(url, json={"ok": True, "result": [{"update_id": 5}, "junk"]})
    assert client().get_updates(offset=5) == [{"update_id": 5}]
    body = responses.calls[0].request.body
    assert b'"offset": 5' in body and b'"timeout": 0' in body and b'"allowed_updates": ["message"]' in body


@responses.activate
def test_set_my_commands():
    url = f"https://api.telegram.org/bot{TOKEN}/setMyCommands"
    responses.post(url, json={"ok": True, "result": True})
    client().set_my_commands([("ultima", "Ultima partita")])
    assert b'"command": "ultima"' in responses.calls[0].request.body


@responses.activate
def test_send_returns_message_id_and_replies():
    responses.post(URL, json={"ok": True, "result": {"message_id": 77}})
    assert client().send_message("x", reply_to=5) == 77
    body = responses.calls[0].request.body
    assert b'"reply_parameters": {"message_id": 5, "allow_sending_without_reply": true}' in body
    assert b'"link_preview_options": {"is_disabled": true}' in body


@responses.activate
@pytest.mark.parametrize(
    ("name", "method", "field"), [("gg.gif", "sendAnimation", "animation"), ("gg.PNG", "sendPhoto", "photo")]
)
def test_send_media_uploads_file(tmp_path, name, method, field):
    url = f"https://api.telegram.org/bot{TOKEN}/{method}"
    responses.post(url, json={"ok": True, "result": {"message_id": 88}})
    path = tmp_path / name
    path.write_bytes(b"GIF89a")
    assert client().send_media(path, "<b>didascalia</b>", reply_to=5) == 88
    body = responses.calls[0].request.body
    assert f'name="{field}"; filename="{name}"'.encode() in body
    assert b"<b>didascalia</b>" in body and b'name="parse_mode"' in body
    assert b'"message_id": 5' in body


@responses.activate
def test_send_media_retry_rereads_file(tmp_path):
    url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
    responses.post(url, status=502)
    responses.post(url, json={"ok": True, "result": {"message_id": 1}})
    path = tmp_path / "a.png"
    path.write_bytes(b"PNGDATA")
    client().send_media(path, "x")
    assert b"PNGDATA" in responses.calls[1].request.body  # il file viene rimandato per intero


@responses.activate
def test_send_media_error_does_not_leak_token(tmp_path):
    url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
    responses.post(url, status=400, json={"ok": False, "description": "Bad Request: wrong file"})
    path = tmp_path / "a.png"
    path.write_bytes(b"x")
    with pytest.raises(TelegramError) as exc:
        client().send_media(path, "x")
    assert "SUPERSECRET" not in str(exc.value)
