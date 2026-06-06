#!/usr/bin/env python3
"""
Demo runner — uses fixture data, no real API calls.
Used by run_demo.sh for recording the asciinema demo GIF.
"""
import json
import sys
import time
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"


def _print_slow(text: str, delay: float = 0.02) -> None:
    for char in text:
        print(char, end="", flush=True)
        time.sleep(delay)
    print()


def cmd_scan() -> None:
    companies = json.loads((FIXTURES / "demo_companies.json").read_text())
    jobs = json.loads((FIXTURES / "demo_jobs.json").read_text())

    print("\n\033[1m🤖 autopilot-jobs — daily scan\033[0m\n")
    time.sleep(0.5)

    for company in companies:
        _print_slow(f"Scanning {company['name']}...", delay=0.01)
        time.sleep(0.4)
        matching = [j for j in jobs if j["company"] == company["name"]]
        if matching:
            print(f"  ✓ {len(matching)} new job(s) found")
        else:
            print(f"  — No new jobs")
        time.sleep(0.2)

    print()
    print("Scoring with AI...")
    time.sleep(1.2)
    print()

    scored = sorted(jobs, key=lambda x: x["score"], reverse=True)
    print("\033[1m📋 Top Matches\033[0m\n")
    for i, job in enumerate(scored, 1):
        time.sleep(0.15)
        print(
            f"  \033[1m#{i}\033[0m  {job['company']:15s}  "
            f"\033[32m{job['score']}%\033[0m  {job['extracted_title']}"
        )
        print(f"       📍 {job['location_remote']}")
        print(f"       🔧 {job['stack']}")
        print()

    print("📱 Telegram notification sent.\n")
    state_dir = Path("state")
    state_dir.mkdir(exist_ok=True)
    (state_dir / "last_scan.json").write_text(json.dumps(jobs, indent=2))
    print(f"✅ Scan complete. {len(jobs)} jobs evaluated.")


def cmd_draft() -> None:
    jobs = json.loads((FIXTURES / "demo_jobs.json").read_text())
    job = jobs[0]

    print(f"\n\033[1m📝 Drafting application: #{1} — {job['extracted_title']} @ {job['company']}\033[0m\n")
    time.sleep(0.5)

    _print_slow(f"Fetching JD: {job['url']}", delay=0.008)
    time.sleep(0.8)
    print("  ✓ Job description fetched (2,847 words)\n")

    print("Tailoring resume...")
    for i in range(5):
        time.sleep(0.3)
        print(f"  {'█' * (i + 1)}{'░' * (4 - i)}  {(i + 1) * 20}%", end="\r")
    print(f"  █████  100%")
    time.sleep(0.2)
    print("  ✓ Saved: output/stripe-2025-06-06/resume_stripe.md\n")

    print("Drafting cover letter...")
    time.sleep(1.0)
    print("  ✓ Saved: output/stripe-2025-06-06/cover_letter_stripe.md\n")

    print("Extracting application info...")
    time.sleep(0.6)
    print("  ✓ Saved: output/stripe-2025-06-06/application_info.txt\n")

    print("\033[1mAll files in: output/stripe-2025-06-06/\033[0m")
    print("Review, edit, then submit manually.")


def cmd_export() -> None:
    jobs = json.loads((FIXTURES / "demo_jobs.json").read_text())
    scored = [j for j in jobs if j.get("score", 0) >= 70]

    print(f"\n\033[1m📊 Exporting {len(scored)} jobs (score ≥ 70)\033[0m\n")
    time.sleep(0.4)

    out = Path("output")
    out.mkdir(exist_ok=True)
    out_file = out / "demo_jobs_export.csv"

    import csv
    with out_file.open("w", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["Company", "Role", "Score (%)", "Location", "Stack"]
        )
        writer.writeheader()
        for j in scored:
            writer.writerow({
                "Company": j["company"],
                "Role": j["extracted_title"],
                "Score (%)": j["score"],
                "Location": j["location_remote"],
                "Stack": j["stack"],
            })

    print(f"✅ Exported → {out_file}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "scan"
    if cmd == "scan":
        cmd_scan()
    elif cmd == "draft":
        cmd_draft()
    elif cmd == "export":
        cmd_export()
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
