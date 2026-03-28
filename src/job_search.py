"""
job_search.py — Searches for job listings from Indeed and LinkedIn.
Uses SerpAPI (Google Jobs) if a key is configured, otherwise scrapes directly.
"""

import os
import re
import requests
from bs4 import BeautifulSoup

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# Patterns like "2+ years", "3-5 years", "minimum 2 years", "at least 4 years"
_EXP_RE = re.compile(
    r"(?:minimum\s+of\s+|minimum\s+|at\s+least\s+)?"
    r"(\d+)\s*(?:\+|\-\s*\d+)?\s*(?:\+)?\s*year",
    re.IGNORECASE,
)


def extract_experience(text: str) -> int | None:
    """Return minimum years of experience mentioned in text, else None."""
    matches = _EXP_RE.findall(text or "")
    years = [int(m) for m in matches if m.isdigit()]
    if not years:
        return None
    return min(years)


def _fmt_exp(text: str) -> str:
    """Return a display string like '2+ yrs' or '—'."""
    val = extract_experience(text)
    return f"{val}+ yrs" if val is not None else "—"


# ─── SerpAPI ──────────────────────────────────────────────────────────────────

def _search_serpapi(query: str, location: str, num: int) -> list[dict]:
    api_key = os.environ.get("SERPAPI_KEY", "")
    if not api_key:
        raise EnvironmentError("no key")

    params = {
        "engine": "google_jobs",
        "q": f"{query} {location}".strip(),
        "api_key": api_key,
        "num": num,
        "hl": "en",
    }
    resp = requests.get("https://serpapi.com/search", params=params, timeout=15)
    resp.raise_for_status()
    jobs = []
    for item in resp.json().get("jobs_results", []):
        jobs.append({
            "title":    item.get("title", ""),
            "company":  item.get("company_name", ""),
            "location": item.get("location", ""),
            "url":      item.get("share_link") or "",
            "snippet":  item.get("description", "")[:500],
            "source":   "Google Jobs",
            "exp":      _fmt_exp(item.get("description", "")),
        })
    return jobs


# ─── Indeed scrape ────────────────────────────────────────────────────────────

def _search_indeed(query: str, location: str, num: int) -> list[dict]:
    q   = requests.utils.quote(query)
    loc = requests.utils.quote(location)
    url = f"https://www.indeed.com/jobs?q={q}&l={loc}&limit={min(num, 50)}"

    resp = requests.get(url, headers=_HEADERS, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")

    jobs = []
    for card in soup.select("div.job_seen_beacon, div.jobsearch-SerpJobCard"):
        title_el   = card.select_one("h2.jobTitle span, a.jobtitle")
        company_el = card.select_one("span.companyName, span.company")
        loc_el     = card.select_one("div.companyLocation, span.location")
        snippet_el = card.select_one("div.job-snippet, div.summary")
        link_el    = card.select_one("a[id^='job_'], a.jobtitle")

        title   = title_el.get_text(strip=True)   if title_el   else ""
        company = company_el.get_text(strip=True) if company_el else ""
        loc_txt = loc_el.get_text(strip=True)     if loc_el     else location
        snippet = snippet_el.get_text(strip=True) if snippet_el else ""
        href    = link_el.get("href", "")         if link_el    else ""
        full_url = f"https://www.indeed.com{href}" if href.startswith("/") else href

        if title:
            jobs.append({
                "title":    title,
                "company":  company,
                "location": loc_txt,
                "url":      full_url,
                "snippet":  snippet[:500],
                "source":   "Indeed",
                "exp":      _fmt_exp(snippet),
            })
        if len(jobs) >= num:
            break
    return jobs


# ─── LinkedIn scrape ──────────────────────────────────────────────────────────

def _search_linkedin(query: str, location: str, num: int) -> list[dict]:
    q   = requests.utils.quote(query)
    loc = requests.utils.quote(location)
    url = f"https://www.linkedin.com/jobs/search/?keywords={q}&location={loc}&count={min(num, 25)}"

    resp = requests.get(url, headers=_HEADERS, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")

    jobs = []
    for card in soup.select("div.base-card, li.result-card"):
        title_el   = card.select_one("h3.base-search-card__title, span.screen-reader-text")
        company_el = card.select_one("h4.base-search-card__subtitle, a.result-card__subtitle-link")
        loc_el     = card.select_one("span.job-search-card__location, span.job-result-card__location")
        link_el    = card.select_one("a.base-card__full-link, a.result-card__full-card-link")

        title   = title_el.get_text(strip=True)   if title_el   else ""
        company = company_el.get_text(strip=True) if company_el else ""
        loc_txt = loc_el.get_text(strip=True)     if loc_el     else location
        href    = link_el.get("href", "")         if link_el    else ""

        if title:
            jobs.append({
                "title":    title,
                "company":  company,
                "location": loc_txt,
                "url":      href.split("?")[0],
                "snippet":  "",
                "source":   "LinkedIn",
                "exp":      "—",
            })
        if len(jobs) >= num:
            break
    return jobs


# ─── Unified entry point ──────────────────────────────────────────────────────

def search_jobs(query: str, location: str = "", num_results: int = 20) -> list[dict]:
    """
    Try SerpAPI first, then scrape Indeed + LinkedIn in parallel.
    Always returns a combined, deduplicated list.
    """
    # Try SerpAPI
    try:
        results = _search_serpapi(query, location, num_results)
        if results:
            return results
    except Exception:
        pass

    # Scrape Indeed + LinkedIn
    jobs: list[dict] = []
    for scraper in (_search_indeed, _search_linkedin):
        try:
            jobs += scraper(query, location, num_results)
        except Exception:
            pass

    # Deduplicate by title+company
    seen = set()
    unique = []
    for j in jobs:
        key = (j["title"].lower(), j["company"].lower())
        if key not in seen:
            seen.add(key)
            unique.append(j)

    return unique[:num_results]
