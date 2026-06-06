# autopilot-jobs

**Your AI job agent. Finds, scores, and drafts applications — while you sleep.**

> Scans 130+ company careers pages nightly → scores every role against your resume with an LLM → sends you the top matches on Telegram → drafts a tailored resume + cover letter on demand.

<!-- Add demo GIF here after recording: ![Demo](demo/demo.gif) -->

[![PyPI version](https://img.shields.io/pypi/v/autopilot-jobs)](https://pypi.org/project/autopilot-jobs/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![GitHub Stars](https://img.shields.io/github/stars/tarunlnmiit/autopilot-jobs?style=social)](https://github.com/tarunlnmiit/autopilot-jobs/stargazers)

---

## What it does

```
Every night at 2:30 AM:
  ┌─────────────────────────────────────────────────────────┐
  │  Scans careers pages  →  Scores with LLM  →  Notifies  │
  │       (130+ cos)           (0–100 fit)       (Telegram) │
  └─────────────────────────────────────────────────────────┘

On demand:
  autopilot draft 1  →  tailored resume + cover letter in 60s
```

**The scoring prompt uses your actual resume** — not keywords. The LLM reads your full work history and the job description, then explains in one sentence why you fit or don't. No more guessing.

---

## Quick start

### 1. Install

```bash
pip install autopilot-jobs
# or clone and install locally:
git clone https://github.com/tarunlnmiit/autopilot-jobs.git
cd autopilot-jobs
pip install -e .
```

### 2. Get API keys

| Service | Cost | Link |
|---|---|---|
| **TinyFish** | Free tier available | [agent.tinyfish.ai](https://agent.tinyfish.ai) |
| **OpenRouter** | Free tier (multiple models) | [openrouter.ai](https://openrouter.ai) |
| **Telegram bot** | Free | [@BotFather](https://t.me/BotFather) on Telegram |

### 3. Configure

```bash
cp .env.example .env
# Edit .env with your API keys

cp config.example.json config.json
# Edit config.json with your candidate profile
# config.json is gitignored — safe to put real values here
```

Key fields in `config.json`:

```json
{
  "candidate": {
    "name": "Your Name",
    "resume_path": "resume/YOUR_RESUME.md",
    "profile": "8 YOE Senior ML Engineer. Python, LLMs, AWS, MLOps.",
    "seeking": "Remote-friendly EU or NA roles",
    "min_score": 65,
    "top_n": 5
  }
}
```

### 4. Add your resume

Replace the template at `resume/YOUR_RESUME.md` with your own resume in Markdown format.

### 5. Run

```bash
# One-off scan
autopilot scan

# Draft application for job #1 from last scan
autopilot draft 1

# Draft for a specific URL
autopilot draft https://company.com/jobs/senior-ml-engineer

# Export last scan to CSV
autopilot export --min 70
```

### 6. Automate (optional)

```bash
bash setup_cron.sh
# Runs autopilot scan every day at 2:30 AM
```

---

## Claude / MCP integration

Use autopilot-jobs directly inside Claude Code or Claude Desktop:

```bash
pip install 'autopilot-jobs[mcp]'
```

Add to your Claude config:

```json
{
  "mcpServers": {
    "autopilot-jobs": {
      "command": "python",
      "args": ["-m", "job_hunt.mcp_server"],
      "cwd": "/path/to/your/autopilot-jobs",
      "env": {
        "TINYFISH_API_KEY": "your_key",
        "OPENROUTER_API_KEY": "your_key"
      }
    }
  }
}
```

Then just say: *"Scan for ML jobs"* or *"Draft an application for job #2"*

---

## Customize your target companies

Edit `companies.json`. Each entry needs:

```json
{
  "name": "Stripe",
  "careers_url": "https://stripe.com/jobs",
  "search_domain": "stripe.com",
  "location": "Remote / San Francisco, CA",
  "region": "Remote"
}
```

The repo ships with 130+ pre-configured EU, NZ, and remote-friendly tech companies. Add or remove as you like.

---

## How scoring works

The LLM reads your full resume + the full job description and assigns a score 0–100:

| Score | Meaning |
|---|---|
| 80–100 | Near-perfect fit — apply immediately |
| 60–79 | Good fit — worth applying |
| 40–59 | Partial fit — apply if pipeline is thin |
| < 40 | Poor fit — skipped |

Set `min_score` in config to filter. Default: 60.

---

## Project structure

```
autopilot-jobs/
├── job_hunt/
│   ├── main.py          # CLI entry point
│   ├── scanner.py       # Job discovery + LLM scoring
│   ├── drafter.py       # Resume tailoring + cover letter
│   ├── notifier.py      # Telegram notifications
│   ├── llm_utils.py     # OpenRouter wrapper with fallback
│   ├── tools.py         # Protocol-agnostic tool layer
│   └── mcp_server.py    # MCP server (Claude/AI assistant integration)
├── demo/                # Demo scripts for recording GIF
├── resume/              # Put your resume here (gitignored)
├── state/               # Scan state (gitignored)
├── output/              # Generated applications (gitignored)
├── companies.json       # 130+ target companies
├── config.example.json  # Config template (copy to config.json — gitignored)
└── config.json          # Your config (gitignored — never committed)
```

---

## LLM models used (all free)

The tool uses [OpenRouter](https://openrouter.ai) with a fallback chain of free models:

1. `meta-llama/llama-3.3-70b-instruct:free` (primary)
2. `deepseek/deepseek-r1:free`
3. `google/gemma-2-27b-it:free`
4. `mistralai/mistral-7b-instruct:free`

If one model rate-limits, it automatically falls back to the next. **Zero LLM cost by default.**

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). PRs welcome for:
- Adding companies to `companies.json`
- New ATS platform support (Rippling, Lever variants, Workday)
- OpenAI / Gemini MCP adapters
- Better scoring prompts

---

## License

MIT — see [LICENSE](LICENSE).

---

*Built by [@tarunlnmiit](https://github.com/tarunlnmiit). If this saved you hours of job searching, a ⭐ means a lot.*
