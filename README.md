```markdown
# 📄 Journal Metadata Scraper

[![Python 3.6+](https://img.shields.io/badge/python-3.6+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CrossRef API](https://img.shields.io/badge/API-Crossref-orange)](https://www.crossref.org/documentation/retrieve-metadata/rest-api/)
[![Semantic Scholar](https://img.shields.io/badge/API-Semantic%20Scholar-blue)](https://www.semanticscholar.org/product/api)

A lightweight, **zero‑dependency** Python script that scrapes academic paper metadata from journals using the **CrossRef REST API** and optionally enriches abstracts via the **Semantic Scholar API**.

## ✨ Features

- 🔍 **Search any journal** by name (auto‑resolves ISSN)
- 📚 **Fetch papers** from the most recent N issues – or all issues
- 📝 **Extract complete metadata**:
  - Title, authors (formatted), year, journal name
  - Volume, issue, page range, DOI, direct URL
  - Abstract (plain text, cleaned from XML)
- ⚡ **Abstract enrichment** – fills missing abstracts using Semantic Scholar
- 📁 **Clean CSV export** with UTF‑8 encoding (ready for Excel, R, pandas)
- 🛡️ **Polite API usage** – built‑in delays, automatic retries on rate limits
- 🧪 **No external libraries** – uses only Python standard library (`urllib`, `json`, `csv`, etc.)

## 📦 Requirements

- **Python 3.6 or higher** (tested on 3.6–3.12)
- Internet connection (to call CrossRef and Semantic Scholar APIs)
- No `pip install` needed – pure standard library

## 🚀 Quick Start

### 1. Download the script

```bash
curl -O https://raw.githubusercontent.com/yourusername/journal-scraper/main/journal_scraper.py
```

Or download manually from the [Releases](https://github.com/yourusername/journal-scraper/releases) page.

### 2. Run it

```bash
python journal_scraper.py
```

The script will prompt you for:
- Journal name (e.g., `Nature`)
- Number of recent issues to fetch (press Enter for all)
- Output filename (auto‑generated if you skip)

Or use command‑line arguments:

```bash
python journal_scraper.py --journal "American Political Science Review" --issues 4 --output apsr_papers.csv
```

## 🧭 Command‑Line Interface (CLI)

| Argument | Short | Description |
|----------|-------|-------------|
| `--journal` | `-j` | Full journal name (e.g. `"The Lancet"`) |
| `--issues` | `-i` | Number of most‑recent issues to fetch (default: all) |
| `--output` | `-o` | Output CSV file path (default: `journalname_timestamp.csv`) |
| `--no-enrich` | – | Skip Semantic Scholar abstract enrichment (faster, but may leave abstracts blank) |

### Example commands

```bash
# Fetch everything available for "Science"
python journal_scraper.py -j "Science"

# Fetch 2 latest issues of "Nature", custom output name
python journal_scraper.py --journal Nature --issues 2 --output nature_recent.csv

# Disable abstract enrichment for bulk runs (much faster)
python journal_scraper.py --journal "PLOS ONE" --issues 1 --no-enrich
```

## 📁 Output Format (CSV)

The generated CSV contains the following columns:

| Column     | Description                                                                 | Example                                      |
|------------|-----------------------------------------------------------------------------|----------------------------------------------|
| `title`    | Full paper title                                                            | *"Deep learning for climate modelling"*      |
| `authors`  | Semicolon‑separated list: `Given Family`                                    | `John Smith; Jane Doe`                       |
| `year`     | Publication year (from the earliest date‑part)                              | `2023`                                       |
| `journal`  | Journal name (as returned by CrossRef)                                      | `Nature`                                     |
| `volume`   | Volume number (string, may contain letters)                                | `15` or `S1`                                 |
| `issue`    | Issue number                                                                | `3`                                          |
| `pages`    | Page range (e.g. `123-130`) or article number                               | `e10045`                                     |
| `doi`      | Digital Object Identifier (lowercase, no prefix)                            | `10.1038/s41586-023-00000-0`                 |
| `url`      | Full DOI link or CrossRef URL                                               | `https://doi.org/10.1038/...`                |
| `abstract` | Plain‑text abstract (cleaned from XML tags). Empty if not available.        | *"We present a novel method …"*               |

## ⚙️ How It Works (Detailed)

### Step 1 – Journal Resolution
- The script queries the CrossRef `/journals` endpoint with your journal name.
- It selects the best match (exact title match if possible, otherwise first result).
- Extracts the **ISSN** (print or online) – required for the next step.

### Step 2 – Fetch All Works
- Using the ISSN, it calls `/journals/{issn}/works` with pagination (100 items per request).
- Results are sorted newest‑first by publication date.
- Up to 2000 works are retrieved (this can be adjusted in the code).

### Step 3 – Issue Grouping & Selection
- Each work is assigned a key: `(year, volume, issue)`.
- The script groups works by that key and sorts the groups descending (newest year, then volume, then issue).
- If you specify `--issues N`, only papers from the **N most recent distinct issues** are kept.

