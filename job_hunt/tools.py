"""
Protocol-agnostic tool layer.

These functions contain zero MCP/OpenAI/Google dependencies.
The MCP server, future OpenAI tool adapter, and future Gemini function adapter
all import from here — one place to update, all adapters benefit.
"""
from pathlib import Path

from job_hunt.main import load_config, load_companies, export_jobs
from job_hunt.scanner import run_scan
from job_hunt.drafter import draft_application


def tool_scan(config_path: str = "config.json", companies_path: str = "companies.json") -> str:
    """
    Discover new jobs, score them, send Telegram notification.
    Returns a summary string.
    """
    import json, os
    old_cwd = Path.cwd()
    project_root = Path(config_path).parent.resolve()
    os.chdir(project_root)
    try:
        config = load_config()
        companies = load_companies()
        run_scan(config, companies)
        last_scan = Path("state/last_scan.json")
        if last_scan.exists():
            jobs = json.loads(last_scan.read_text())
            scored = [j for j in jobs if j.get("score")]
            return f"Scan complete. {len(jobs)} jobs found, {len(scored)} scored."
        return "Scan complete. No results file written."
    finally:
        os.chdir(old_cwd)


def tool_draft(job_ref: str, config_path: str = "config.json") -> str:
    """
    Draft a tailored resume + cover letter for a job.
    job_ref: '#1', '1', or a full job URL.
    Returns path to output directory.
    """
    import os
    old_cwd = Path.cwd()
    project_root = Path(config_path).parent.resolve()
    os.chdir(project_root)
    try:
        config = load_config()
        draft_application(config, job_ref)
        return f"Application drafted in output/ directory."
    finally:
        os.chdir(old_cwd)


def tool_export(min_score: int = 0, days: int = 0, config_path: str = "config.json") -> str:
    """
    Export jobs to CSV.
    Returns path to exported CSV.
    """
    import os
    old_cwd = Path.cwd()
    project_root = Path(config_path).parent.resolve()
    os.chdir(project_root)
    try:
        export_jobs(min_score=min_score, days=days)
        return "Export complete. Check output/ directory."
    finally:
        os.chdir(old_cwd)
