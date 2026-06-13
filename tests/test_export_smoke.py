"""Smoke tests for `autopilot export` — must work with no API keys.

Regression guard: export reads local scan state only. It must NOT call
load_config() or require TINYFISH_API_KEY (the documented Step 6 smoke test).
"""
import json
import os

import pytest

from job_hunt import main


@pytest.fixture
def workdir(tmp_path, monkeypatch):
    """Run inside an empty working dir with no config.json and no env keys."""
    monkeypatch.chdir(tmp_path)
    for key in ("TINYFISH_API_KEY", "OPENROUTER_API_KEY", "LLM_PROVIDER"):
        monkeypatch.delenv(key, raising=False)
    return tmp_path


def test_export_without_keys_reports_no_scan(workdir, monkeypatch, capsys):
    """No keys, no config, no scan state → friendly 'no scan' message, not a key error."""
    monkeypatch.setattr("sys.argv", ["autopilot", "export"])

    with pytest.raises(SystemExit) as exc:
        main.main()

    out = capsys.readouterr().out
    assert "No scan found. Run: autopilot scan" in str(exc.value) + out
    assert "TINYFISH_API_KEY" not in str(exc.value)


def test_export_reads_last_scan(workdir, monkeypatch, capsys):
    """With a last_scan.json present, export writes a CSV — still no keys needed."""
    state = workdir / "state"
    state.mkdir()
    (state / "last_scan.json").write_text(
        json.dumps(
            [{"company": "Acme", "title": "ML Engineer", "url": "https://x/jobs/1", "score": 90}]
        )
    )
    monkeypatch.setattr("sys.argv", ["autopilot", "export"])

    main.main()

    out = capsys.readouterr().out
    assert "Exported 1 jobs" in out
    assert (workdir / "output").exists()


def test_parse_export_args():
    assert main._parse_export_args(["autopilot", "export"]) == (0, 0)
    assert main._parse_export_args(["autopilot", "export", "--min", "70"]) == (70, 0)
    assert main._parse_export_args(["autopilot", "export", "--days", "7", "--min", "60"]) == (60, 7)
