"""
Job Tracker - Checks career pages for new job postings hourly
Filters for: Internships, New Grad, No-Experience, 1-3 years experience
Sends email notifications to jobnotif27@gmail.com when new jobs are found
"""

import os
import json
import hashlib
import smtplib
import requests
import time
import re
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from bs4 import BeautifulSoup

NOTIFY_EMAIL = "jobnotif27@gmail.com"
SEEN_JOBS_FILE = "seen_jobs.json"

# ─────────────────────────────────────────────
# ENTRY-LEVEL FILTER CONFIGURATION
# ─────────────────────────────────────────────

ENTRY_LEVEL_TITLE_KEYWORDS = [
    "intern", "internship", "co-op", "coop",
    "new grad", "new graduate", "recent grad", "recent graduate",
    "entry level", "entry-level",
    "junior", "jr.",
    "associate",
    "early career",
    "university grad", "university graduate",
    "campus", "trainee", "apprentice",
]

EXCLUDE_TITLE_KEYWORDS = [
    "senior", "sr.", "staff", "principal", "lead", "director",
    "head of", "vp ", "vice president", "manager", "chief",
    "distinguished", "fellow", "architect",
]

ENTRY_LEVEL_API_VALUES = [
    "intern", "internship", "entry", "entry_level", "entrylevel",
    "junior", "associate", "new_grad", "newgrad",
    "0", "0-1", "0-2", "1", "1-2", "1-3",
]

ENTRY_LEVEL_DESC_PHRASES = [
    "0-1 year", "0-2 year", "0 year", "no experience required",
    "no prior experience", "1-3 year", "1 to 3 year",
    "fresh graduate", "recent graduate", "new graduate",
    "entry level", "entry-level", "junior level",
    "0+ year", "less than 1 year",
]


def is_entry_level(job):
    title = job.get("title", "").lower()
    experience = job.get("experience_level", "").lower()
    description = job.get("description", "").lower()

    # 1. Explicit title match (check exclusions first)
    for kw in ENTRY_LEVEL_TITLE_KEYWORDS:
        if kw in title:
            for ex in EXCLUDE_TITLE_KEYWORDS:
                if ex in title:
                    return False, f"excluded (senior variant: '{ex}' in title)"
            return True, f"title match: '{kw}'"

    # 2. API experience level field
    for val in ENTRY_LEVEL_API_VALUES:
        if val in experience:
            return True, f"experience_level field: '{experience}'"

    # 3. Description phrases
    if description:
        for phrase in ENTRY_LEVEL_DESC_PHRASES:
            if phrase in description:
                return True, f"description match: '{phrase}'"

    # 4. Exclude clearly senior titles
    for ex in EXCLUDE_TITLE_KEYWORDS:
        if ex in title:
            return False, f"senior title excluded: '{ex}'"

    # 5. Default: include generic titles (many startups don't label levels)
    return True, "no seniority indicator — included by default"


# ─────────────────────────────────────────────
# COMPANIES LIST
# ─────────────────────────────────────────────

