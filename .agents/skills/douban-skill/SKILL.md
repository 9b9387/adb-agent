---
name: douban-skill
description: "Collect hot, latest books, and book details from Douban using the standalone douban_scraper module."
---

# Douban Skill（豆瓣采集技能）

## Description

A pure, standalone CLI and Python module for collecting book information from Douban (`book.douban.com`). It leverages Crawl4AI to fetch pages and `JsonCssExtractionStrategy` to parse data reliably, bypassing the need for manual HTML scraping or API logic directly in the agent.

## Capabilities

- **热门图书 (Hot Catalog)** — Collect Douban's hot books chart (`https://book.douban.com/chart`) spanning up to 99 pages, returning a structured JSON list of `BookCatalogItem`.
- **新书速递 (Latest Catalog)** — Collect Douban's latest books listing (`https://book.douban.com/latest`) spanning up to 99 pages, returning a structured JSON list of `BookCatalogItem`.
- **详情抓取 (Book Detail)** — Extract comprehensive metadata from a specific book subject URL using the `detail` endpoint. Includes: Title, Rating, Votes, Info (author, publisher, ISBN, etc.), and the full unfolded Introduction/Summary.

## Usage

### As a Python Module

You can import and call the pure core logic directly in agent code without relying on any external tools state:

```python
from douban_scraper.core import collect_hot_catalog, collect_latest_catalog, collect_book_detail

# Fetch hot books (default 99 pages max, breaks when encountering an empty page)
hot_results = collect_hot_catalog()

# Fetch latest books
latest_results = collect_latest_catalog()

# Fetch specific book details
detail = collect_book_detail("https://book.douban.com/subject/37930972/")
```

### As a CLI Tool

The tool exposes a Typer CLI bound to `douban-catalog`:

```bash
uv run douban-catalog hot
uv run douban-catalog latest
uv run douban-catalog detail "https://book.douban.com/subject/37930972/"
```

Data is returned in formatted JSON conforming to the Pydantic schemas in `douban_scraper/schemas.py`.

## Directory Structure

The core implementation is centralized in the `douban_scraper/` package:
- `douban_scraper/core.py`: Pure logic for Crawl4AI fetching and CSS strategy extraction. Automatically handles pagination and anti-crawling delays.
- `douban_scraper/schemas.py`: Pydantic models for output (`BookCatalogResult`, `BookCatalogItem`, `BookDetail`).
- `douban_scraper/config.py`: Centralized CSS selectors and HTTP headers (`CATALOG_SCHEMA`, `BOOK_DETAIL_SCHEMA`, etc.).
- `douban_scraper/cli.py`: Typer commands mapping to core routines.

No external files are needed; schemas are defined entirely within the program.

## Triggers

豆瓣, 热门图书, 新书速递, 豆瓣新书, 图书详情, douban_scraper, book chart, book detail, 抓取豆瓣
