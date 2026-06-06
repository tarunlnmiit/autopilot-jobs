import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

from tinyfish import RateLimitError, TinyFish

from job_hunt.llm_utils import chat_with_llm
from job_hunt.notifier import send_telegram

STATE_FILE = Path("state/seen_jobs.json")
LAST_SCAN_FILE = Path("state/last_scan.json")
JOB_HISTORY_FILE = Path("state/job_history.json")

# Matches individual job postings by URL pattern
JOB_URL_RE = re.compile(
    r"/(job|jobs|opening|openings|position|positions|vacancy|vacancies|role|roles|apply)"
    r"/[a-zA-Z0-9_%@.-]{4,}",
    re.IGNORECASE,
)
# Lever: job UUID is 36 chars; Greenhouse: /jobs/12345; Ashby: /jobs/uuid
ATS_JOB_RE = re.compile(
    r"(greenhouse\.io/.+/jobs/\d+"
    r"|lever\.co/[^/]+/[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}"
    r"|myworkdayjobs\.com/[^?#]+"
    r"|smartrecruiters\.com/[^/]+/[A-Z0-9]+"
    r"|ashbyhq\.com/[^/]+/[a-f0-9-]{32,})",
    re.IGNORECASE,
)
# ATS listing pages (company-level, not individual jobs) — need one more hop
ATS_LISTING_RE = re.compile(
    r"^https?://(jobs\.lever\.co|boards\.greenhouse\.io|apply\.workable\.com"
    r"|jobs\.smartrecruiters\.com)/[^/?#]+/?(\?.*)?$",
    re.IGNORECASE,
)

SEARCH_QUERY = (
    'site:{domain} (senior OR staff OR principal OR lead) '
    '("data scientist" OR "ML engineer" OR "machine learning engineer" '
    'OR "AI engineer" OR MLOps OR "deep learning")'
)

SCORE_PROMPT = """You are evaluating job postings for a candidate. Output ONLY a JSON array, no other text.

CANDIDATE:
{candidate_profile}

RESUME SUMMARY:
{resume_summary}

JOBS TO SCORE:
{jobs_text}

For each job output:
{{
  "job_number": 1,
  "score": 0-100,
  "title": "extracted job title",
  "stack": "key tech from JD (comma-separated, max 6 items)",
  "location_remote": "location + remote policy",
  "reason": "one sentence why this fits or doesn't fit the candidate",
  "worth_applying": true/false
}}

Scoring: 80-100 near-perfect; 60-79 good fit; 40-59 partial; <40 poor.
Set worth_applying=true only if score >= {min_score}.
Include ALL jobs. Output ONLY the JSON array."""


def _build_candidate_profile(config: dict) -> str:
    cand = config.get("candidate", {})
    name = cand.get("name", "the candidate")
    profile = cand.get("profile", "")
    seeking = cand.get("seeking", "")
    not_suitable = cand.get("not_suitable", "")

    lines = [f"- {name}"]
    if profile:
        lines.append(f"- {profile}")
    if seeking:
        lines.append(f"- Seeking: {seeking}")
    if not_suitable:
        lines.append(f"- NOT suitable: {not_suitable}")
    return "\n".join(lines)


def is_job_url(url: str) -> bool:
    return bool(JOB_URL_RE.search(url)) or bool(ATS_JOB_RE.search(url))


def is_ats_listing(url: str) -> bool:
    return bool(ATS_LISTING_RE.match(url))


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"seen_urls": []}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


_FETCH_URL_DELAY = 2.5  # seconds per URL to stay under 25 URLs/min


def _fetch_with_ratelimit(
    tf: TinyFish, urls: list[str], **kwargs
):
    """Single fetch call with rate-limit retry."""
    for attempt in range(2):
        try:
            resp = tf.fetch.get_contents(urls, **kwargs)
            time.sleep(len(urls) * _FETCH_URL_DELAY)
            return resp
        except RateLimitError:
            print("  fetch rate-limited, waiting 65s...")
            time.sleep(65)
        except Exception as e:
            print(f"  fetch error: {e}")
            time.sleep(len(urls) * _FETCH_URL_DELAY)
            return None
    return None


def _fetch_links(tf: TinyFish, urls: list[str]) -> dict[str, list[str]]:
    """Batch fetch URLs, return {url: [links]} mapping."""
    result = {}
    for i in range(0, len(urls), 10):
        batch = urls[i : i + 10]
        resp = _fetch_with_ratelimit(tf, batch, format="markdown", links=True)
        if resp:
            for r in resp.results:
                result[r.url] = r.links
    return result


