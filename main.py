"""
main.py — Interactive CLI for the Job Application Automation suite.

Modules:
  1. Fully automated apply  → generate cover letter + email → send
  2. Draft only             → generate cover letter + email → save (no send)
  3. Job search             → search internet → save to Excel
"""

import os
import re
import sys

# Load .env before importing any src module that reads env vars
from dotenv import load_dotenv
load_dotenv()

# Add src/ to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from cv_parser  import extract_cv_text
from generator  import generate_cover_letter, generate_email, save_cover_letter_pdf, regenerate_cover_letter, regenerate_email
from email_sender import send_application_email
from tracker    import log_application, update_application_status, log_job
from job_search import search_jobs
from excel_batch_apply import run_batch_apply_workflow
from recruiter_matcher import find_best_jobs_for_cv, save_ranked_jobs_to_excel

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")


class ExitProgram(Exception):
    """Raised when user confirms they want to leave the program."""


class ReturnToMenu(Exception):
    """Raised when user types 'menu' to go back to the main menu."""


def _missing_env_vars(names: list[str]) -> list[str]:
    """Return env var names that are missing or blank."""
    missing = []
    for name in names:
        if not str(os.environ.get(name, "")).strip():
            missing.append(name)
    return missing


def preflight_for_choice(choice: str) -> bool:
    """Validate required environment variables for each module choice."""
    if choice == "1":
        required = ["DEEPSEEK_API_KEY", "EMAIL_ADDRESS", "EMAIL_PASSWORD"]
        missing = _missing_env_vars(required)
        if missing:
            print("\n  ✗ Missing required .env values for Module 1:")
            for name in missing:
                print(f"    - {name}")
            print("  Please update your .env and try again.")
            return False

    elif choice == "2":
        missing = _missing_env_vars(["DEEPSEEK_API_KEY"])
        if missing:
            print("\n  ✗ Missing required .env value for Module 2:")
            print("    - DEEPSEEK_API_KEY")
            print("  Please update your .env and try again.")
            return False

    elif choice == "3":
        if _missing_env_vars(["SERPAPI_KEY"]):
            print("\n  ! SERPAPI_KEY is not set. Falling back to web scraping mode.")

    elif choice == "4":
        missing = _missing_env_vars(["DEEPSEEK_API_KEY"])
        if missing:
            print("\n  ✗ Missing required .env value for Module 4:")
            print("    - DEEPSEEK_API_KEY")
            print("  Please update your .env and try again.")
            return False
        if _missing_env_vars(["EMAIL_ADDRESS", "EMAIL_PASSWORD"]):
            print("\n  ! EMAIL_ADDRESS / EMAIL_PASSWORD not fully configured.")
            print("  Draft generation will work, but sending emails will fail.")

    elif choice == "5":
        if _missing_env_vars(["DEEPSEEK_API_KEY"]):
            print("\n  ! DEEPSEEK_API_KEY not set. Using fallback recruiter matching logic.")

    return True


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _confirm_exit_program() -> bool:
    """Ask user if they want to exit the program."""
    while True:
        answer = input("Do you want to leave the program? (y/n): ").strip().lower()
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        print("  ✗ Please answer with 'y' or 'n'.")


def _print_help_panel() -> None:
    """Show global help text available from any prompt."""
    print("\n" + "=" * 68)
    print("  Help")
    print("=" * 68)
    print("  Global commands:")
    print("    - help  : show this help panel")
    print("    - menu  : return to the main menu")
    print("    - exit  : request program exit (with confirmation)")
    print("\n  Main menu options:")
    print("    1 - Fully automated apply (generate + send)")
    print("    2 - Draft only (generate, no send)")
    print("    3 - Search for jobs")
    print("    4 - Batch apply from Excel (review first)")
    print("    5 - Recruiter match (CV -> ranked jobs)")
    print("    6 - Exit")
    print("\n  In job search results screen:")
    print("    d <number>  : view job details")
    print("    s <list>    : save selected jobs, example s 1,3,5")
    print("    s all       : save all shown jobs")
    print("    n           : start a new search")
    print("    q           : return to main menu")
    print("=" * 68)


def _read_input(prompt: str) -> str:
    """Read input and handle global 'exit', 'menu', and 'help' commands."""
    while True:
        value = input(prompt)
        normalized = value.strip().lower()
        if normalized == "help":
            _print_help_panel()
            continue
        if normalized == "menu":
            raise ReturnToMenu()
        if normalized == "exit":
            if _confirm_exit_program():
                raise ExitProgram()
            continue
        return value

def ask(prompt: str, default: str = "") -> str:
    """Prompt user for input, returning default if blank."""
    suffix = f" [{default}]" if default else ""
    value = _read_input(f"{prompt}{suffix}: ").strip()
    return value if value else default