### Step 4 – Metadata Extraction
- Title, authors, year, volume, issue, pages, DOI, and URL are extracted directly from the CrossRef record.
- **Abstract cleaning**: CrossRef sometimes returns JATS XML (e.g. `<jats:p>...</jats:p>`). The script strips all XML tags and normalises whitespace.

### Step 5 – Abstract Enrichment (optional)
- If the cleaned abstract is empty **and** you did not use `--no-enrich`, the script tries to fetch it from Semantic Scholar using the DOI.
- Request: `GET https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}?fields=abstract`
- A 0.3‑second delay is added between enrichment requests to respect Semantic Scholar’s rate limits.

### Step 6 – CSV Export
- All records are written to a UTF‑8 encoded CSV file.
- Fields with commas or newlines are automatically quoted.

## ⏱️ Rate Limiting & Politeness

The script is designed to be a **good citizen** of academic APIs:

| API               | Delay between requests | Retries on 429 (Too Many Requests) |
|-------------------|------------------------|------------------------------------|
| CrossRef          | 0.5 seconds            | 3 retries, increasing waits (5, 10, 15 sec) |
| Semantic Scholar  | 0.3 seconds (per enrichment) | 2 retries, 1‑second base pause |

- If you run the script on a large journal (e.g., *Nature* with >50,000 papers), consider using `--issues` to limit the scope.
- For bulk metadata dumps, the `--no-enrich` flag removes Semantic Scholar calls entirely.

## 🐛 Troubleshooting

| Problem                                      | Likely cause & solution                                                                 |
|----------------------------------------------|------------------------------------------------------------------------------------------|
| `✗ Could not find journal "X" in CrossRef` | Journal name might be slightly different. Try the official title (e.g. *"The New England Journal of Medicine"*). |
| Empty CSV or very few papers                 | The journal may not expose its works via CrossRef, or the ISSN is missing. Try another journal. |
| No abstracts even with enrichment            | Semantic Scholar may not have indexed that paper. You can manually check: `https://www.semanticscholar.org/paper/DOI` |
| `HTTP 403 Forbidden`                         | Your IP might be blocked. Add a polite `User-Agent` with your email (already included – change it in the script). |
| `SSL: CERTIFICATE_VERIFY_FAILED`             | Older Python versions may lack root certificates. Update Python or run with `certifi` (but that would add a dependency). |

## 🔧 Customisation (for advanced users)

Edit the script directly to change:

- **Maximum number of works** – adjust `max_rows` in `get_journal_works()` (default 2000).
- **Rows per page** – change `rows_per_page` (higher values are more efficient but may cause timeouts).
- **User‑Agent** – replace `mailto:user@example.com` with your email to help API providers contact you.
- **Timeouts & retries** – modify `pause` and `retries` in `_get_json()`.

## 📄 License

MIT License – you are free to use, modify, and distribute this software. See the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

- Keep the script **dependency‑free** (standard library only) unless absolutely necessary.
- Maintain the existing coding style (functions, type hints, docstrings).
- Add tests if you change critical logic (test with a few known journals).
- Open an issue first to discuss major changes.

### Development setup

```bash
git clone https://github.com/yourusername/journal-scraper
cd journal-scraper
# No pip install -r requirements.txt – it's empty!
```

## 📚 Acknowledgements

- [CrossRef](https://www.crossref.org/) for providing the metadata REST API.
- [Semantic Scholar](https://www.semanticscholar.org/) for the abstract enrichment endpoint.
- All academic publishers who make metadata openly available.

## ❓ FAQ

**Q: Can I extract full text (PDF)?**  
A: No – this script only fetches metadata (title, abstract, etc.). Accessing full texts would require publisher permissions or open‑access agreements.

**Q: Will this work for preprint servers like arXiv or bioRxiv?**  
A: CrossRef primarily indexes journals. For preprints, consider using dedicated APIs (e.g., arXiv API). That said, some preprint servers have CrossRef DOIs – they will appear as type `posted-content`.

**Q: How long does the script take?**  
A: For a typical journal with 500 articles, about 1‑2 minutes (including enrichment). Disable enrichment (`--no-enrich`) to cut time by ~70%.

**Q: I got a 429 error even after retries**  
A: CrossRef rate limits are per IP. If you are on a shared network (university, VPN), wait a few minutes and try again. For large bulk downloads, contact CrossRef for a polite pool.

**Q: Can I use this in a Jupyter notebook?**  
A: Yes – copy the functions into a notebook cell, or run the script via `!python journal_scraper.py`.

**Q: What if a paper has no DOI?**  
A: Some older journals may not have DOIs for all papers. The script will still include the paper with an empty `doi` field.

## 📬 Contact

For issues, feature requests, or questions, please [open an issue](https://github.com/yourusername/journal-scraper/issues) on GitHub.

---

**Happy scraping!** If you use this script for a research project, a citation or star on GitHub is appreciated ⭐
```
