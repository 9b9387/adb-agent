"""Regression tests for navigation-triggered observation failures."""

import asyncio
from types import SimpleNamespace

import browser_agent.runtime_registry as runtime_registry
from browser_agent.tools.browser import open_url
from browser_agent.tools.browser import type_text


class FakeKeyboard:
    async def press(self, key):
        self.last_key = key


class FakeLocator:
    def __init__(self, page, selector):
        self.page = page
        self.selector = selector

    @property
    def first(self):
        return self

    async def fill(self, text):
        self.page.last_fill = (self.selector, text)


class FakePage:
    def __init__(self):
        self.url = "about:blank"
        self.keyboard = FakeKeyboard()
        self.evaluate_attempts = 0

    def is_closed(self):
        return False

    def set_default_timeout(self, timeout_ms):
        self.timeout_ms = timeout_ms

    async def goto(self, url, wait_until):
        self.url = url

    async def title(self):
        return "GitHub"

    def locator(self, selector):
        return FakeLocator(self, selector)

    async def wait_for_load_state(self, state, timeout):
        self.waited_for_state = (state, timeout)

    async def evaluate(self, script, args):
        self.evaluate_attempts += 1
        if self.evaluate_attempts == 1:
            raise RuntimeError(
                "Page.evaluate: Execution context was destroyed, most likely because of a navigation"
            )
        return {
            "url": self.url,
            "title": "GitHub",
            "textExcerpt": "Search results visible",
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
        self.session = SimpleNamespace(id="navigation-regression")
        self.state = {}


def test_type_text_recovers_after_navigation_destroys_context(monkeypatch):
    # Regression: ISSUE-002 — observation capture crashed after Enter-triggered navigation
    # Found by /qa on 2026-04-01
    # Report: live repro from `uv run browser-agent "打开 GitHub 并搜索 google/adk"`
    monkeypatch.setattr(
        runtime_registry,
        "async_playwright",
        lambda: FakePlaywrightManager(),
    )
    monkeypatch.setenv("BROWSER_CDP_URL", "http://127.0.0.1:9222")

    async def scenario():
        tool_context = FakeToolContext()
        await open_url("https://github.com", tool_context)
        result = await type_text('input[name="query-builder-test"]', "google/adk", True, tool_context)
        assert result["status"] == "success"

    asyncio.run(scenario())