COMPANIES = [
    {"name": "Gumloop",                  "url": "https://jobs.ashbyhq.com/gumloop",               "ats": "ashby"},
    {"name": "Braintrust",               "url": "https://jobs.ashbyhq.com/braintrust",             "ats": "ashby"},
    {"name": "Render",                   "url": "https://render.com/careers",                      "ats": "generic"},
    {"name": "Basis",                    "url": "https://jobs.ashbyhq.com/basis",                  "ats": "ashby"},
    {"name": "Emergent",                 "url": "https://jobs.ashbyhq.com/emergent",               "ats": "ashby"},
    {"name": "Paraform",                 "url": "https://jobs.ashbyhq.com/paraform",               "ats": "ashby"},
    {"name": "Fieldguide",               "url": "https://job-boards.greenhouse.io/fieldguide",     "ats": "greenhouse"},
    {"name": "Cape",                     "url": "https://jobs.ashbyhq.com/cape",                   "ats": "ashby"},
    {"name": "Kai Security",             "url": "https://jobs.ashbyhq.com/kaisecurity",            "ats": "ashby"},
    {"name": "Zafran",                   "url": "https://jobs.ashbyhq.com/zafran",                 "ats": "ashby"},
    {"name": "WitnessAI",                "url": "https://jobs.ashbyhq.com/witnessai",              "ats": "ashby"},
    {"name": "Zocks",                    "url": "https://jobs.ashbyhq.com/zocks",                  "ats": "ashby"},
    {"name": "Pomelo Care",              "url": "https://job-boards.greenhouse.io/pomelocare",     "ats": "greenhouse"},
    {"name": "Tandem",                   "url": "https://jobs.ashbyhq.com/tandem",                 "ats": "ashby"},
    {"name": "Doctronic",                "url": "https://jobs.ashbyhq.com/doctronic",              "ats": "ashby"},
    {"name": "Northwood Space",          "url": "https://jobs.ashbyhq.com/northwoodspace",         "ats": "ashby"},
    {"name": "Overland AI",              "url": "https://jobs.ashbyhq.com/overlandai",             "ats": "ashby"},
    {"name": "Articul8 AI",              "url": "https://jobs.ashbyhq.com/articul8",               "ats": "ashby"},
    {"name": "Freeform",                 "url": "https://jobs.ashbyhq.com/freeform",               "ats": "ashby"},
    {"name": "Listen Labs",              "url": "https://jobs.ashbyhq.com/listenlabs",             "ats": "ashby"},
    {"name": "Spade",                    "url": "https://jobs.ashbyhq.com/spade",                  "ats": "ashby"},
    {"name": "Ostro",                    "url": "https://jobs.ashbyhq.com/ostro",                  "ats": "ashby"},
    {"name": "Hydra Host",               "url": "https://jobs.ashbyhq.com/hydrahost",              "ats": "ashby"},
    {"name": "BreezeBio",                "url": "https://jobs.ashbyhq.com/breezebio",              "ats": "ashby"},
    {"name": "Jump",                     "url": "https://jobs.ashbyhq.com/jump",                   "ats": "ashby"},
    {"name": "Eight Sleep",              "url": "https://job-boards.greenhouse.io/eightsleep",     "ats": "greenhouse"},
    {"name": "Profound",                 "url": "https://jobs.ashbyhq.com/profound",               "ats": "ashby"},
    {"name": "Encord",                   "url": "https://jobs.ashbyhq.com/encord",                 "ats": "ashby"},
    {"name": "Novig",                    "url": "https://jobs.ashbyhq.com/novig",                  "ats": "ashby"},
    {"name": "Guidde",                   "url": "https://jobs.ashbyhq.com/guidde",                 "ats": "ashby"},
    {"name": "UniUni",                   "url": "https://jobs.ashbyhq.com/uniuni",                 "ats": "ashby"},
    {"name": "ORO Labs",                 "url": "https://jobs.ashbyhq.com/orolabs",                "ats": "ashby"},
    {"name": "Aalyria",                  "url": "https://job-boards.greenhouse.io/aalyria",        "ats": "greenhouse"},
    {"name": "Nominal",                  "url": "https://jobs.ashbyhq.com/nominal",                "ats": "ashby"},
    {"name": "Nitra",                    "url": "https://jobs.ashbyhq.com/nitra",                  "ats": "ashby"},
    {"name": "Dwelly",                   "url": "https://jobs.ashbyhq.com/dwelly",                 "ats": "ashby"},
    {"name": "IDfy",                     "url": "https://jobs.ashbyhq.com/idfy",                   "ats": "ashby"},
    {"name": "Axiamatic",                "url": "https://jobs.ashbyhq.com/axiamatic",              "ats": "ashby"},
    {"name": "Juicebox",                 "url": "https://jobs.ashbyhq.com/juicebox",               "ats": "ashby"},
    {"name": "KAST",                     "url": "https://jobs.ashbyhq.com/kast",                   "ats": "ashby"},
    {"name": "ChipAgents",               "url": "https://jobs.ashbyhq.com/chipagents",             "ats": "ashby"},
    {"name": "Isembard",                 "url": "https://jobs.ashbyhq.com/isembard",               "ats": "ashby"},
    {"name": "Mesh Optical Technologies","url": "https://jobs.ashbyhq.com/meshoptical",            "ats": "ashby"},
    {"name": "Salma Health",             "url": "https://jobs.ashbyhq.com/salmahealth",            "ats": "ashby"},
    {"name": "Databricks",               "url": "https://job-boards.greenhouse.io/databricks",     "ats": "greenhouse"},
    {"name": "MotherDuck",               "url": "https://job-boards.greenhouse.io/motherduck",     "ats": "greenhouse"},
    {"name": "HashiCorp",                "url": "https://job-boards.greenhouse.io/hashicorp",      "ats": "greenhouse"},
    {"name": "Temporal",                 "url": "https://job-boards.greenhouse.io/temporal",       "ats": "greenhouse"},
    {"name": "Fivetran",                 "url": "https://job-boards.greenhouse.io/fivetran",       "ats": "greenhouse"},
    {"name": "dbt Labs",                 "url": "https://job-boards.greenhouse.io/dbtlabs",        "ats": "greenhouse"},
    {"name": "ClickUp",                  "url": "https://job-boards.greenhouse.io/clickup",        "ats": "greenhouse"},
    {"name": "Dialpad",                  "url": "https://job-boards.greenhouse.io/dialpad",        "ats": "greenhouse"},
    {"name": "Illumio",                  "url": "https://job-boards.greenhouse.io/illumio",        "ats": "greenhouse"},
    {"name": "GitLab",                   "url": "https://job-boards.greenhouse.io/gitlab",         "ats": "greenhouse"},
    {"name": "Replit",                   "url": "https://jobs.ashbyhq.com/replit",                 "ats": "ashby"},
    {"name": "Tanium",                   "url": "https://job-boards.greenhouse.io/tanium",         "ats": "greenhouse"},
    {"name": "Cursor",                   "url": "https://jobs.ashbyhq.com/anysphere",              "ats": "ashby"},
    {"name": "Sentry",                   "url": "https://job-boards.greenhouse.io/sentry",         "ats": "greenhouse"},
    {"name": "Vanta",                    "url": "https://job-boards.greenhouse.io/vanta",          "ats": "greenhouse"},
    {"name": "Kong",                     "url": "https://job-boards.greenhouse.io/kong",           "ats": "greenhouse"},
    {"name": "Hex",                      "url": "https://jobs.ashbyhq.com/hex",                    "ats": "ashby"},
    {"name": "Wiz",                      "url": "https://job-boards.greenhouse.io/wiz",            "ats": "greenhouse"},
    {"name": "Anchorage Digital",        "url": "https://job-boards.greenhouse.io/anchoragedigital","ats": "greenhouse"},
    {"name": "Coinbase",                 "url": "https://job-boards.greenhouse.io/coinbase",       "ats": "greenhouse"},
    {"name": "Mercury",                  "url": "https://job-boards.greenhouse.io/mercury",        "ats": "greenhouse"},
    {"name": "SpotOn",                   "url": "https://job-boards.greenhouse.io/spoton",         "ats": "greenhouse"},
    {"name": "EarnIn",                   "url": "https://job-boards.greenhouse.io/earnin",         "ats": "greenhouse"},
    {"name": "Affirm",                   "url": "https://job-boards.greenhouse.io/affirm",         "ats": "greenhouse"},
    {"name": "Stripe",                   "url": "https://job-boards.greenhouse.io/stripe",         "ats": "greenhouse"},
    {"name": "Gusto",                    "url": "https://job-boards.greenhouse.io/gusto",          "ats": "greenhouse"},
    {"name": "Aptos",                    "url": "https://jobs.ashbyhq.com/aptos",                  "ats": "ashby"},
    {"name": "Carta",                    "url": "https://job-boards.greenhouse.io/carta",          "ats": "greenhouse"},
    {"name": "Check",                    "url": "https://job-boards.greenhouse.io/check",          "ats": "greenhouse"},
    {"name": "Plaid",                    "url": "https://job-boards.greenhouse.io/plaid",          "ats": "greenhouse"},
    {"name": "Ramp",                     "url": "https://job-boards.greenhouse.io/ramp",           "ats": "greenhouse"},
]

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; JobTracker/1.0)"}


