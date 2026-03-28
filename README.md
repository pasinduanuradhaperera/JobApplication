# Job Application Automation Suite

> **⚠️ Disclaimer**
>
> This tool is built **purely to help the community** — to reduce the frustration of repetitive job application paperwork and let you focus on what actually matters: finding the right role.
>
> **Please use it responsibly:**
> - Every application is reviewed and approved by **you** before anything is sent
> - Do not use this tool to spam recruiters or apply to roles you have no genuine interest in
> - Do not misrepresent your experience or qualifications in generated content — always review and edit drafts to ensure they are accurate and honest
> - Respect the time of hiring managers and recruiters
>
> Automation is a tool, not a shortcut to dishonesty. Use it to work smarter, not to undermine trust in the hiring process.

An AI-powered Python CLI that handles five core modules:

| # | Module | What it does |
|---|--------|--------------|
| 1 | **Fully automated apply** | Reads your CV → generates cover letter + email → sends the email automatically |
| 2 | **Draft only** | Same as #1 but saves drafts without sending |
| 3 | **Job search** | Searches the internet for matching roles → saves to Excel |
| 4 | **Batch apply from Excel (review-first)** | Reads applications from Excel (including CV path per row) → generates drafts one-by-one → user approves before sending |
| 5 | **Recruiter match (CV → ranked jobs)** | Acts like a recruiter: reads your CV → finds and ranks best-fit jobs → writes a new Excel file |

Both modules 1 & 2 log every application to `output/applications.xlsx`.  
Module 3 saves results to `output/job_search.xlsx`.

---

## Setup

### 1. Install Python dependencies

```bash
cd "job application"
pip install -r requirements.txt
```

### 2. Configure credentials

```bash
cp .env.example .env
```

Open `.env` and fill in:

