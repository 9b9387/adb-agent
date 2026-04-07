"""Regression tests for async Playwright browser tools."""

import asyncio
from types import SimpleNamespace

import browser_agent.runtime_registry as runtime_registry
from browser_agent.tools.browser import open_url


class FakePage:
    def __init__(self):
        self.url = "about:blank"

    async def goto(self, url, wait_until):
        self.url = url

    def set_default_timeout(self, timeout_ms):
        self.timeout_ms = timeout_ms

    def is_closed(self):
        return False

    async def title(self):
        return "Example Domain"

    async def evaluate(self, script, args):
        return {
            "url": self.url,
            "title": "Example Domain",
            "textExcerpt": "Regression page",
            "focusedElement": None,
            "elements": [],
        }

    async def screenshot(self, type, quality):
        return b"fake-jpeg"


class FakeContext:
    def __init__(self):
        self.pages = [FakePage()]

    def set_default_timeout(self, timeout_ms):
        self.timeout_ms = timeout_ms

    async def new_page(self):
        page = FakePage()
        self.pages.append(page)
        return page

    async def close(self):
        return None


class FakeBrowser:
    def __init__(self):
        self.contexts = [FakeContext()]


class FakeChromium:
    async def connect_over_cdp(self, endpoint_url):
        return FakeBrowser()

    async def launch_persistent_context(self, **kwargs):
        return FakeContext()


class FakePlaywright:
    def __init__(self):
        self.chromium = FakeChromium()

    async def stop(self):
        return None


class FakePlaywrightManager:
    async def start(self):
        return FakePlaywright()


class FakeToolContext:
    def __init__(self):
        self.session = SimpleNamespace(id="regression-session")
        self.state = {}


def test_open_url_works_inside_asyncio_loop(monkeypatch):
    # Regression: ISSUE-001 — browser tools used Playwright Sync API inside ADK's asyncio loop
    # Found by /qa on 2026-04-01
    # Report: live repro from `uv run browser-agent "打开 GitHub 并搜索 google/adk"`
    monkeypatch.setattr(
        runtime_registry,
        "async_playwright",
        lambda: FakePlaywrightManager(),
    )
    monkeypatch.setenv("BROWSER_CDP_URL", "http://127.0.0.1:9222")

    async def scenario():
        result = await open_url("https://example.com", FakeToolContext())
        assert result["status"] == "success"
        assert result["current_url"] == "https://example.com"

    asyncio.run(scenario())