def ask_non_empty(prompt: str) -> str:
    """Prompt until user provides a non-empty value."""
    while True:
        value = ask(prompt).strip()
        if value:
            return value
        print("  ✗ This field is required. Please enter a value.")


def ask_int_in_range(prompt: str, default: int, min_value: int, max_value: int) -> int:
    """Prompt for an integer constrained to [min_value, max_value]."""
    while True:
        raw = ask(prompt, str(default))
        try:
            value = int(raw)
        except ValueError:
            print(f"  ✗ Please enter a valid number between {min_value} and {max_value}.")
            continue
        if min_value <= value <= max_value:
            return value
        print(f"  ✗ Number out of range. Allowed: {min_value}–{max_value}.")


def _is_valid_email(email: str) -> bool:
    return bool(EMAIL_RE.match((email or "").strip()))


def ask_email(prompt: str) -> str:
    """Prompt until user provides a valid email address."""
    while True:
        value = ask_non_empty(prompt)
        if _is_valid_email(value):
            return value
        print("  ✗ Invalid email format. Please enter a valid email address.")


def preview(label: str, content: str):
    print(f"\n{'─'*60}")
    print(f"  {label}")
    print('─'*60)
    print(content)
    print('─'*60)


def confirm(prompt: str) -> bool:
    while True:
        answer = _read_input(f"{prompt} (y/n): ").strip().lower()
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        print("  ✗ Please answer with 'y' or 'n'.")


def get_cv_path() -> str:
    while True:
        path = ask_non_empty("Path to your CV PDF (drag & drop the file here)").strip('"').strip("'")
        path = os.path.abspath(os.path.expanduser(path))
        if os.path.isfile(path) and path.lower().endswith(".pdf"):
            return path
        print(f"  ✗ File not found or not a PDF: '{path}'. Please try again.")


def collect_job_details() -> dict:
    print("\n── Job Details ───────────────────────────────────────────")
    company  = ask_non_empty("Company name")
    role     = ask_non_empty("Job title / role")
    extras   = ask("Any extra info for the cover letter? (e.g. referral, specific project)", "")
    return {"company": company, "role": role, "extras": extras}


def get_excel_path(prompt_text: str) -> str:
    while True:
        path = ask_non_empty(prompt_text).strip('"').strip("'")
        path = os.path.abspath(os.path.expanduser(path))
        if os.path.isfile(path) and path.lower().endswith(('.xlsx', '.xlsm', '.xltx', '.xltm')):
            return path
        print(f"  ✗ File not found or not an Excel file: '{path}'. Please try again.")


# ─── Module 1 & 2 shared workflow ─────────────────────────────────────────────

def run_application(send_email: bool):
    """Shared flow for Module 1 (send) and Module 2 (draft only)."""
    print("\n=== Step 1: Upload your CV ===")
    cv_path  = get_cv_path()
    cv_text  = extract_cv_text(cv_path)
    print("  ✓ CV parsed successfully.")

    details  = collect_job_details()
    company  = details["company"]
    role     = details["role"]
    extras   = details["extras"]

    recipient = ""
    if send_email:
        recipient = ask_email("Recipient email address (HR / hiring manager)")

    print("\n  Generating cover letter …")
    cover_letter = generate_cover_letter(cv_text, company, role, extras)

    print("  Generating email …")
    email_data   = generate_email(cv_text, company, role, cover_letter)

    # ── Preview & Regeneration Loop ──
    while True:
        preview("COVER LETTER", cover_letter)
        preview(f"EMAIL SUBJECT: {email_data['subject']}\n\n  EMAIL BODY", email_data["body"])

        if confirm("\nAre you happy with these drafts?"):
            break

        if not confirm("Would you like to regenerate them?"):
            print("  Application cancelled. Nothing was saved.")
            return

        use_feedback = confirm("Provide suggestions to improve the regeneration?")
        feedback = ""
        if use_feedback:
            feedback = ask("Your suggestions (or press Enter for generic regeneration)", "")

        print("  Regenerating cover letter …")
        cover_letter = regenerate_cover_letter(cv_text, company, role, extras, feedback)

        print("  Regenerating email …")
        email_data = regenerate_email(cv_text, company, role, cover_letter, feedback)
        print("  ✓ Regenerated.")

    # ── Save PDF ──
    safe_name   = f"{company}_{role}".replace(" ", "_").replace("/", "-")
    pdf_path    = os.path.join(OUTPUT_DIR, f"CoverLetter_{safe_name}.pdf")
    save_cover_letter_pdf(cover_letter, pdf_path)
    print(f"  ✓ Cover letter saved → {pdf_path}")

    status = "Draft"
    notes = ""

    # ── Send ──
    if send_email:
        if confirm(f"Send email to {recipient}?"):
            try:
                send_application_email(
                    to_address=recipient,
                    subject=email_data["subject"],
                    body=email_data["body"],
                    cover_letter_pdf_path=pdf_path,
                    cv_path=cv_path,
                )
                status = "Sent"
                print("  ✓ Email sent!")
            except Exception as e:
                notes = f"Send failed: {e}"
                print(f"  ✗ Email send failed, kept as Draft: {e}")
        else:
            print("  Email not sent. Status logged as Draft.")

    # ── Log to Excel ──
    log_application(
        company=company,
        role=role,
        recipient_email=recipient,
        cover_letter_pdf=pdf_path,
        email_subject=email_data["subject"],
        email_body=email_data["body"],
        status=status,
        notes=notes,
    )
    print(f"  ✓ Application logged to Excel (status: {status})")


