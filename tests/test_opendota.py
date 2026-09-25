import pytest
import requests
import responses

from src.opendota import BASE_URL, OpenDotaClient, OpenDotaError

URL = f"{BASE_URL}/players/1/recentMatches"


def client(sleeps=None):
    return OpenDotaClient(sleep=(sleeps.append if sleeps is not None else lambda s: None))


@responses.activate
def test_recent_matches_ok():
    responses.get(URL, json=[{"match_id": 5}, {"foo": 1}])
    assert client().recent_matches(1) == [{"match_id": 5}]


@responses.activate
def test_retry_then_success():
    sleeps = []
    responses.get(URL, status=502)
    responses.get(URL, status=429)
    responses.get(URL, json=[])
    assert client(sleeps).recent_matches(1) == []
    assert sleeps == [1.0, 2.0]


@responses.activate
def test_network_error_exhausts_retries():
    responses.get(URL, body=requests.ConnectionError("boom"))
    with pytest.raises(OpenDotaError, match="errore di rete"):
        client().recent_matches(1)
    assert len(responses.calls) == 4


@responses.activate
def test_404_no_retry():
    responses.get(URL, status=404)
    with pytest.raises(OpenDotaError, match="404"):
        client().recent_matches(1)
    assert len(responses.calls) == 1


@responses.activate
def test_bad_json():
    responses.get(URL, body="<html>")
    with pytest.raises(OpenDotaError):
        client().recent_matches(1)


@responses.activate
def test_heroes():
    responses.get(f"{BASE_URL}/heroes", json=[{"id": 1, "localized_name": "Anti-Mage"}, {"id": 2}])
    assert client().heroes() == {1: "Anti-Mage", 2: "Hero 2"}


@responses.activate
def test_player_matches():
    responses.get(f"{BASE_URL}/players/1/matches?date=7", json=[{"match_id": 1}, {"x": 2}])
    assert client().player_matches(1, 7) == [{"match_id": 1}]
    assert responses.calls[0].request.url.endswith("/players/1/matches?date=7")
