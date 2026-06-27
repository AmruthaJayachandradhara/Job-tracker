# 🚀 Job Tracker Bot

Automatically checks **75 startup/tech company** career pages every hour and emails new job postings to `jobnotif27@gmail.com`.

---

## 📋 Companies Tracked

Gumloop, Braintrust, Render, Basis, Emergent, Paraform, Fieldguide, Cape, Kai Security, Zafran, WitnessAI, Zocks, Pomelo Care, Tandem, Doctronic, Northwood Space, Overland AI, Articul8 AI, Freeform, Listen Labs, Spade, Ostro, Hydra Host, BreezeBio, Jump, Eight Sleep, Profound, Encord, Novig, Guidde, UniUni, ORO Labs, Aalyria, Nominal, Nitra, Dwelly, IDfy, Axiamatic, Juicebox, KAST, ChipAgents, Isembard, Mesh Optical Technologies, Salma Health, Databricks, MotherDuck, HashiCorp, Temporal, Fivetran, dbt Labs, ClickUp, Dialpad, Illumio, GitLab, Replit, Tanium, Cursor, Sentry, Vanta, Kong, Hex, Wiz, Anchorage Digital, Coinbase, Mercury, SpotOn, EarnIn, Affirm, Stripe, Gusto, Aptos, Carta, Check, Plaid, Ramp

---

## ⚙️ Setup Instructions

### Step 1: Fork / Push to your GitHub
Push this entire repository to your GitHub account (`AmruthaJayachandradhara`).

### Step 2: Create a Gmail App Password
1. Go to your Google Account → **Security** → **2-Step Verification** (must be ON)
2. Search for **"App passwords"** → Create one for "Mail"
3. Copy the 16-character password (e.g., `abcd efgh ijkl mnop`)

### Step 3: Add GitHub Secrets
In your GitHub repo, go to **Settings → Secrets and variables → Actions → New repository secret**:

| Secret Name | Value |
|---|---|
| `GMAIL_USER` | Your Gmail address (e.g., `yourname@gmail.com`) |
| `GMAIL_APP_PASSWORD` | The 16-char app password from Step 2 |

### Step 4: Enable GitHub Actions
- Go to the **Actions** tab in your repo
- Click **"I understand my workflows, go ahead and enable them"**
- The workflow will now run **every hour automatically**

### Step 5: Test Manually
- Go to **Actions → Job Tracker - Hourly Check → Run workflow**
- Check your email at `jobnotif27@gmail.com`

---

## 🔧 How It Works

```
Every Hour (GitHub Actions)
    │
    ├── Fetches jobs via Ashby API (for Ashby-hosted companies)
    ├── Fetches jobs via Greenhouse API (for Greenhouse-hosted companies)
    └── Scrapes HTML (for other sites)
         │
         ├── Compares with seen_jobs.json (stored in repo)
         ├── If NEW jobs found → sends HTML email to jobnotif27@gmail.com
         └── Updates seen_jobs.json and commits back to repo
```

## 📁 File Structure

```
job-tracker/
├── .github/
│   └── workflows/
│       └── job_tracker.yml      ← GitHub Actions schedule
├── scripts/
│   └── check_jobs.py            ← Main job checking logic
├── seen_jobs.json               ← Auto-generated, tracks seen jobs
├── requirements.txt
└── README.md
```

## ➕ Adding More Companies

Edit `scripts/check_jobs.py` and add to the `COMPANIES` list:
```python
{"name": "Company Name", "url": "https://job-boards.greenhouse.io/companyslug", "ats": "greenhouse"},
# or
{"name": "Company Name", "url": "https://jobs.ashbyhq.com/companyslug", "ats": "ashby"},
```

---

*Built using Python + GitHub Actions*
