"""config.json + .env composition.

Rule: an env var overrides config.json only when it's set AND not a placeholder.
The default `.env` template written by `autopilot init` is full of `your_..._here`
placeholders — those must never clobber real values in config.json.
"""
import json

import pytest

from job_hunt import main


@pytest.fixture
def workdir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # Start from a clean env so the host shell's keys don't leak into assertions.
    for k in ("TINYFISH_API_KEY", "OPENROUTER_API_KEY", "ANTHROPIC_API_KEY",
              "ANTHROPIC_MODEL", "TELEGRAM_TOKEN", "TELEGRAM_CHAT_ID"):
        monkeypatch.delenv(k, raising=False)
    return tmp_path


def _write_config(workdir, **overrides):
    cfg = {"tinyfish_api_key": "sk-real-config-key"}
    cfg.update(overrides)
    (workdir / "config.json").write_text(json.dumps(cfg))


def test_placeholder_env_does_not_override_real_config(workdir, monkeypatch):
    _write_config(workdir, openrouter_api_key="sk-or-real-config")
    monkeypatch.setenv("OPENROUTER_API_KEY", "your_openrouter_api_key_here")

    cfg = main.load_config()

    assert cfg["openrouter_api_key"] == "sk-or-real-config"


def test_real_env_overrides_config(workdir, monkeypatch):
    _write_config(workdir, openrouter_api_key="sk-or-from-config")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-from-env")

    cfg = main.load_config()

    assert cfg["openrouter_api_key"] == "sk-or-from-env"


def test_placeholder_tinyfish_env_does_not_break_real_config_key(workdir, monkeypatch):
    """The exact 'config.json and .env don't compose' bug: real key in config,
    placeholder in .env — must not exit with 'TINYFISH_API_KEY not set'."""
    _write_config(workdir)  # tinyfish_api_key = sk-real-config-key
    monkeypatch.setenv("TINYFISH_API_KEY", "YOUR_TINYFISH_API_KEY")

    cfg = main.load_config()  # must not SystemExit

    assert cfg["tinyfish_api_key"] == "sk-real-config-key"


def test_anthropic_key_bridged_from_env(workdir, monkeypatch):
    _write_config(workdir)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-real")

    cfg = main.load_config()

    assert cfg["anthropic_api_key"] == "sk-ant-real"