# ─── Module 3 ─────────────────────────────────────────────────────────────────

def _print_job_table(jobs: list):
    """Print a numbered, formatted table of jobs."""
    col_t = 35  # title
    col_c = 26  # company
    col_l = 20  # location
    col_e =  8  # exp
    col_s = 10  # source
    sep    = f"  {'─'*4}  {'─'*col_t}  {'─'*col_c}  {'─'*col_l}  {'─'*col_e}  {'─'*col_s}"
    header = f"  {'#':>3}   {'Title':<{col_t}}  {'Company':<{col_c}}  {'Location':<{col_l}}  {'Min Exp':<{col_e}}  {'Source':<{col_s}}"
    print(f"\n{header}")
    print(sep)
    for i, job in enumerate(jobs, 1):
        title   = (job["title"]          or "—")[:col_t]
        company = (job["company"]        or "—")[:col_c]
        loc     = (job["location"]       or "—")[:col_l]
        exp     = (job.get("exp", "")    or "—")[:col_e]
        source  = (job["source"]         or "—")[:col_s]
        print(f"  {i:>3}.  {title:<{col_t}}  {company:<{col_c}}  {loc:<{col_l}}  {exp:<{col_e}}  {source:<{col_s}}")
    print()


def _print_job_detail(i: int, job: dict):
    print(f"\n{'─'*60}")
    print(f"  #{i}  {job['title']}")
    print(f"  Company  : {job['company']  or '—'}")
    print(f"  Location : {job['location'] or '—'}")
    print(f"  Min Exp  : {job.get('exp', '—') or '—'}")
    print(f"  Source   : {job['source']   or '—'}")
    print(f"  URL      : {job['url']      or '—'}")
    if job.get("snippet"):
        print(f"\n  Description:\n  {job['snippet']}")
    print('─'*60)


def run_job_search():
    print("\n╔══════════════════════════════════════════════╗")
    print("║              Job Search                      ║")
    print("╚══════════════════════════════════════════════╝")

    while True:
        query    = ask_non_empty("\n  Role / keywords  (e.g. 'Python developer')")
        location = ask("  Location         (leave blank for remote/worldwide)", "")
        num = ask_int_in_range("  Number of results", 20, 1, 100)

        print(f"\n  Searching for \"{query}\" {('in ' + location) if location else '(worldwide)'} …")
        try:
            jobs = search_jobs(query, location, num)
        except Exception as e:
            print(f"\n  Search failed: {e}")
            if not confirm("  Try again?"):
                return
            continue

        if not jobs:
            print("\n  No results found. Try different keywords or location.")
            if not confirm("  Search again?"):
                return
            continue

        print(f"\n  Found {len(jobs)} jobs:")
        _print_job_table(jobs)

        # ── Post-search action loop ──
        while True:
            print("  Options:")
            print("    d <number>   — view details  (e.g. d 3)")
            print("    s <numbers>  — save to Excel (e.g. s 1,3,5  or  s all)")
            print("    n            — new search")
            print("    q            — back to main menu")
            action = _read_input("\n  Your choice: ").strip().lower()

            if action == "q":
                return

            elif action == "n":
                break  # break inner loop → outer loop runs new search

            elif action.startswith("d "):
                try:
                    idx = int(action[2:].strip())
                    if 1 <= idx <= len(jobs):
                        _print_job_detail(idx, jobs[idx - 1])
                    else:
                        print(f"  Please enter a number between 1 and {len(jobs)}.")
                except ValueError:
                    print("  Invalid input. Example: d 3")

            elif action.startswith("s "):
                selection = action[2:].strip()
                to_save: list[dict] = []
                if selection == "all":
                    to_save = jobs
                else:
                    try:
                        indices = [int(x.strip()) for x in selection.split(",")]
                        invalid = [i for i in indices if not (1 <= i <= len(jobs))]
                        if invalid:
                            print(f"  Invalid numbers: {invalid}. Use 1–{len(jobs)}.")
                            continue
                        to_save = [jobs[i - 1] for i in indices]
                    except ValueError:
                        print("  Invalid input. Example: s 1,3,5  or  s all")
                        continue

                for job in to_save:
                    log_job(
                        title=job["title"],
                        company=job["company"],
                        location=job["location"],
                        url=job["url"],
                        snippet=job["snippet"],
                        source=job["source"],
                    )
                print(f"  ✓ {len(to_save)} job(s) saved to output/job_search.xlsx")

            else:
                print("  Unknown option. Use d <n>, s <n>, n, or q.")


