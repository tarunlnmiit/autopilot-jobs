#!/usr/bin/env python3
"""
Usage:
  autopilot init              — set up working directory (first-time pip install setup)
  autopilot scan              — run daily job scan
  autopilot draft #1          — draft application for job #1 from last scan
  autopilot draft https://... — draft application for a specific URL
  autopilot export            — export last scan to CSV (output/jobs_YYYY-MM-DD.csv)
  autopilot export --min 60   — export only jobs with score >= 60
  autopilot export --days 7   — export jobs from last 7 days (requires scan history)
  autopilot export --days 7 --min 60  — combine filters
"""
import csv
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

_PLACEHOLDERS = {
    "YOUR_TINYFISH_API_KEY", "your_tinyfish_api_key_here",
    "YOUR_OPENROUTER_API_KEY", "your_openrouter_api_key_here",
    "YOUR_ANTHROPIC_API_KEY", "your_anthropic_api_key_here",
}


def _is_placeholder(val: str) -> bool:
    return val in _PLACEHOLDERS or val.startswith("YOUR_") or val.endswith("_HERE") or val.endswith("_here")


def load_config() -> dict:
    load_dotenv(dotenv_path=Path(".env"), override=True)
    p = Path("config.json")
    if not p.exists():
        sys.exit("config.json not found.\nRun 'autopilot init' to set up your working directory.")

    config = json.loads(p.read_text())

    env_mapping = {
        "TINYFISH_API_KEY": "tinyfish_api_key",
        "LLM_PROVIDER": "llm_provider",
        "OPENROUTER_API_KEY": "openrouter_api_key",
        "OPENROUTER_MODEL": "openrouter_model",
        "OPENROUTER_FALLBACK_MODELS": "openrouter_fallback_models",
        "CLAUDE_CLI_MODEL": "claude_cli_model",
    }

    for env_key, config_key in env_mapping.items():
        val = os.getenv(env_key)
        if val:
            if env_key == "OPENROUTER_FALLBACK_MODELS":
                config[config_key] = [m.strip() for m in val.split(",")]
            else:
                config[config_key] = val

    tinyfish_key = config.get("tinyfish_api_key", "")
    if not tinyfish_key or _is_placeholder(tinyfish_key):
        sys.exit(
            "TINYFISH_API_KEY not set.\n"
            "Add it to your .env file: TINYFISH_API_KEY=sk-tinyfish-...\n"
            "Get a key at https://agent.tinyfish.ai"
        )

    tg_token = os.getenv("TELEGRAM_TOKEN")
    tg_chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if tg_token or tg_chat_id:
        if "telegram" not in config:
            config["telegram"] = {}
        if tg_token:
            config["telegram"]["token"] = tg_token
        if tg_chat_id:
            config["telegram"]["chat_id"] = tg_chat_id

    cand_name = os.getenv("CANDIDATE_NAME")
    cand_resume = os.getenv("RESUME_PATH")
    cand_min_score = os.getenv("MIN_SCORE")
    cand_top_n = os.getenv("TOP_N")
    if cand_name or cand_resume or cand_min_score or cand_top_n:
        if "candidate" not in config:
            config["candidate"] = {}
        if cand_name:
            config["candidate"]["name"] = cand_name
        if cand_resume:
            config["candidate"]["resume_path"] = cand_resume
        if cand_min_score:
            config["candidate"]["min_score"] = int(cand_min_score)
        if cand_top_n:
            config["candidate"]["top_n"] = int(cand_top_n)

    return config


def load_companies() -> list:
    p = Path("companies.json")
    if not p.exists():
        sys.exit("companies.json not found.\nRun 'autopilot init' to set up your working directory.")
    return json.loads(p.read_text())


