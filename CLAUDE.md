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
  llm_utils.py  — LLM dispatch: OpenRouter (default), Anthropic API, or Claude Code CLI
  tools.py      — protocol-agnostic tool layer (wraps scanner/drafter/exporter)
  mcp_server.py — FastMCP server exposing scan_jobs, draft_application, export_jobs
  main.py       — CLI entry point (autopilot command)
```

## Rate limits (free tier)

### TinyFish (job discovery)

- **Search:** 5 requests/min — scanner auto-paces, sleeps between batches
- **URL fetch:** 25 requests/min — auto-paced, no action needed
- **Free tier:** completely free, no credit card, no daily cap
- **Scan duration:** 30–90 min for 130+ companies is normal — deliberate pacing, not a bug
- **"No new jobs found":** TinyFish found no postings matching the query for that company today — not an error

### OpenRouter (LLM scoring + drafting)

- **Free tier:** no credit card needed, but each model has a **daily quota** (resets midnight UTC)
- **Fallback chain** (tried in order, auto-skips on quota exhaustion):
  1. `meta-llama/llama-3.3-70b-instruct:free` — primary
  2. `nvidia/nemotron-3-super-120b-a12b:free` — fallback 1
  3. `google/gemma-4-31b-it:free` — fallback 2
  4. `qwen/qwen3-coder:free` — fallback 3
- **Calls per scan:** ~5–15 LLM calls (jobs scored in batches of 10) — one nightly scan stays within all four models' free limits
- **"All LLM models failed":** all 4 models hit their daily quota — wait for midnight UTC reset, or add a small OpenRouter credit ($1–5) to remove the cap
- **Multiple scans/day:** risks exhausting free-tier quota — run once nightly via cron
- Check live per-model limits: [openrouter.ai/models](https://openrouter.ai/models)

### Claude Code CLI (LLM backend — no API key needed)

- **Cost:** uses your Claude subscription (Pro/Team/Enterprise)
- **Setup:** `claude auth login` — no API key required
- **Activate:** set `"llm_provider": "claude_cli"` in `config.json` or `LLM_PROVIDER=claude_cli` in `.env`
- **Model:** set `"claude_cli_model": "sonnet"` (or `"opus"`, `"haiku"`) — empty = Claude's default
- **Rate limits:** governed by your subscription tier, not a daily free quota
- **Cron / MCP note:** subprocess inherits user session auth — verify with `claude --print "hi"` in the same shell context before scheduling

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
