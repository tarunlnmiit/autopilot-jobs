# Contributing to autopilot-jobhunt

Thanks for wanting to contribute. Here's what's most useful:

## High-value contributions

### 1. Add companies to `companies.json`

The most impactful contribution — more companies = more jobs found for everyone.

Format:
```json
{
  "name": "Company Name",
  "careers_url": "https://company.com/careers",
  "search_domain": "company.com",
  "location": "City, Country",
  "region": "EU | US | APAC | Remote | NZ"
}
```

Please verify the careers URL works before submitting.

### 2. ATS platform support

The scanner handles: Lever, Greenhouse, Ashby, SmartRecruiters, Workable.

Missing: Rippling, Fountain, Teamtailor, SAP SuccessFactors, iCIMS.

If you can identify the URL patterns for a new ATS, open an issue or PR targeting `scanner.py`.

### 3. MCP adapters for other AI assistants

The `job_hunt/tools.py` layer is protocol-agnostic. Adding support for a new AI assistant = wrapping the three functions in that assistant's tool format.

See `mcp_server.py` as the reference implementation.

### 4. Scoring prompt improvements

If you find the LLM scores inaccurately, open an issue with:
- The job description (anonymized if needed)
- The score given
- What you expected and why

## Development setup

```bash
git clone https://github.com/tarunlnmiit/autopilot-jobhunt.git
cd autopilot-jobhunt
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

Run linting:
```bash
ruff check job_hunt/
```

## Pull request guidelines

- One PR per logical change
- Test your change locally before submitting
- For `companies.json` additions: batch up to 10 companies per PR
- For code changes: briefly explain what problem you're solving

## Reporting issues

Open an issue with:
1. What you ran (`autopilot scan`, `autopilot draft`, etc.)
2. The error message or unexpected behavior
3. Your Python version and OS
