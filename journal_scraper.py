#!/usr/bin/env python3
"""
Journal Metadata Scraper
Fetches paper metadata (title, abstract, authors, year, DOI, etc.)
from academic journals using the CrossRef and Semantic Scholar APIs.

Usage:
    python journal_scraper.py
    python journal_scraper.py --journal "American Political Science Review" --issues 4
    python journal_scraper.py --journal "Nature" --issues 2 --output nature_papers.csv
"""

import argparse
import csv
import json
import sys
import time
from datetime import datetime
from typing import Optional
import urllib.request
import urllib.parse
import urllib.error


# ─── HTTP helpers ────────────────────────────────────────────────────────────

def _get_json(url: str, retries: int = 3, pause: float = 1.5) -> Optional[dict]:
    """GET a URL and return parsed JSON, with simple retry logic."""
    headers = {
        "User-Agent": "JournalScraper/1.0 (mailto:user@example.com)",
        "Accept": "application/json",
    }
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = (attempt + 1) * 5
                print(f"  Rate-limited. Waiting {wait}s …", file=sys.stderr)
                time.sleep(wait)
            elif e.code == 404:
                return None
            else:
                print(f"  HTTP {e.code} on {url}", file=sys.stderr)
        except Exception as exc:
            print(f"  Request error ({exc}) – retry {attempt+1}/{retries}", file=sys.stderr)
        time.sleep(pause)
    return None


# ─── CrossRef helpers ─────────────────────────────────────────────────────────

CROSSREF_BASE = "https://api.crossref.org"

def search_journal(name: str) -> Optional[dict]:
    """Return the best-matching journal record from CrossRef."""
    q = urllib.parse.quote(name)
    url = f"{CROSSREF_BASE}/journals?query={q}&rows=5"
    data = _get_json(url)
    if not data:
        return None
    items = data.get("message", {}).get("items", [])
    if not items:
        return None
    # Pick the item whose title is closest to the query (case-insensitive)
    name_lower = name.lower()
    for item in items:
        if item.get("title", "").lower() == name_lower:
            return item
    return items[0]   # fall back to first result


def get_journal_works(issn: str, rows_per_page: int = 100, max_rows: int = 2000) -> list:
    """Fetch all works for a journal ISSN, sorted newest-first."""
    all_works = []
    offset = 0
    while offset < max_rows:
        url = (
            f"{CROSSREF_BASE}/journals/{issn}/works"
            f"?rows={rows_per_page}&offset={offset}"
            f"&sort=published&order=desc"
            f"&select=DOI,title,abstract,author,published-print,published-online,"
            f"volume,issue,page,container-title,URL,type"
        )
        data = _get_json(url)
        if not data:
            break
        items = data.get("message", {}).get("items", [])
        if not items:
            break
        all_works.extend(items)
        offset += len(items)
        if len(items) < rows_per_page:
            break
        time.sleep(0.5)   # be polite to CrossRef
    return all_works


# ─── Issue grouping ───────────────────────────────────────────────────────────

def _pub_date(work: dict) -> tuple:
    """Return (year, volume_str, issue_str) for sorting / grouping."""
    for key in ("published-print", "published-online", "published"):
        dp = work.get(key, {}).get("date-parts", [[]])
        if dp and dp[0]:
            year = dp[0][0] if len(dp[0]) > 0 else 0
            return (year, str(work.get("volume", "")), str(work.get("issue", "")))
    return (0, "", "")


def group_by_issue(works: list) -> dict:
    """Group works into {(year, volume, issue): [works]} dict."""
    groups: dict = {}
    for w in works:
        key = _pub_date(w)
        groups.setdefault(key, []).append(w)
    return groups


def select_recent_issues(works: list, n_issues: int) -> list:
    """Return the works belonging to the N most recent distinct issues."""
    groups = group_by_issue(works)
    # Sort keys newest-first: by year desc, then volume desc, then issue desc
    def sort_key(k):
        year, vol, iss = k
        try:
            vol_n = float(vol) if vol else 0
        except ValueError:
            vol_n = 0
        try:
            iss_n = float(iss) if iss else 0
        except ValueError:
            iss_n = 0
        return (year, vol_n, iss_n)

    sorted_keys = sorted(groups.keys(), key=sort_key, reverse=True)
    selected_keys = sorted_keys[:n_issues]
    selected = []
    for k in selected_keys:
        selected.extend(groups[k])
    return selected


# ─── Semantic Scholar enrichment ──────────────────────────────────────────────

SS_BASE = "https://api.semanticscholar.org/graph/v1"

def fetch_abstract_from_ss(doi: str) -> Optional[str]:
    """Try to get an abstract from Semantic Scholar by DOI."""
    encoded = urllib.parse.quote(f"DOI:{doi}", safe="")
    url = f"{SS_BASE}/paper/{encoded}?fields=abstract"
    data = _get_json(url, retries=2, pause=1.0)
    if data:
        return data.get("abstract")
    return None


# ─── Metadata extraction ──────────────────────────────────────────────────────

