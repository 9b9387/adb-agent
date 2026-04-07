"""Douban Scraper standalone module.

This module provides pure functions, schemas, and a Typer CLI
to collect data from Douban, independent of any specific agent.
"""

from .core import (
    collect_book_detail,
    collect_catalog,
    collect_hot_catalog,
    collect_latest_catalog,
    extract_catalog_items,
    fetch_catalog_html_with_crawl4ai,
)
from .schemas import BookCatalogItem, BookCatalogResult, BookDetail

__all__ = [
    "collect_book_detail",
    "collect_catalog",
    "collect_hot_catalog",
    "collect_latest_catalog",
    "extract_catalog_items",
    "fetch_catalog_html_with_crawl4ai",
    "BookCatalogItem",
    "BookCatalogResult",
    "BookDetail",
]
