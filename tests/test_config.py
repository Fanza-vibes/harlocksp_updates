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


def test_defaults_timezone_and_hour(cfg_file):
    c = load_config(cfg_file, env={}, require_secrets=False)
    assert c.timezone == "Europe/Rome" and c.daily_summary_hour == 23


@pytest.mark.parametrize(
    "extra", ["timezone: Marte/Base\n", "daily_summary_hour: 24\n", "daily_summary_hour: sera\n"]
)
def test_invalid_timezone_or_hour(cfg_file, extra):
    cfg_file.write_text(cfg_file.read_text() + extra)
    with pytest.raises(ConfigError):
        load_config(cfg_file, env={}, require_secrets=False)


def test_summary_can_be_disabled(cfg_file):
    cfg_file.write_text(cfg_file.read_text() + "daily_summary_hour: null\n")
    assert load_config(cfg_file, env={}, require_secrets=False).daily_summary_hour is None