def load_seen_jobs():
    if os.path.exists(SEEN_JOBS_FILE):
        with open(SEEN_JOBS_FILE, "r") as f:
            return json.load(f)
    return {}


def save_seen_jobs(seen):
    with open(SEEN_JOBS_FILE, "w") as f:
        json.dump(seen, f, indent=2)


def make_job_id(company, title, url=""):
    key = f"{company}|{title}|{url}"
    return hashlib.md5(key.encode()).hexdigest()


def fetch_greenhouse_jobs(company):
    try:
        api_url = company["url"].replace(
            "job-boards.greenhouse.io", "boards-api.greenhouse.io/v1/boards"
        ) + "/jobs?content=true"
        resp = requests.get(api_url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return []
        data = resp.json()
        jobs = []
        for job in data.get("jobs", []):
            exp_level = ""
            for meta in job.get("metadata", []):
                if "experience" in meta.get("name", "").lower():
                    exp_level = str(meta.get("value", "")).lower()
            content = job.get("content", "") or ""
            desc_snippet = BeautifulSoup(content, "html.parser").get_text()[:600].lower()
            jobs.append({
                "title": job.get("title", "Unknown"),
                "url": job.get("absolute_url", company["url"]),
                "location": job.get("location", {}).get("name", "Remote/Unknown"),
                "id": str(job.get("id", "")),
                "experience_level": exp_level,
                "description": desc_snippet,
            })
        return jobs
    except Exception as e:
        print(f"  [ERROR] Greenhouse fetch failed for {company['name']}: {e}")
        return []


def fetch_ashby_jobs(company):
    try:
        board_slug = company["url"].rstrip("/").split("/")[-1]
        api_url = f"https://api.ashbyhq.com/posting-api/job-board/{board_slug}"
        resp = requests.get(api_url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return []
        data = resp.json()
        jobs = []
        for job in data.get("jobs", []):
            exp_level = job.get("employmentType", "").lower()
            desc = job.get("descriptionPlain", "") or job.get("description", "") or ""
            desc_snippet = desc[:600].lower()
            jobs.append({
                "title": job.get("title", "Unknown"),
                "url": job.get("jobUrl", company["url"]),
                "location": job.get("location", "Remote/Unknown"),
                "id": job.get("id", ""),
                "experience_level": exp_level,
                "description": desc_snippet,
            })
        return jobs
    except Exception as e:
        print(f"  [ERROR] Ashby fetch failed for {company['name']}: {e}")
        return []


def fetch_generic_jobs(company):
    try:
        resp = requests.get(company["url"], headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return []
        soup = BeautifulSoup(resp.text, "html.parser")
        job_links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            text = a.get_text(strip=True)
            if text and len(text) > 5 and any(
                kw in href.lower() for kw in ["/job", "/position", "/opening", "/role"]
            ):
                full_url = href if href.startswith("http") else f"https://{company['url'].split('/')[2]}{href}"
                job_links.append({
                    "title": text[:100],
                    "url": full_url,
                    "location": "See posting",
                    "id": hashlib.md5(full_url.encode()).hexdigest()[:8],
                    "experience_level": "",
                    "description": "",
                })
        return job_links[:50]
    except Exception as e:
        print(f"  [ERROR] Generic fetch failed for {company['name']}: {e}")
        return []


def fetch_jobs(company):
    ats = company.get("ats", "generic")
    if ats == "greenhouse":
        return fetch_greenhouse_jobs(company)
    elif ats == "ashby":
        return fetch_ashby_jobs(company)
    else:
        return fetch_generic_jobs(company)


def send_email(new_jobs_by_company):
    sender = os.environ.get("GMAIL_USER")
    password = os.environ.get("GMAIL_APP_PASSWORD")
    if not sender or not password:
        print("[ERROR] GMAIL_USER or GMAIL_APP_PASSWORD not set.")
        return

    total = sum(len(jobs) for jobs in new_jobs_by_company.values())
    subject = f"🎓 {total} New Entry-Level Job{'s' if total > 1 else ''} Found! [{datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}]"

    rows = ""
    for company, jobs in new_jobs_by_company.items():
        for job in jobs:
            title = job["title"]
            tl = title.lower()
            if any(k in tl for k in ["intern", "internship", "co-op"]):
                badge = '<span style="background:#FF6B35;color:white;padding:2px 7px;border-radius:10px;font-size:11px;margin-left:6px">Internship</span>'
            elif any(k in tl for k in ["new grad", "new graduate", "recent grad"]):
                badge = '<span style="background:#28A745;color:white;padding:2px 7px;border-radius:10px;font-size:11px;margin-left:6px">New Grad</span>'
            elif any(k in tl for k in ["junior", "jr.", "entry", "associate"]):
                badge = '<span style="background:#007BFF;color:white;padding:2px 7px;border-radius:10px;font-size:11px;margin-left:6px">Entry Level</span>'
            else:
                badge = '<span style="background:#6C757D;color:white;padding:2px 7px;border-radius:10px;font-size:11px;margin-left:6px">Junior/Assoc</span>'

            rows += f"""
            <tr>
              <td style="padding:10px;border:1px solid #eee;font-weight:bold;color:#1a1a2e">{company}</td>
              <td style="padding:10px;border:1px solid #eee">{title}{badge}</td>
              <td style="padding:10px;border:1px solid #eee;color:#555">{job.get("location","N/A")}</td>
              <td style="padding:10px;border:1px solid #eee">
                <a href="{job["url"]}" style="background:#1F4E79;color:white;padding:6px 14px;border-radius:5px;text-decoration:none;font-size:13px">Apply →</a>
              </td>
            </tr>"""

    html = f"""
    <html><body style="font-family:Arial,sans-serif;max-width:860px;margin:auto;padding:20px;background:#f5f5f5">
      <div style="background:linear-gradient(135deg,#1F4E79,#2E86AB);padding:28px;border-radius:12px;color:white;text-align:center;margin-bottom:20px">
        <h1 style="margin:0;font-size:26px">🎓 Entry-Level Job Alerts</h1>
        <p style="margin:10px 0 4px;font-size:15px">{total} new matching opening{'s' if total > 1 else ''}</p>
        <p style="margin:0;opacity:0.75;font-size:12px">Internships · New Grad · Junior · Associate · 0–3 yrs exp</p>
      </div>
      <div style="background:white;border-radius:10px;padding:20px;box-shadow:0 2px 8px rgba(0,0,0,0.07)">
        <table style="width:100%;border-collapse:collapse">
          <thead>
            <tr style="background:#1F4E79;color:white">
              <th style="padding:12px;border:1px solid #ddd;text-align:left">Company</th>
              <th style="padding:12px;border:1px solid #ddd;text-align:left">Job Title</th>
              <th style="padding:12px;border:1px solid #ddd;text-align:left">Location</th>
              <th style="padding:12px;border:1px solid #ddd;text-align:left">Link</th>
            </tr>
          </thead>
          <tbody>{rows}</tbody>
        </table>
      </div>
      <p style="color:#aaa;font-size:11px;text-align:center;margin-top:14px">
        Checked {datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")} · Job Tracker Bot · Entry-level filter active
      </p>
    </body></html>"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = NOTIFY_EMAIL
    msg.attach(MIMEText(html, "html"))
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender, password)
            server.sendmail(sender, NOTIFY_EMAIL, msg.as_string())
        print(f"[EMAIL] Sent {total} entry-level job alert(s) to {NOTIFY_EMAIL}")
    except Exception as e:
        print(f"[ERROR] Failed to send email: {e}")


def main():
    print(f"\n{'='*60}")
    print(f"Job Tracker Run: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"Filter: Internships / New Grad / Junior / 0-3 yrs exp")
    print(f"{'='*60}")

    seen = load_seen_jobs()
    new_jobs_by_company = {}
    total_fetched = 0
    total_passed = 0

    for company in COMPANIES:
        print(f"\nChecking: {company['name']} ({company['ats'].upper()})")
        jobs = fetch_jobs(company)
        print(f"  Found {len(jobs)} total postings")
        total_fetched += len(jobs)

        for job in jobs:
            qualifies, reason = is_entry_level(job)
            if not qualifies:
                continue
            total_passed += 1
            job_id = make_job_id(company["name"], job["title"], job.get("url", ""))
            if job_id not in seen:
                seen[job_id] = {
                    "company": company["name"],
                    "title": job["title"],
                    "url": job.get("url", ""),
                    "location": job.get("location", ""),
                    "filter_reason": reason,
                    "first_seen": datetime.utcnow().isoformat(),
                }
                if company["name"] not in new_jobs_by_company:
                    new_jobs_by_company[company["name"]] = []
                new_jobs_by_company[company["name"]].append(job)
                print(f"  [NEW] {job['title']}  ← {reason}")

        time.sleep(0.5)

    save_seen_jobs(seen)

    print(f"\n{'='*60}")
    print(f"Total fetched: {total_fetched} | Passed filter: {total_passed}")

    if new_jobs_by_company:
        total_new = sum(len(j) for j in new_jobs_by_company.values())
        print(f"[SUMMARY] {total_new} new entry-level job(s). Sending email...")
        send_email(new_jobs_by_company)
    else:
        print("[SUMMARY] No new entry-level jobs found this run.")

    print(f"Done. Total tracked jobs: {len(seen)}")


if __name__ == "__main__":
    main()