def init_project() -> None:
    import importlib.resources as pkg_resources

    cwd = Path.cwd()
    data_pkg = pkg_resources.files("job_hunt.data")

    def _copy(src_name: str, dest: Path, label: str) -> None:
        if dest.exists():
            print(f"  {dest.name} already exists, skipping")
        else:
            dest.write_text(data_pkg.joinpath(src_name).read_text(encoding="utf-8"), encoding="utf-8")
            print(f"✓ {label}")

    _copy("companies.json", cwd / "companies.json", "companies.json created (130+ companies pre-loaded)")
    _copy("config.example.json", cwd / "config.json", "config.json created — fill in your API keys and profile")
    _copy("env_example", cwd / ".env", ".env created — fill in your API keys")

    resume_dir = cwd / "resume"
    resume_dir.mkdir(exist_ok=True)
    _copy("resume_template.md", resume_dir / "YOUR_RESUME.md", "resume/YOUR_RESUME.md created — replace with your resume")

    (cwd / "state").mkdir(exist_ok=True)
    (cwd / "output").mkdir(exist_ok=True)

    print("\nNext:")
    print("  1. Edit config.json — set your name, profile, and API keys")
    print("  2. Replace resume/YOUR_RESUME.md with your actual resume")
    print("  3. Run: autopilot scan")


LAST_SCAN_FILE = Path("state/last_scan.json")
JOB_HISTORY_FILE = Path("state/job_history.json")

EXPORT_FIELDS = [
    "Company", "Role", "Location", "Application URL",
    "Score (%)", "Stack", "Region", "Reason", "Worth Applying", "Scan Date",
]


def _job_to_row(j: dict) -> dict:
    worth = j.get("worth_applying")
    return {
        "Company": j.get("company", ""),
        "Role": j.get("extracted_title") or j.get("title", ""),
        "Location": j.get("location_remote") or j.get("location", ""),
        "Application URL": j.get("url", ""),
        "Score (%)": j.get("score", ""),
        "Stack": j.get("stack", ""),
        "Region": j.get("region", ""),
        "Reason": j.get("reason", ""),
        "Worth Applying": "Yes" if worth else ("No" if worth is False else ""),
        "Scan Date": j.get("scan_date", ""),
    }


def export_jobs(min_score: int = 0, days: int = 0) -> None:
    if days > 0:
        if not JOB_HISTORY_FILE.exists():
            sys.exit(
                "No history yet. Run 'autopilot scan' at least once after this update."
            )
        all_jobs: list[dict] = json.loads(JOB_HISTORY_FILE.read_text())
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
        jobs = [j for j in all_jobs if j.get("scan_date", "9999") >= cutoff]
        source_label = f"last {days} days"
    else:
        if not LAST_SCAN_FILE.exists():
            sys.exit("No scan found. Run: autopilot scan")
        jobs = json.loads(LAST_SCAN_FILE.read_text())
        source_label = "last scan"

    filtered = [j for j in jobs if j.get("score", 0) >= min_score]

    if not filtered:
        print(f"No jobs with score >= {min_score} in {source_label}")
        return

    date_str = datetime.now().strftime("%Y-%m-%d")
    suffix = f"_last{days}d" if days else ""
    out_path = Path("output") / f"jobs_{date_str}{suffix}.csv"
    out_path.parent.mkdir(exist_ok=True)

    with out_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=EXPORT_FIELDS)
        writer.writeheader()
        for j in filtered:
            writer.writerow(_job_to_row(j))

    print(f"Exported {len(filtered)} jobs ({source_label}) → {out_path}")
    if min_score:
        print(f"Filter: score >= {min_score} (skipped {len(jobs) - len(filtered)})")


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0)

    cmd = sys.argv[1].lower()

    if cmd == "init":
        init_project()
        return

    config = load_config()

    if cmd == "scan":
        from job_hunt.scanner import run_scan
        run_scan(config, load_companies())

    elif cmd == "draft":
        if len(sys.argv) < 3:
            sys.exit("Usage: autopilot draft #N  or  autopilot draft URL")
        from job_hunt.drafter import draft_application
        draft_application(config, sys.argv[2])

    elif cmd == "export":
        min_score = 0
        days = 0
        if "--min" in sys.argv:
            idx = sys.argv.index("--min")
            try:
                min_score = int(sys.argv[idx + 1])
            except (IndexError, ValueError):
                sys.exit("--min requires an integer, e.g. --min 60")
        if "--days" in sys.argv:
            idx = sys.argv.index("--days")
            try:
                days = int(sys.argv[idx + 1])
            except (IndexError, ValueError):
                sys.exit("--days requires an integer, e.g. --days 7")
        export_jobs(min_score=min_score, days=days)

    else:
        sys.exit(f"Unknown command: {cmd}\nUse: scan | draft | export")


if __name__ == "__main__":
    main()
