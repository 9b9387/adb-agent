"""Integration tests for the crawl4ai Docker service.

These tests verify:
1. The service is reachable and healthy (/health endpoint)
2. The service can crawl and return HTML
3. Local extraction using JsonCssExtractionStrategy works on the crawled HTML

The tests automatically skip when the service is not reachable, so they do not
break CI pipelines that run without the Docker service.

Run against the live service:
    CRAWL4AI_BASE_URL=http://192.168.8.109:11235 pytest tests/test_crawl4ai_integration.py -v -s
    or
    pytest tests/test_crawl4ai_integration.py -v -s
"""

import os

import httpx
import pytest
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy

CRAWL4AI_BASE_URL = os.getenv("CRAWL4AI_BASE_URL", "http://localhost:11235")

def test_crawl4ai_service_health():
    """Verify the crawl4ai service is reachable and returns health status."""
    url = f"{CRAWL4AI_BASE_URL}/health"

    try:
        response = httpx.get(url, timeout=5.0)
    except (httpx.ConnectError, httpx.TimeoutException):
        pytest.skip(f"crawl4ai service not reachable at {CRAWL4AI_BASE_URL}")

    assert response.status_code == 200, (
        f"Expected HTTP 200, got {response.status_code}"
    )

    body = response.json()

    assert body.get("status") == "ok", (
        f"Expected status='ok', got {body.get('status')!r}"
    )
    assert "version" in body, "Response missing 'version' field"
    assert "timestamp" in body, "Response missing 'timestamp' field"


def test_crawl4ai_extracting_douban_book_title():
    """Crawl Douban book page and extract title using JsonCssExtractionStrategy."""
    url = "https://book.douban.com/subject/38237921/"

    print(f"\nTarget URL: {url}")

    # Simple schema: extract title
    schema = {
        "name": "DoubanBookTitle",
        "baseSelector": "#wrapper",
        "fields": [
            {
                "name": "title",
                "selector": "h1 span[property='v:itemreviewed']",
                "type": "text"
            }
        ]
    }

    # Request crawl4ai to fetch the page
    endpoint = f"{CRAWL4AI_BASE_URL}/crawl"
    print(f"crawl4ai endpoint: {endpoint}")
    
    payload = {
        "urls": [url],
        "crawler_config": {
            "headers": {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            }
        }
    }

    try:
        response = httpx.post(endpoint, json=payload, timeout=30.0)
    except (httpx.ConnectError, httpx.TimeoutException) as e:
        pytest.skip(f"crawl4ai service not reachable at {CRAWL4AI_BASE_URL}")

    assert response.status_code == 200, f"Crawl failed: HTTP {response.status_code}"

    data = response.json()
    assert data.get("success"), f"Crawl unsuccessful: {data.get('error_message')}"
    assert data.get("results"), "No crawl results returned"

    result = data["results"][0]
    assert result.get("success"), f"Result failed: {result.get('error_message')}"

    html_content = result.get("html", "")
    assert html_content, "No HTML content returned"

    # Extract using JsonCssExtractionStrategy
    strategy = JsonCssExtractionStrategy(schema)
    extracted = strategy.extract(url, html_content)

    print(f"Extraction result: {extracted}")

    # Verify extraction result — extracted is a list of records
    assert extracted, "Extraction returned empty result"
    assert isinstance(extracted, list), f"Expected list, got {type(extracted)}"
    assert len(extracted) > 0, "No extraction records returned"

    record = extracted[0]
    assert "title" in record, "Title field not extracted"

    title = record.get("title", "").strip()
    print(f"Extracted title: '{title}'")
    assert len(title) > 0, "Extracted title is empty"