| Variable | Description |
|----------|-------------|
| `DEEPSEEK_API_KEY` | Your DeepSeek API key (OpenAI-compatible endpoint used by this app) |
| `EMAIL_ADDRESS` | Your Gmail address |
| `EMAIL_PASSWORD` | A **Gmail App Password** (not your real password) — [instructions below](#gmail-app-password) |
| `SERPAPI_KEY` | *(Optional)* SerpAPI key for better job search — [serpapi.com](https://serpapi.com) |

> If no `SERPAPI_KEY` is set, the job search falls back to a basic Google web scrape.

### Startup preflight validation

Before running a selected module, the app validates required `.env` values:

- Module 1 (Fully automated apply): requires `DEEPSEEK_API_KEY`, `EMAIL_ADDRESS`, `EMAIL_PASSWORD`
- Module 2 (Draft only): requires `DEEPSEEK_API_KEY`
- Module 3 (Job search): `SERPAPI_KEY` optional (falls back to scraping)
- Module 4 (Batch apply): requires `DEEPSEEK_API_KEY`; warns if email credentials are missing
- Module 5 (Recruiter match): works without `DEEPSEEK_API_KEY` using fallback ranking/query logic

### Gmail App Password

1. Go to [myaccount.google.com/security](https://myaccount.google.com/security)
2. Enable **2-Step Verification** if not already on
3. Search for **"App passwords"** → create one for "Mail"
4. Paste the 16-character password into `EMAIL_PASSWORD`

---

## Run

```bash
python main.py
```

You will see a menu:

```
╔══════════════════════════════════════════════╗
║        Job Application Automation Suite      ║
╠══════════════════════════════════════════════╣
║  1. Fully automated apply (generate + send)  ║
║  2. Draft only (generate, no send)           ║
║  3. Search for jobs                          ║
║  4. Batch apply from Excel (review first)    ║
║  5. Recruiter match (CV → ranked jobs)       ║
║  6. Exit                                     ║
╚══════════════════════════════════════════════╝
```

Tip: At any input prompt, type `help` to view command guidance, type `menu` to return to the main menu, or type `exit` to request program termination. The app will ask for confirmation before quitting.

### Module 1 & 2 flow
1. Drag & drop (or paste the path to) your **CV PDF**
2. Enter **company**, **role**, and any extra context
3. For module 1: enter the **recipient's email address**
4. Review the generated cover letter and email on screen
5. **Regenerate with suggestions** (optional):
   - App asks "Are you happy with these drafts?"
   - If no, ask "Would you like to regenerate?"
   - Option to provide suggestions to improve the next version
   - View regenerated drafts and repeat until satisfied
6. Confirm → cover letter PDF saved to `output/`, application logged to Excel
7. (Module 1 only) Confirm send → email dispatched

### Module 3 flow
1. Enter the **role** you are looking for and optional **location**
2. Choose how many results to fetch
3. Confirm → results saved to `output/job_search.xlsx`

### Module 4 flow (Batch apply from Excel)
1. Use the included template file: `inputs/sample_batch_applications.xlsx`
   - You can upload this template to GitHub as the official sample input file
   - Duplicate it for personal runs, then edit the rows
2. Prepare your Excel file with required columns:
    - `company`
    - `role`
    - `recipient_email`
    - `cv_path`
3. Optional columns:
    - `extras` (any additional context about the application)
    - `status` (auto-filled after first run to track sent/draft/skipped positions)
    - `date_applied` (auto-filled when each row is processed)
4. Run module 4 and provide the Excel path
5. For each new row, the app:
    - Generates cover letter + email
    - Shows preview
    - Asks "Are you happy with these?" (can regenerate with suggestions here)
    - Asks "Send now?" (yes/no/draft)
6. **Smart rerun handling**: On second+ run, app automatically skips rows with Status = Sent/Draft/Skipped
    - You can manually clear Status cells to reprocess those rows
    - Only new rows and cleared rows are processed
7. Status and Date Applied auto-update in your Excel file after each run

### Module 5 flow (Recruiter match)
1. Provide your CV PDF path
2. Optionally provide location + number of ranked jobs
3. App generates role queries from your CV, fetches jobs, and ranks fit score
4. Ranked list saved to `output/cv_best_jobs.xlsx`

---

## Output files

```
output/
├── applications.xlsx        ← all applications (modules 1 & 2)
├── job_search.xlsx          ← job search results (module 3)
├── cv_best_jobs.xlsx        ← ranked best-fit jobs from your CV (module 5)
└── CoverLetter_<Company>_<Role>.pdf
```

---

## Advanced Features

### Regeneration with suggestions (Modules 1, 2, 4)

After cover letter and email are generated, you can:
1. See a preview of both documents
2. Choose "Are you happy with these drafts?" → No
3. Choose "Would you like to regenerate?" → Yes
4. Optionally provide **suggestions** to improve the next version (you can press Enter to skip)
5. The app regenerates both with your feedback incorporated
6. Repeat the approval cycle until satisfied

At **any input prompt** throughout the app, these global commands are available:

| Command | Action |
|---------|--------|
| `help` | Show the help panel with command reference |
| `menu` | Immediately return to the main menu |
| `exit` | Exit the program (asks for confirmation) |

Example feedback you could provide:
- "Make it more technical focused, emphasizing Python and cloud design patterns"
- "Shift focus to leadership and team management experience"
- "Add more energy and enthusiasm to the tone"
- "Keep the technical depth but simplify the first paragraph"

### Batch apply status tracking (Module 4)

The batch apply workflow now tracks which positions you've already applied to:
- **First run**: app processes all rows in your Excel file
- **Second run**: app automatically **skips** rows already marked as Sent/Draft/Skipped
- **To reprocess a row**: manually clear its Status cell and rerun
- Status column auto-updates in your input Excel after each run

This prevents accidental duplicate applications when you rerun the same batch file multiple times.

---

```
job application/
├── main.py              ← CLI entry point
├── requirements.txt
├── .env.example
├── .gitignore
├── inputs/
│   └── sample_batch_applications.xlsx  ← batch apply template file
└── src/
    ├── cv_parser.py     ← extracts text from CV PDF
    ├── generator.py     ← GPT-4o cover letter + email generation + PDF export
    ├── email_sender.py  ← sends email via Gmail SMTP
    ├── tracker.py       ← logs applications and jobs to Excel
    ├── job_search.py    ← searches jobs via SerpAPI or Google scrape
    ├── excel_batch_apply.py  ← module 4 workflow (Excel-driven batch apply)
    └── recruiter_matcher.py  ← module 5 workflow (CV-based recruiter matching)
```
