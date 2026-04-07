"""Pure core logic for Douban catalog scraper."""

from __future__ import annotations

import os
import random
import re
import sys
import time
from urllib.parse import urljoin

import httpx
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy
from dotenv import load_dotenv

from .config import BOOK_DETAIL_SCHEMA, CATALOG_SCHEMA, DEFAULT_HEADERS, HOT_CATALOG_URL, LATEST_CATALOG_URL
from .schemas import BookCatalogItem, BookCatalogResult, BookDetail

load_dotenv()


def _pick_html_from_crawl4ai_result(raw_result: dict) -> str:
    """Extract and prioritize html content from crawl4ai dictionary."""
    for key in ("html", "cleaned_html", "raw_html"):
        value = raw_result.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return ""


def normalize_subject_url(raw_url: str, base_url: str) -> str:
    """Normalize Douban subject links to canonical https URLs."""
    if not raw_url:
        return ""
    full = urljoin(base_url, raw_url.strip())
    if not re.match(r"^https?://book\.douban\.com/subject/\d+/?$", full):
        return ""
    return full.replace("http://", "https://").rstrip("/") + "/"


def extract_catalog_items(html: str, page_url: str) -> list[BookCatalogItem]:
    """Extract catalog items via JsonCssExtractionStrategy.

    Only list fields are extracted (title + url). Detail pages are not visited.
    """
    raw_items = JsonCssExtractionStrategy(CATALOG_SCHEMA).extract(page_url, html) or []
    results: list[BookCatalogItem] = []
    seen: set[str] = set()

    for item in raw_items:
        title = " ".join((item.get("title") or "").split())
        url = normalize_subject_url(item.get("url", ""), page_url)
        if not title or not url or url in seen:
            continue
        seen.add(url)
        results.append(BookCatalogItem(title=title, url=url))

    return results


def fetch_catalog_html_with_crawl4ai(base_url: str, target_url: str) -> str:
    """Fetch Douban HTML using external Crawl4AI server."""
    endpoint = f"{base_url.rstrip('/')}/crawl"
    payload = {
        "urls": [target_url],
        "browser_config": {
            "user_agent": DEFAULT_HEADERS["User-Agent"],
            "extra_headers": {"Accept-Language": DEFAULT_HEADERS["Accept-Language"]},
        },
        "crawler_config": {"word_count_threshold": 0},
    }
    with httpx.Client(timeout=120.0) as client:
        response = client.post(endpoint, json=payload)
        response.raise_for_status()
        data = response.json()

    if not data.get("success"):
        raise RuntimeError(f"Crawl4AI crawl failed: {data.get('error', 'unknown error')}")

    results = data.get("results") or []
    if not results:
        raise RuntimeError("Crawl4AI crawl returned empty results")

    html = _pick_html_from_crawl4ai_result(results[0])
    if not html:
        raise RuntimeError("Crawl4AI result has no usable html field")
    return html


def collect_catalog(kind: str, base_catalog_url: str, max_pages: int = 99) -> BookCatalogResult:
    """Pure core logic: Collect Douban catalog books via Crawl4AI with pagination."""
    base_url = os.getenv("CRAWL4AI_BASE_URL", "").strip()
    if not base_url:
        raise RuntimeError("CRAWL4AI_BASE_URL is not set")

    all_items: list[BookCatalogItem] = []
    seen_urls: set[str] = set()

    for page in range(1, max_pages + 1):
        if page > 1:
            delay = random.uniform(2.0, 5.0)
            print(f"[{kind}] Sleeping {delay:.1f}s to avoid anti-crawling...", file=sys.stderr)
            time.sleep(delay)

        target_url = base_catalog_url if page == 1 else f"{base_catalog_url}?p={page}"
        html = fetch_catalog_html_with_crawl4ai(base_url, target_url)
        items = extract_catalog_items(html, target_url)
        
        new_items = []
        for item in items:
            if item.url not in seen_urls:
                seen_urls.add(item.url)
                new_items.append(item)

        print(
            f"[{kind}] page={page} url={target_url} found={len(items)} new={len(new_items)}",
            file=sys.stderr,
        )
        
        if not items:
            break
            
        all_items.extend(new_items)
        
    return BookCatalogResult(kind=kind, total=len(all_items), books=all_items)


def collect_hot_catalog(max_pages: int = 99) -> BookCatalogResult:
    """Helper purely for hot books collection."""
    return collect_catalog("hot", HOT_CATALOG_URL, max_pages)


def collect_latest_catalog(max_pages: int = 99) -> BookCatalogResult:
    """Helper purely for latest books collection."""
    return collect_catalog("latest", LATEST_CATALOG_URL, max_pages)


def collect_book_detail(subject_url: str) -> BookDetail:
    """Fetch and parse detailed information for a specific Douban book subject."""
    base_url = os.getenv("CRAWL4AI_BASE_URL", "").strip()
    if not base_url:
        raise RuntimeError("CRAWL4AI_BASE_URL is not set")
    if not re.match(r"^https?://book\.douban\.com/subject/\d+/?$", subject_url):
        raise ValueError(f"Invalid Douban subject URL: {subject_url}")

    print(f"[detail] fetching url={subject_url}", file=sys.stderr)
    html = fetch_catalog_html_with_crawl4ai(base_url, subject_url)
    
    raw_items = JsonCssExtractionStrategy(BOOK_DETAIL_SCHEMA).extract(subject_url, html) or []
    if not raw_items:
        raise RuntimeError(f"Could not extract details from {subject_url}")

    raw = raw_items[0]
    
    title = (raw.get("title") or "").strip()
    
    try:
        rating = float(raw.get("rating", 0.0))
    except ValueError:
        rating = 0.0
        
    try:
        votes = int(raw.get("votes", 0))
    except ValueError:
        votes = 0

    info = " ".join((raw.get("info") or "").split())
    
    intro_all = raw.get("intro_all", "").strip()
    intro_short = raw.get("intro_short", "").strip()
    # prefer the unfolded ALL intro if available
    intro = " ".join((intro_all or intro_short).split())

    return BookDetail(
        title=title,
        url=subject_url,
        rating=rating,
        votes=votes,
        info=info,
        intro=intro,
    )
