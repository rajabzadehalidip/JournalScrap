# 📄 Journal Metadata Scraper

Fetches paper metadata (title, abstract, authors, year, DOI, etc.) from academic journals using the **CrossRef** and **Semantic Scholar** APIs.

## ✨ Features

- Search for any journal by name
- Retrieve papers from the most recent N issues (or all issues)
- Extract: title, authors, year, journal, volume, issue, pages, DOI, URL, abstract
- Automatically enrich missing abstracts via Semantic Scholar
- Export results to a clean CSV file

## 🚀 Usage

### Basic example

```bash
python journal_scraper.py --journal "Nature" --issues 2
