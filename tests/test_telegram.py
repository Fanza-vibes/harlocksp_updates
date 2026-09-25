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