def discover_job_urls(
    tf: TinyFish, company: dict, seen_urls: set
) -> list[dict]:
    """
    Multi-hop discovery:
    1. Fetch careers page → extract direct job links + ATS listing pages
    2. Fetch ATS listing pages → extract individual job links
    3. Search for additional indexed job pages
    """
    found_urls: set[str] = set()

    # --- Step 1: Fetch careers page ---
    resp = _fetch_with_ratelimit(tf, [company["careers_url"]], format="markdown", links=True)
    if resp:
        if resp.results:
            links = resp.results[0].links
            direct = [link for link in links if is_job_url(link) and link not in seen_urls]
            ats_pages = list({link for link in links if is_ats_listing(link)})
            found_urls.update(direct)

            # --- Step 2: Expand ATS listing pages ---
            if ats_pages:
                ats_link_map = _fetch_links(tf, ats_pages[:5])
                for page_links in ats_link_map.values():
                    for link in page_links:
                        if is_job_url(link) and link not in seen_urls:
                            found_urls.add(link)

    # --- Step 3: Search for indexed job pages (rate-limited: 5/min) ---
    query = SEARCH_QUERY.format(domain=company["search_domain"])
    for attempt in range(2):
        try:
            resp = tf.search.query(query, language="en")
            for r in resp.results:
                if is_job_url(r.url) and r.url not in seen_urls:
                    found_urls.add(r.url)
            time.sleep(13)  # stay under 5 req/min
            break
        except RateLimitError:
            print(f"  search rate-limited ({company['name']}), waiting 60s...")
            time.sleep(62)
        except Exception as e:
            print(f"  search error ({company['name']}): {e}")
            time.sleep(13)
            break

    new = [
        {
            "url": u,
            "title": u.split("/")[-1].replace("-", " ").title(),
            "snippet": "",
            "company": company["name"],
            "location": company["location"],
            "region": company["region"],
        }
        for u in found_urls
    ]
    return new


def fetch_job_details(tf: TinyFish, jobs: list[dict]) -> list[dict]:
    enriched = []
    for i in range(0, len(jobs), 10):
        batch = jobs[i : i + 10]
        urls = [j["url"] for j in batch]
        resp = _fetch_with_ratelimit(tf, urls, format="markdown")
        if not resp:
            enriched.extend(batch)
            continue
        fetched = {r.url: r for r in resp.results}
        for job in batch:
            r = fetched.get(job["url"])
            if r and r.text:
                job["content"] = r.text[:3000]
                job["title"] = r.title or job["title"]
            enriched.append(job)
    return enriched


def score_jobs(jobs: list[dict], resume: str, config: dict) -> list[dict]:
    if not jobs:
        return []

    jobs_text = "\n\n".join(
        f"JOB {i + 1}:\nCompany: {j['company']} | Location: {j['location']}\n"
        f"Title: {j['title']}\nURL: {j['url']}\n"
        f"Content:\n{j.get('content', j.get('snippet', ''))[:1500]}"
        for i, j in enumerate(jobs)
    )

    min_score = config.get("candidate", {}).get("min_score", 55)
    candidate_profile = _build_candidate_profile(config)

    prompt = SCORE_PROMPT.format(
        candidate_profile=candidate_profile,
        resume_summary=resume[:2500],
        jobs_text=jobs_text,
        min_score=min_score,
    )

    try:
        raw = chat_with_llm(
            config,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
        )
        start, end = raw.find("["), raw.rfind("]") + 1
        if start == -1:
            return []
        scored = json.loads(raw[start:end])
    except Exception as e:
        print(f"  scoring error: {e}")
        return []

    results = []
    for item in scored:
        if not item.get("worth_applying"):
            continue
        idx = item.get("job_number", 0) - 1
        if 0 <= idx < len(jobs):
            job = jobs[idx].copy()
            job.update(
                {
                    "score": item.get("score", 0),
                    "extracted_title": item.get("title", job["title"]),
                    "stack": item.get("stack", ""),
                    "location_remote": item.get("location_remote", job["location"]),
                    "reason": item.get("reason", ""),
                }
            )
            results.append(job)

    return sorted(results, key=lambda x: x["score"], reverse=True)


