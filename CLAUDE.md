# autopilot-jobhunt

AI job agent: scans 130+ company careers pages nightly, scores every role against your resume with an LLM (0–100), sends top matches via Telegram, and drafts tailored cover letters + resume bullets on demand.

## Key commands

```bash
autopilot scan              # discover jobs, score with LLM, send Telegram notification
autopilot draft 1           # draft cover letter + resume for job #1 from last scan
autopilot draft https://... # draft for a specific job URL
autopilot export            # export last scan to CSV
autopilot export --min 70   # export only jobs with score >= 70
autopilot export --days 7   # export jobs from the past 7 days

python -m job_hunt.mcp_server  # start the MCP server (Claude Code / Claude Desktop)
```

## Config files

| File | Controls | Gitignored? |
|---|---|---|
| `config.json` | Candidate profile, LLM settings, Telegram | Yes — copy from `config.example.json` |
| `.env` | API keys (TinyFish, OpenRouter, Telegram) | Yes — copy from `.env.example` |
| `companies.json` | List of companies to scan | No — committed, edit freely |
| `resume/YOUR_RESUME.md` | Your resume text (Markdown) | Yes — template committed |

## Package structure

```
job_hunt/
  scanner.py    — TinyFish API job discovery + LLM scoring pipeline
  drafter.py    — cover letter + tailored resume bullet generation
  notifier.py   — Telegram notification sender (optional, graceful if unconfigured)
  llm_utils.py  — OpenRouter wrapper with 4-model free-tier fallback chain
  tools.py      — protocol-agnostic tool layer (wraps scanner/drafter/exporter)
  mcp_server.py — FastMCP server exposing scan_jobs, draft_application, export_jobs
  main.py       — CLI entry point (autopilot command)
```

## Rate limits (free tier)

- **TinyFish:** 5 searches/min, 25 URL fetches/min — scanner auto-paces, no action needed
- **OpenRouter:** 4-model fallback chain handles per-model daily quotas automatically
- **Scan time:** 30–90 min for 130+ companies — normal, run nightly via cron

## MCP registration (Claude Code)

See [SETUP.md §7](SETUP.md#step-7--register-with-claude-code-mcp) for the full setup.

Quick reference:
```bash
claude mcp add autopilot-jobhunt \
  --env TINYFISH_API_KEY=your_key \
  --env OPENROUTER_API_KEY=your_key \
  -- python -m job_hunt.mcp_server
# Then add "cwd": "/path/to/autopilot-jobhunt" in ~/.claude.json
```

MCP tools exposed: `scan_jobs`, `draft_application(job_ref)`, `export_jobs(min_score, days)`

## State files (gitignored)

- `state/last_scan.json` — job results from the most recent scan
- `output/` — drafted cover letters and resume files
- `scan.log` — scan activity log (when using cron)