# ─── Module 4 ─────────────────────────────────────────────────────────────────

def run_batch_apply_from_excel():
    print("\n╔══════════════════════════════════════════════╗")
    print("║     Batch Apply from Excel (Review Mode)    ║")
    print("╚══════════════════════════════════════════════╝")
    print("\n  Required Excel columns:")
    print("    - company")
    print("    - role")
    print("    - recipient_email")
    print("    - cv_path")
    print("  Optional:")
    print("    - extras")

    excel_path = get_excel_path("\nPath to your batch Excel file")
    try:
        run_batch_apply_workflow(
            excel_path=excel_path,
            output_dir=OUTPUT_DIR,
            confirm_fn=confirm,
            preview_fn=preview,
            ask_fn=ask,
        )
    except ValueError as e:
        print("\n  Batch setup issue:")
        print(f"  {e}")
        print("\n  Tip: Open your Excel file and fix the headers, then run module 4 again.")
    except Exception as e:
        print(f"\n  Batch run failed due to an unexpected error: {e}")


# ─── Module 5 ─────────────────────────────────────────────────────────────────

def run_recruiter_matcher():
    print("\n╔══════════════════════════════════════════════╗")
    print("║      Recruiter Match (CV → Best Jobs)       ║")
    print("╚══════════════════════════════════════════════╝")

    cv_path = get_cv_path()
    location = ask("Target location (blank = worldwide/remote)", "")
    max_results_int = ask_int_in_range("How many ranked jobs to save", 25, 5, 100)

    try:
        print("\n  Parsing CV ...")
        cv_text = extract_cv_text(cv_path)
        print("  Finding and ranking best-fit jobs ...")
        ranked_jobs, queries = find_best_jobs_for_cv(cv_text, location, max_results_int)
    except Exception as e:
        print(f"  Recruiter match failed: {e}")
        return

    if not ranked_jobs:
        print("  No suitable jobs found right now. Try again with a different location.")
        return

    print("\n  Suggested search queries from your CV:")
    for i, q in enumerate(queries, start=1):
        print(f"    {i}. {q}")

    top_preview = min(5, len(ranked_jobs))
    print(f"\n  Top {top_preview} matches:")
    for i, job in enumerate(ranked_jobs[:top_preview], start=1):
        print(f"    {i}. [{job.get('score', '0')}] {job.get('title', '—')} @ {job.get('company', '—')} ({job.get('location', '—')})")

    output_path = os.path.join(OUTPUT_DIR, "cv_best_jobs.xlsx")
    save_ranked_jobs_to_excel(ranked_jobs, output_path)
    print(f"\n  ✓ Ranked jobs saved to: {output_path}")


# ─── Menu ─────────────────────────────────────────────────────────────────────

MENU = """
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
"""

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    valid_choices = {"1", "2", "3", "4", "5", "6"}
    try:
        while True:
            print(MENU)
            choice = ask("Choose an option", "6")
            if choice not in valid_choices:
                print("  Invalid choice, please enter 1–6.")
                continue

            if choice != "6" and not preflight_for_choice(choice):
                continue

            if choice == "1":
                try:
                    run_application(send_email=True)
                except ReturnToMenu:
                    print("  Returning to main menu...")
            elif choice == "2":
                try:
                    run_application(send_email=False)
                except ReturnToMenu:
                    print("  Returning to main menu...")
            elif choice == "3":
                try:
                    run_job_search()
                except ReturnToMenu:
                    print("  Returning to main menu...")
            elif choice == "4":
                try:
                    run_batch_apply_from_excel()
                except ReturnToMenu:
                    print("  Returning to main menu...")
            elif choice == "5":
                try:
                    run_recruiter_matcher()
                except ReturnToMenu:
                    print("  Returning to main menu...")
            elif choice == "6":
                print("Goodbye!")
                break
    except ExitProgram:
        print("Goodbye!")


if __name__ == "__main__":
    main()
