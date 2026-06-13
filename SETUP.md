# Setting Up autopilot-jobhunt

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue)](https://www.python.org/)
[![Free APIs](https://img.shields.io/badge/APIs-free%20tier-brightgreen)](#step-1--get-your-api-keys)
[![MCP-ready](https://img.shields.io/badge/MCP-Claude%20Code-blueviolet)](#step-7--register-with-claude-code-mcp)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

This guide walks you from zero to a running job scanner with Claude Code MCP integration. It covers every prerequisite, API key setup, rate limit details, and the exact commands needed at each step.

**Time to complete:** ~15 minutes setup + first scan runs automatically.

---

## Prerequisites

```bash
python3 --version   # must be 3.11 or higher
git --version       # any recent version
```

If Python is below 3.11, install via [pyenv](https://github.com/pyenv/pyenv) or [python.org](https://www.python.org/downloads/).

---

## Step 1 — Get your API keys

### TinyFish (required · free)

> [!NOTE]
> TinyFish is **completely free**. No credit card required — just sign up.

1. Go to [agent.tinyfish.ai](https://agent.tinyfish.ai) and create an account
2. Dashboard → **API Keys** → **Create key**
3. Copy the key (starts with `sk-tinyfish-…`)

> [!TIP]
> The free tier has generous throughput limits. The scanner automatically paces itself to
> 5 searches/minute and 25 URL fetches/minute to stay well within these limits.
> A full scan of 130+ companies takes 30–90 minutes **by design** — not because of
> tight limits, but because of deliberate rate-limit-friendly pacing.

---

### OpenRouter (required · free)

> [!NOTE]
> OpenRouter provides access to powerful LLM models on a free tier. No credit card needed to get started.

1. Go to [openrouter.ai](https://openrouter.ai) and create an account
2. **Keys** → **Create key**
3. Copy the key (starts with `sk-or-v1-…`)

autopilot-jobhunt uses a 4-model fallback chain — all free:

| Model | Role | Characteristic |
|---|---|---|
| `meta-llama/llama-3.3-70b-instruct` | Primary | Best scoring quality |
| `nvidia/nemotron-3-super-120b-a12b` | Fallback 1 | 120B — strong reasoning |
| `google/gemma-4-31b-it` | Fallback 2 | Reliable, fast |
| `qwen/qwen3-coder` | Fallback 3 | Good at structured output |

If the primary model hits its daily free quota, the tool automatically tries the next one — no action needed from you.

A nightly scan uses approximately **5–15 LLM calls** (jobs are scored in batches of 10). Running once per day via cron is comfortably within free tier limits for all four models.

> [!TIP]
> Check current per-model free limits at [openrouter.ai/models](https://openrouter.ai/models).
> If all 4 models hit their daily quota, wait for the **midnight UTC reset** — or add a
> small OpenRouter credit ($1–5) to remove the daily cap entirely.

---

### Option B — Claude Code CLI (optional — no API key needed)

<details>
<summary>Use Claude Code CLI as your LLM — no API key required — click to expand</summary>

If you have [Claude Code](https://claude.ai/code) installed and authenticated (Pro, Team, or Enterprise subscription), you can use it as the LLM backend without any API key.

1. Install Claude Code: [claude.ai/code](https://claude.ai/code)
2. Authenticate:
   ```bash
   claude auth login
   ```
3. Verify it works:
   ```bash
   claude --print "hi"
   ```
4. In `config.json`, set:
   ```json
   "llm_provider": "claude_cli"
   ```
5. Optionally set a model (empty string = Claude's default):
   ```json
   "claude_cli_model": "sonnet"
   ```
   Accepted values: `"sonnet"`, `"opus"`, `"haiku"`, or a full model ID like `"claude-sonnet-4-6"`.

You can also switch provider via environment variable without editing config:
```bash
LLM_PROVIDER=claude_cli autopilot scan
```

> [!TIP]
> Leave `openrouter_api_key` empty if using Claude CLI — the field is ignored when
> `llm_provider` is set to `"claude_cli"`.

> [!WARNING]
> **Cron jobs and MCP server:** Both run as background processes. They inherit the shell
> environment of the user who started them, so your `claude` auth session must be active
> in that environment. Run `claude --print "hi"` from the same shell context (same user,
> same session) before scheduling to confirm auth works there.

> [!NOTE]
> `temperature` and `max_tokens` are not configurable when using Claude CLI — the binary
> doesn't expose these flags. The default model settings are used for all calls.

> [!WARNING]
> **Subscription rate-limit burn.** Each CLI call loads your global Claude Code context
> (CLAUDE.md, rules, memory) — typically 25,000–30,000 tokens even for a short prompt. A
> nightly scan makes 5–15 LLM calls, consuming that many large requests against your
> subscription's 7-day rate limit. If you're already heavy on Claude Code usage, a full
> scan may trigger a rate-limit warning or temporary slowdown. Prefer OpenRouter (default)
> for nightly automation; use Claude CLI for occasional on-demand drafts or when testing.

</details>

---

### Option C — Anthropic API (optional — alternative to OpenRouter)

<details>
<summary>Use Claude API with an Anthropic API key — click to expand</summary>

If you have an Anthropic API key or Claude Pro, you can skip OpenRouter entirely.

1. Get an API key at [console.anthropic.com](https://console.anthropic.com)
2. Install the Claude extra:
   ```bash
   pip install 'autopilot-jobhunt[claude]'
   ```
3. In `config.json`, set:
   ```json
   "llm_provider": "anthropic",
   "anthropic_api_key": "sk-ant-...",
   "anthropic_model": "claude-haiku-4-5-20251001"
   ```

Recommended models:
- `claude-haiku-4-5-20251001` — fast and affordable, handles JSON scoring well
- `claude-sonnet-4-6` — higher quality scores, higher cost

> [!TIP]
> Leave `openrouter_api_key` empty if using the Anthropic API — the field is ignored when
> `llm_provider` is set to `"anthropic"`.

</details>

---

### Telegram (optional)

<details>
<summary>Set up Telegram notifications — click to expand</summary>

Telegram lets autopilot-jobhunt message you the top job matches immediately after each scan.

1. Open Telegram and message **@BotFather**
2. Send `/newbot` and follow the prompts
3. Copy the **bot token** (looks like `8024470769:AAFw…`)
4. Message **@userinfobot** to get your **chat_id** (a number like `123456789`)

You'll add both values to `.env` in Step 5.

> [!NOTE]
> Telegram is **entirely optional**. If you skip it, scan results print to your terminal
> instead of being sent to you. The tool does not crash or exit without Telegram configured.

</details>

---

## Step 2 — Install

### Option A — pip install (quickest)

```bash
pip install 'autopilot-jobhunt[mcp]'   # includes Claude Code MCP support
mkdir my-job-hunt && cd my-job-hunt
autopilot init
```

`autopilot init` seeds your working directory with everything you need:

```
✓ companies.json created (130+ companies pre-loaded)
✓ config.json created — fill in your API keys and profile
✓ .env created — fill in your API keys
✓ resume/YOUR_RESUME.md created — replace with your resume

Next:
  1. Edit config.json — set your name, profile, and API keys
  2. Replace resume/YOUR_RESUME.md with your actual resume
  3. Run: autopilot scan
```

> [!IMPORTANT]
> Always run `autopilot` commands from the directory where you ran `autopilot init`.
> The tool reads `config.json` and `companies.json` from the current working directory.

### Option B — clone (recommended if you want to customize companies or contribute)

```bash
git clone https://github.com/tarunlnmiit/autopilot-jobhunt.git
cd autopilot-jobhunt
pip install -e '.[mcp]'
```

✅ **Expected last line:**
```
Successfully installed autopilot-jobhunt-0.1.0
```

> [!NOTE]
> The `[mcp]` extra installs the MCP SDK needed for Claude Code integration.
> If you only want the CLI (no Claude Code), use `pip install -e .` instead.

---

## Step 3 — Configure your candidate profile

```bash
cp config.example.json config.json
```

Open `config.json` and fill in the `candidate` section. Here's what each field controls:

```jsonc
{
  "tinyfish_api_key": "YOUR_TINYFISH_API_KEY",
  "openrouter_api_key": "YOUR_OPENROUTER_API_KEY",
  "candidate": {
    "name": "Your Name",                          // appears in drafted cover letters
    "resume_path": "resume/YOUR_RESUME.md",       // path to your resume file
    "profile": "8 YOE ML Engineer. Python, LLMs, AWS, MLOps.",
    //          ↑ 1–2 sentence summary — the LLM uses this when scoring fit
    "seeking": "Remote EU or NA roles, open to relocation",
    //          ↑ positive signal — jobs matching this score higher
    "not_suitable": "Junior roles, pure front-end, no-ML SWE",
    //               ↑ negative filter — jobs matching this score lower
    "min_score": 65,   // jobs below this threshold are not saved or drafted
    "top_n": 5         // how many top matches to include in Telegram notification
  }
}
```

> [!WARNING]
> `config.json` is gitignored — it will **never** be accidentally committed to git.
> It is safe to store your real values here.

---

## Step 4 — Add your resume

```bash
# macOS
open resume/YOUR_RESUME.md

# Linux / any editor
nano resume/YOUR_RESUME.md
```

Replace the placeholder content with your real work history. The template uses standard Markdown — headings, bullet points, no special syntax required.

> [!TIP]
> The LLM reads your **full resume text** when scoring each job. More specific detail
> (exact tools, scale of projects, years per role) directly improves scoring accuracy.
> A thin resume = lower-confidence scores.

---

## Step 5 — Set API keys

```bash
cp .env.example .env
```

Open `.env` and fill in your keys:

```bash
# Required
TINYFISH_API_KEY=sk-tinyfish-your-key-here
OPENROUTER_API_KEY=sk-or-v1-your-key-here

# Optional — delete these two lines if skipping Telegram
TELEGRAM_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_numeric_chat_id_here
```

> [!WARNING]
> `.env` is gitignored. Never commit it. Never share it. If you accidentally expose a key,
> rotate it immediately from the service dashboard.

---

## Step 6 — Verify setup

Run a smoke test that makes **no API calls** and needs **no API keys** —
`export` only reads local scan state:

```bash
autopilot export
```

✅ **Expected output (before first scan):**
```
No scan found. Run: autopilot scan
```

If you see this, your install is working correctly — the CLI is on your PATH,
bundled data files are in place, everything is wired up. The message just means
you haven't run a scan yet. (You do **not** need to fill in any API keys for this
check to pass.)

**After your first scan**, `autopilot export` produces a CSV like this:

```
Company,Role,Location,Application URL,Score (%),Stack,Region,Reason,Worth Applying,Scan Date
Mistral AI,Applied AI Engineer ML Infrastructure,Paris/London/Marseille On-site,https://jobs.lever.co/mistral/...,85,"Python,LLMs,RAG,AWS,MLOps,DevOps",EU,Role combines applied AI + ML infrastructure in EU,True,2026-06-06
HuggingFace,Staff ML Engineer,Remote (EU),https://apply.workable.com/huggingface/...,80,"Python,PyTorch,Transformers,CUDA,MLOps",EU,Open-source ML role matches deep learning background,True,2026-06-06
```

> [!NOTE]
> If you see `autopilot: command not found`, re-run `pip install -e '.[mcp]'` from
> inside the `autopilot-jobhunt` directory.

---

## Step 7 — Register with Claude Code (MCP)

> [!IMPORTANT]
> The MCP server reads `config.json` and `companies.json` from its **working directory**.
> You must tell Claude Code where the repo lives by setting the `cwd` field.

### 7a — Get the absolute path to the repo

Run this from inside the `autopilot-jobhunt` directory:

```bash
pwd
```

Example output:
```
/Users/yourname/autopilot-jobhunt
```

Copy this path — you'll need it in 7c.

---

### 7b — Register the MCP server

**Option A: one command (then manually add `cwd` in 7c)**

```bash
claude mcp add autopilot-jobhunt \
  --env TINYFISH_API_KEY=sk-tinyfish-your-key \
  --env OPENROUTER_API_KEY=sk-or-v1-your-key \
  --env TELEGRAM_TOKEN=your_token \
  --env TELEGRAM_CHAT_ID=your_chat_id \
  -- python -m job_hunt.mcp_server
```

> [!NOTE]
> If skipping Telegram, omit the last two `--env` lines.

**Option B: edit `~/.claude.json` directly**

Open `~/.claude.json` (create it if it doesn't exist) and add the block below under `"mcpServers"`:

```json
{
  "mcpServers": {
    "autopilot-jobhunt": {
      "command": "python",
      "args": ["-m", "job_hunt.mcp_server"],
      "cwd": "/Users/yourname/autopilot-jobhunt",
      "env": {
        "TINYFISH_API_KEY": "sk-tinyfish-your-key",
        "OPENROUTER_API_KEY": "sk-or-v1-your-key",
        "TELEGRAM_TOKEN": "your_token",
        "TELEGRAM_CHAT_ID": "your_chat_id"
      }
    }
  }
}
```

---

### 7c — Set the working directory (required for Option A)

If you used `claude mcp add` (Option A), open `~/.claude.json` and find the `autopilot-jobhunt` entry. Add the `"cwd"` field pointing to your repo path from Step 7a:

```json
"autopilot-jobhunt": {
  "command": "python",
  "args": ["-m", "job_hunt.mcp_server"],
  "cwd": "/Users/yourname/autopilot-jobhunt",   // ← add this line
  "env": { ... }
}
```

---

### 7d — Confirm registration

```bash
claude mcp list
```

✅ **Expected:** `autopilot-jobhunt` appears in the list.

If it doesn't appear, open a new terminal and try again — Claude Code picks up config changes on restart.

---

### 7e — Verify MCP is working

Start a Claude Code session and say:

> "List the tools available from autopilot-jobhunt"

Claude should respond with: `scan_jobs`, `draft_application`, `export_jobs`.

---

## Step 8 — First scan

```bash
autopilot scan
```

Or, inside Claude Code:

> "Scan for new jobs matching my profile"

> [!NOTE]
> A full scan of all 130+ companies takes **30–90 minutes**. This is expected — the scanner
> paces itself to stay within TinyFish's free throughput limits (5 searches/min,
> 25 URL fetches/min). You don't need to do anything during this time.

During the scan, you'll see progress like:

```
Scanning Mistral AI...
  3 new job URLs. Fetching details...
  Scoring jobs...
  Saved 2 jobs from Mistral AI

Scanning HuggingFace...
  5 new job URLs. Fetching details...
  Scoring jobs...
  Saved 3 jobs from HuggingFace

Scanning Stripe...
  No new jobs found

Scanning Wise...
  2 new job URLs. Fetching details...
  Scoring jobs...
  Saved 0 jobs from Wise

...
Scan complete.
Top 5 sent to Telegram.
```

> [!NOTE]
> "Saved 0 jobs" means jobs were found but scored below your `min_score` threshold — not an error.
> "No new jobs found" means TinyFish found no postings matching your search query for that company today.

---

## Step 9 — Use inside Claude Code

After registration, these prompts work in any Claude Code session:

```
"Scan for new jobs matching my profile"
"Draft an application for job #1 from the last scan"
"Draft a cover letter for this job: https://company.com/jobs/ml-engineer"
"Export all jobs with score above 70 from the past week"
"Show me the top 5 jobs from yesterday's scan"
```

---

## Step 10 — Automate with cron (optional)

<details>
<summary>Run autopilot scan every night automatically — click to expand</summary>

```bash
bash setup_cron.sh
```

This adds a cron job that runs `autopilot scan` every day at 2:30 AM local time and saves logs to `scan.log`.

> [!TIP]
> Running once per day is the recommended cadence. It keeps you within OpenRouter's
> per-model daily quotas and ensures you see new postings the morning after they appear.
> Running the scan multiple times per day risks exhausting free-tier LLM limits.

To remove the cron job:
```bash
crontab -e   # delete the autopilot-jobhunt line
```

</details>

---

## Troubleshooting

<details>
<summary>Common errors and how to fix them — click to expand</summary>

| Symptom | Likely cause | Fix |
|---|---|---|
| `config.json not found` | Wrong working directory or `cwd` not set | Run `autopilot init` in your working dir, or add `"cwd"` to `~/.claude.json` — see Step 7c |
| `All LLM models failed` | Wrong key, or all 4 models hit daily quota | Verify `OPENROUTER_API_KEY`; wait for midnight UTC reset |
| `claude binary not found in PATH` | Claude CLI not installed or not on PATH | Install from [claude.ai/code](https://claude.ai/code); run `which claude` to verify |
| `claude CLI exited 1` | Not authenticated | Run `claude auth login` then retry |
| `autopilot: command not found` | pip install incomplete or wrong venv | Re-run `pip install -e '.[mcp]'` from repo directory |
| No Telegram notification | Token not configured | Expected — scan still completes, results print to terminal |
| Scan takes 30–90 min | Normal pacing for free tier | Let it run; use cron to automate |
| `python3 --version` < 3.11 | Python too old | Install 3.11+ via [pyenv](https://github.com/pyenv/pyenv) |
| MCP server not in `claude mcp list` | Config not reloaded | Open a new terminal and check again |

Still stuck? [Open an issue](https://github.com/tarunlnmiit/autopilot-jobhunt/issues) with the error message and your Python version.

</details>

---

## Next steps

- Edit `companies.json` to add companies you want to target
- Adjust `min_score` in `config.json` (60–70 is a good starting range)
- After your first scan, try `autopilot draft 1` to generate your first cover letter
- Star the repo if this saved you time → [github.com/tarunlnmiit/autopilot-jobhunt](https://github.com/tarunlnmiit/autopilot-jobhunt)
