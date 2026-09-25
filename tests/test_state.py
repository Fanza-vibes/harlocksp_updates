import json

from src.state import State, load_state, save_state


def test_missing_file(tmp_path):
    assert load_state(tmp_path / "nope.json") == State()


def test_empty_file(tmp_path):
    p = tmp_path / "s.json"
    p.write_text("")
    assert load_state(p) == State()


def test_corrupted_file(tmp_path):
    p = tmp_path / "s.json"
    p.write_text("{not json")
    assert load_state(p) == State()


def test_wrong_types(tmp_path):
    p = tmp_path / "s.json"
    p.write_text(json.dumps({"last_match_id": "abc", "heroes": ["x"]}))
    assert load_state(p) == State()
    p.write_text("[1, 2]")
    assert load_state(p) == State()
    p.write_text(json.dumps({"last_match_id": True}))
    assert load_state(p).last_match_id is None


def test_roundtrip(tmp_path):
    p = tmp_path / "s.json"
    s = State(last_match_id=42, heroes={2: "Axe", 1: "Anti-Mage"}, heroes_updated_at="2026-01-01T00:00:00Z")
    save_state(p, s)
    assert load_state(p) == s
    data = json.loads(p.read_text())
    assert list(data["heroes"]) == ["1", "2"]
    assert list(tmp_path.iterdir()) == [p]  # nessun file temporaneo rimasto


def test_save_is_deterministic(tmp_path):
    p = tmp_path / "s.json"
    save_state(p, State(last_match_id=1))
    first = p.read_text()
    save_state(p, State(last_match_id=1))
    assert p.read_text() == first


def test_new_fields_roundtrip_and_validation(tmp_path):
    p = tmp_path / "s.json"
    s = State(last_match_id=1, telegram_offset=500, last_summary_date="2026-09-25", commands_version=1)
    save_state(p, s)
    assert load_state(p) == s
    p.write_text(json.dumps({"telegram_offset": -3, "last_summary_date": "ieri", "commands_version": "1"}))
    assert load_state(p) == State()
