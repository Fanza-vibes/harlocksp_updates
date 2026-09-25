import pytest

from src.config import ConfigError, load_config


@pytest.fixture
def cfg_file(tmp_path):
    p = tmp_path / "config.yaml"
    p.write_text("player_id: 295689331\ndisplay_name: HarlockSP\n")
    return p


def test_load_with_secrets(cfg_file):
    c = load_config(cfg_file, env={"TELEGRAM_TOKEN": "123:SECRET", "TELEGRAM_CHAT_ID": "@canale"})
    assert c.player_id == 295689331 and c.display_name == "HarlockSP"
    assert "SECRET" not in repr(c) and "SECRET" not in str(c)


def test_missing_secrets(cfg_file):
    with pytest.raises(ConfigError, match="TELEGRAM_TOKEN"):
        load_config(cfg_file, env={"TELEGRAM_CHAT_ID": "1"})


def test_dry_run_without_secrets(cfg_file):
    assert load_config(cfg_file, env={}, require_secrets=False).telegram_token is None


def test_invalid_player_id(tmp_path):
    p = tmp_path / "c.yaml"
    p.write_text("player_id: abc\n")
    with pytest.raises(ConfigError):
        load_config(p, env={}, require_secrets=False)


def test_missing_file(tmp_path):
    with pytest.raises(ConfigError):
        load_config(tmp_path / "x.yaml", env={}, require_secrets=False)