def _clean_abstract(raw: Optional[str]) -> str:
    if not raw:
        return ""
    # CrossRef sometimes returns JATS XML snippets — strip common tags
    import re
    text = re.sub(r"<[^>]+>", " ", raw)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_metadata(work: dict, enrich_abstract: bool = True) -> dict:
    """Convert a CrossRef work dict to a flat metadata dict."""
    # Title
    titles = work.get("title", [])
    title = titles[0] if titles else ""

    # Authors
    authors_raw = work.get("author", [])
    authors = "; ".join(
        f"{a.get('given', '')} {a.get('family', '')}".strip()
        for a in authors_raw
    )

    # Year
    year = ""
    for key in ("published-print", "published-online", "published"):
        dp = work.get(key, {}).get("date-parts", [[]])
        if dp and dp[0]:
            year = str(dp[0][0])
            break

    # Volume / issue / pages
    volume = work.get("volume", "")
    issue  = work.get("issue", "")
    pages  = work.get("page", "")

    # DOI / URL
    doi = work.get("DOI", "")
    url = work.get("URL", f"https://doi.org/{doi}" if doi else "")

    # Abstract
    abstract = _clean_abstract(work.get("abstract", ""))
    if not abstract and doi and enrich_abstract:
        abstract = fetch_abstract_from_ss(doi) or ""
        time.sleep(0.3)   # stay within SS rate limits

    # Journal name
    container = work.get("container-title", [])
    journal = container[0] if container else ""

    return {
        "title":    title,
        "authors":  authors,
        "year":     year,
        "journal":  journal,
        "volume":   volume,
        "issue":    issue,
        "pages":    pages,
        "doi":      doi,
        "url":      url,
        "abstract": abstract,
    }


# ─── CSV export ───────────────────────────────────────────────────────────────

FIELDNAMES = ["title", "authors", "year", "journal", "volume", "issue",
              "pages", "doi", "url", "abstract"]

def save_csv(records: list, path: str) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(records)
    print(f"\n✓ Saved {len(records)} records → {path}")


# ─── Main logic ───────────────────────────────────────────────────────────────

def run(journal_name: str, n_issues: Optional[int], output: str,
        no_abstract_enrichment: bool = False) -> None:

    print(f'\n🔍 Searching CrossRef for journal: "{journal_name}" …')
    journal = search_journal(journal_name)
    if not journal:
        sys.exit(f'✗ Could not find journal "{journal_name}" in CrossRef.')

    found_title = journal.get("title", "unknown")
    issns = journal.get("ISSN", [])
    if not issns:
        sys.exit(f'✗ Journal "{found_title}" has no ISSN in CrossRef.')

    issn = issns[0]
    print(f"  Found: {found_title}")
    print(f"  ISSN:  {issn}")

    print(f"\n📥 Fetching works for ISSN {issn} …")
    works = get_journal_works(issn)
    print(f"  Retrieved {len(works)} works total.")

    if not works:
        sys.exit("✗ No works found for this journal.")

    if n_issues:
        print(f"\n📂 Selecting {n_issues} most recent issue(s) …")
        works = select_recent_issues(works, n_issues)
        print(f"  {len(works)} papers in those issue(s).")

    # Filter to only journal articles (skip editorials, errata, etc.)
    articles = [w for w in works if w.get("type") in
                ("journal-article", None, "")]
    if not articles:
        articles = works   # keep everything if type filter removes all

    print(f"\n🧬 Extracting metadata for {len(articles)} articles …")
    if not no_abstract_enrichment:
        print("  (Enriching missing abstracts via Semantic Scholar — may take a moment)")

    records = []
    for i, work in enumerate(articles, 1):
        meta = extract_metadata(work, enrich_abstract=not no_abstract_enrichment)
        records.append(meta)
        if i % 10 == 0 or i == len(articles):
            print(f"  {i}/{len(articles)} done …", end="\r")

    print()
    save_csv(records, output)


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Scrape journal paper metadata into a CSV file."
    )
    parser.add_argument(
        "--journal", "-j",
        help="Journal name, e.g. 'American Political Science Review'",
    )
    parser.add_argument(
        "--issues", "-i",
        type=int,
        default=None,
        help="Number of most-recent issues to retrieve (default: all available)",
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Output CSV file path (default: auto-generated from journal name)",
    )
    parser.add_argument(
        "--no-enrich",
        action="store_true",
        help="Skip Semantic Scholar abstract enrichment (faster, but fewer abstracts)",
    )
    args = parser.parse_args()

    # Interactive prompts if not passed via CLI
    journal_name = args.journal
    if not journal_name:
        journal_name = input("Enter journal name: ").strip()
        if not journal_name:
            sys.exit("No journal name provided.")

    n_issues = args.issues
    if n_issues is None:
        raw = input("Number of recent issues to fetch (press Enter for ALL): ").strip()
        n_issues = int(raw) if raw.isdigit() else None

    output = args.output
    if not output:
        safe = journal_name.lower().replace(" ", "_")[:40]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output = f"{safe}_{timestamp}.csv"

    run(journal_name, n_issues, output, no_abstract_enrichment=args.no_enrich)


if __name__ == "__main__":
    main()
