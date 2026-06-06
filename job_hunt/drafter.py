import json
import re
from datetime import datetime
from pathlib import Path

from tinyfish import TinyFish

from job_hunt.llm_utils import chat_with_llm

LAST_SCAN_FILE = Path("state/last_scan.json")
OUTPUT_DIR = Path("output")


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def _resolve_job(job_ref: str) -> tuple[str, str]:
    """Returns (url, company_slug). job_ref is '#1', '1', or a full URL."""
    if job_ref.startswith("http"):
        return job_ref, "company"

    if not LAST_SCAN_FILE.exists():
        raise FileNotFoundError("No scan results found. Run: autopilot scan")

    jobs = json.loads(LAST_SCAN_FILE.read_text())
    idx = int(re.sub(r"\D", "", job_ref)) - 1
    if idx < 0 or idx >= len(jobs):
        raise ValueError(f"Job #{idx + 1} not in last scan (found {len(jobs)} jobs)")

    job = jobs[idx]
    return job["url"], _slug(job.get("company", "company"))


def draft_application(config: dict, job_ref: str) -> None:
    tf = TinyFish(api_key=config["tinyfish_api_key"])

    cand = config.get("candidate", {})
    candidate_name = cand.get("name", "the candidate")
    resume_path = Path(cand.get("resume_path", "resume/YOUR_RESUME.md"))
    resume = resume_path.read_text()
    relocation_note = cand.get("relocation_note", "")

    job_url, company_slug = _resolve_job(job_ref)

    print(f"Fetching JD: {job_url}")
    fetch_resp = tf.fetch.get_contents([job_url], format="markdown")
    if not fetch_resp.results or not fetch_resp.results[0].text:
        raise RuntimeError(f"Failed to fetch JD. Errors: {fetch_resp.errors}")

    jd = fetch_resp.results[0].text
    jd_truncated = jd[:4000]

    date_str = datetime.now().strftime("%Y-%m-%d")
    out_dir = OUTPUT_DIR / f"{company_slug}-{date_str}"
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Tailored resume
    print("Tailoring resume...")
    resume_md = chat_with_llm(
        config,
        messages=[{"role": "user", "content": f"""Rewrite the resume below to mirror the language and emphasized skills in this job description.

Rules:
- Keep every fact truthful — do NOT invent experience
- Mirror JD terminology where the candidate genuinely has that experience
- Reorder projects/bullets to surface most relevant experience first
- Keep the same section structure
- Output full resume in Markdown

JOB DESCRIPTION:
{jd_truncated}

ORIGINAL RESUME:
{resume}

Output ONLY the tailored resume in Markdown. No preamble."""}],
        temperature=0.2,
    )
    tailored_resume_path = out_dir / f"resume_{company_slug}.md"
    tailored_resume_path.write_text(resume_md)
    print(f"  Saved: {tailored_resume_path}")

    # 2. Cover letter
    print("Drafting cover letter...")
    relocation_line = f"- {relocation_note}" if relocation_note else ""
    cover_md = chat_with_llm(
        config,
        messages=[{"role": "user", "content": f"""Write a one-page cover letter for {candidate_name} applying to this role.

Rules:
- Open with one specific reason this role fits {candidate_name} (reference something concrete in the JD)
- Paragraph 1: most relevant experience (2-3 sentences)
- Paragraph 2: why this company specifically (not generic)
- Close: clear ask for an interview
- Tone: direct and confident, not obsequious
{relocation_line}
- Do NOT use: "I am excited to apply", "I am a team player", "I am passionate about"

JOB DESCRIPTION:
{jd_truncated}

CANDIDATE RESUME:
{resume[:2500]}

Output ONLY the cover letter. No preamble."""}],
        temperature=0.3,
    )
    cover_path = out_dir / f"cover_letter_{company_slug}.md"
    cover_path.write_text(cover_md)
    print(f"  Saved: {cover_path}")

    # 3. Application info
    print("Extracting application info...")
    info_txt = chat_with_llm(
        config,
        messages=[{"role": "user", "content": f"""Extract from this job posting (plain text output, clear labels):

1. Application URL or email
2. Hiring manager / recruiter name (if mentioned)
3. "Contact for questions" info (if mentioned)
4. Application deadline (if mentioned)
5. Key requirements (bullet list, max 8 items)
6. Nice-to-have skills (bullet list, max 5 items)

JOB DESCRIPTION:
{jd_truncated}"""}],
        temperature=0.1,
    )
    info_path = out_dir / "application_info.txt"
    info_path.write_text(f"Source URL: {job_url}\n\n{info_txt}")
    print(f"  Saved: {info_path}")

    print(f"\nAll files in: {out_dir.resolve()}")
    print("Review, edit, then submit manually.")