def format_telegram_message(top_jobs: list[dict], date_str: str) -> str:
    lines = [f"<b>Job Hunt — {date_str}</b>", f"<i>{len(top_jobs)} matches found</i>\n"]
    for i, job in enumerate(top_jobs, 1):
        lines.append(
            f"<b>#{i}</b> | {job['company']} | {job.get('extracted_title', job['title'])}\n"
            f"📍 {job.get('location_remote', job['location'])}\n"
            f"🔧 {job.get('stack', 'N/A')}\n"
            f"✅ {job.get('reason', '')}\n"
            f"<a href=\"{job['url']}\">Apply</a>\n"
        )
    lines.append('Reply "apply to #N" to draft application.')
    return "\n".join(lines)


def run_scan(config: dict, companies: list[dict]) -> None:
    try:
        tf = TinyFish(api_key=config["tinyfish_api_key"])
    except Exception as e:
        print(f"TinyFish init error: {e}")
        return

    resume_path = Path(config.get("candidate", {}).get("resume_path", "resume/YOUR_RESUME.md"))
    resume = resume_path.read_text()
    min_score = config.get("candidate", {}).get("min_score", 55)
    top_n = config.get("candidate", {}).get("top_n", 5)

    state = load_state()
    seen_urls: set = set(state.get("seen_urls", []))
    all_scored_jobs: list[dict] = []
    errors: list[str] = []

    for company in companies:
        print(f"Scanning {company['name']}...")
        try:
            new_jobs = discover_job_urls(tf, company, seen_urls)
            if not new_jobs:
                print("  No new jobs found")
                continue

            print(f"  {len(new_jobs)} new job URLs. Fetching details...")
            new_jobs = fetch_job_details(tf, new_jobs)
            seen_urls.update(j["url"] for j in new_jobs)

            print("  Scoring jobs...")
            scored: list[dict] = []
            try:
                for i in range(0, len(new_jobs), 10):
                    batch = new_jobs[i : i + 10]
                    batch_scored = score_jobs(batch, resume, config)
                    scored.extend(batch_scored)
            except Exception as score_err:
                print(f"  Scoring failed: {score_err}")
                msg = f"⚠️ Scoring failed for {company['name']}: {score_err}"
                errors.append(msg)
                print(f"  Fallback: saving unscored jobs from {company['name']}")
                scored = new_jobs

            if scored:
                all_scored_jobs.extend(scored)
                print(f"  Saved {len(scored)} jobs from {company['name']}")

        except Exception as company_err:
            msg = f"❌ {company['name']}: {company_err}"
            errors.append(msg)
            print(f"  Company scan failed: {company_err}")
            continue

    state["seen_urls"] = list(seen_urls)
    state["last_scan"] = datetime.now(timezone.utc).isoformat()
    save_state(state)

    top_jobs = sorted([j for j in all_scored_jobs if j.get("score", 0) >= min_score],
                      key=lambda x: x.get("score", 0), reverse=True)[:top_n]

    scan_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for job in all_scored_jobs:
        job["scan_date"] = scan_date

    LAST_SCAN_FILE.parent.mkdir(exist_ok=True)
    LAST_SCAN_FILE.write_text(json.dumps(all_scored_jobs, indent=2))

    history: list[dict] = []
    if JOB_HISTORY_FILE.exists():
        try:
            history = json.loads(JOB_HISTORY_FILE.read_text())
        except Exception:
            history = []
    existing_urls = {j["url"] for j in history}
    new_entries = [j for j in all_scored_jobs if j["url"] not in existing_urls]
    history.extend(new_entries)
    JOB_HISTORY_FILE.write_text(json.dumps(history, indent=2))

    date_str = datetime.now().strftime("%d %b %Y")
    tg = config.get("telegram", {})

    if errors and tg.get("token") and tg.get("chat_id"):
        error_msg = f"<b>Job Hunt Errors — {date_str}</b>\n" + "\n".join(errors)
        send_telegram(tg["token"], tg["chat_id"], error_msg)

    if not top_jobs:
        print("No matching jobs found today.")
        msg = f"<b>Job Hunt — {date_str}</b>\nNo new matches today."
    else:
        msg = format_telegram_message(top_jobs, date_str)
        print("\n" + msg)

    if tg.get("token") and tg.get("chat_id"):
        send_telegram(tg["token"], tg["chat_id"], msg)
    else:
        print("\n[Telegram not configured — add token and chat_id to config.json]")
