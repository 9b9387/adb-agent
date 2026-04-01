"""Tests for Playwright-backed browser tools."""

from types import SimpleNamespace

import browser_agent.runtime_registry as runtime_registry
from browser_agent.tools.browser import click
from browser_agent.tools.browser import close_browser
from browser_agent.tools.browser import open_url
from browser_agent.tools.browser import press_key
from browser_agent.tools.browser import read_page
from browser_agent.tools.browser import scroll
from browser_agent.tools.browser import type_text
from browser_agent.tools.browser import wait_for


class FakeKeyboard:
    def __init__(self, page):
        self.page = page
        self.pressed = []

    def press(self, key):
        self.pressed.append(key)


class FakeMouse:
    def __init__(self, page):
        self.page = page
        self.scroll_events = []

    def wheel(self, delta_x, delta_y):
        self.scroll_events.append((delta_x, delta_y))


class FakeLocator:
    def __init__(self, page, selector):
        self.page = page
        self.selector = selector

    @property
    def first(self):
        return self

    def click(self):
        self.page.last_clicked = self.selector
        if self.selector == "text=Continue":
            self.page.title_value = "Continue clicked"

    def fill(self, text):
        self.page.filled[self.selector] = text

    def wait_for(self, state, timeout):
        self.page.waited_for = (self.selector, state, timeout)


class FakePage:
    def __init__(self):
        self.url = "about:blank"
        self.title_value = "Blank page"
        self.closed = False
        self.filled = {}
        self.last_clicked = None
        self.waited_for = None
        self.keyboard = FakeKeyboard(self)
        self.mouse = FakeMouse(self)

    def is_closed(self):
        return self.closed

    def set_default_timeout(self, timeout_ms):
        self.timeout_ms = timeout_ms

    def goto(self, url, wait_until):
        self.url = url
        if "example" in url:
            self.title_value = "Example Domain"
        else:
            self.title_value = "Loaded page"

    def title(self):
        return self.title_value

    def screenshot(self, type, quality):
        return b"fake-jpeg"

    def evaluate(self, script, args):
        return {
            "url": self.url,
            "title": self.title_value,
            "textExcerpt": "Welcome to the test page",
            "focusedElement": {
                "tag": "input",
                "text": "",
                "ariaLabel": "",
                "name": "search",
                "placeholder": "Search",
            },
            "elements": [
                {
                    "tag": "button",
                    "text": "Continue",
                    "ariaLabel": "",
                    "placeholder": "",
                    "testId": "",
                    "id": "",
                    "name": "",
                    "suggestedSelectors": ["text=Continue", '[aria-label="Continue"]'],
                },
                {
                    "tag": "input",
                    "text": "",
                    "ariaLabel": "",
                    "placeholder": "Search",
                    "testId": "",
                    "id": "",
                    "name": "search",
                    "suggestedSelectors": ['input[name="search"]', '[placeholder="Search"]'],
                },
            ],
        }

    def locator(self, selector):
        return FakeLocator(self, selector)


class FakeContext:
    def __init__(self):
        self.page = FakePage()
        self.pages = [self.page]
        self.closed = False

    def set_default_timeout(self, timeout_ms):
        self.timeout_ms = timeout_ms

    def new_page(self):
        self.page = FakePage()
        self.pages.append(self.page)
        return self.page

    def close(self):
        self.closed = True
        for page in self.pages:
            page.closed = True


class FakeBrowser:
    def __init__(self, context):
        self.contexts = [context]


class FakeChromium:
    def launch_persistent_context(self, **kwargs):
        self.launch_kwargs = kwargs
        return FakeContext()

    def connect_over_cdp(self, endpoint_url):
        self.endpoint_url = endpoint_url
        return FakeBrowser(FakeContext())


class FakePlaywright:
    def __init__(self):
        self.chromium = FakeChromium()
        self.stopped = False

    def stop(self):
        self.stopped = True


class FakePlaywrightManager:
    def __init__(self, playwright):
        self.playwright = playwright

    def start(self):
        return self.playwright


class FakeToolContext:
    def __init__(self, session_id="browser-test"):
        self.session = SimpleNamespace(id=session_id)
        self.state = {}


def test_browser_tools_round_trip(monkeypatch):
    fake_playwright = FakePlaywright()
    runtime_registry.close_all_sessions()
    monkeypatch.setattr(
        runtime_registry,
        "sync_playwright",
        lambda: FakePlaywrightManager(fake_playwright),
    )

    tool_context = FakeToolContext()

    open_result = open_url("https://example.com", tool_context)
    assert open_result["status"] == "success"
    assert tool_context.state["browser"]["current_url"] == "https://example.com"

    click_result = click("text=Continue", tool_context)
    assert click_result["status"] == "success"
    assert click_result["title"] == "Continue clicked"

    type_result = type_text('input[name="search"]', "playwright", False, tool_context)
    assert type_result["status"] == "success"

    wait_result = wait_for("", "Welcome", 2.0, tool_context)
    assert wait_result["status"] == "success"

    scroll_result = scroll("down", 500, tool_context)
    assert scroll_result["status"] == "success"

    key_result = press_key("Enter", tool_context)
    assert key_result["status"] == "success"

    page_result = read_page(tool_context)
    assert page_result["status"] == "success"
    assert page_result["url"] == "https://example.com"
    assert page_result["elements"][0]["suggestedSelectors"][0] == "text=Continue"

    close_result = close_browser(tool_context)
    assert close_result["status"] == "success"
    assert tool_context.state["browser"] == {"active": False}
    assert fake_playwright.stopped is True


def test_browser_tools_support_cdp(monkeypatch):
    fake_playwright = FakePlaywright()
    runtime_registry.close_all_sessions()
    monkeypatch.setattr(
        runtime_registry,
        "sync_playwright",
        lambda: FakePlaywrightManager(fake_playwright),
    )
    monkeypatch.setenv("BROWSER_CDP_URL", "http://127.0.0.1:9222")

    tool_context = FakeToolContext(session_id="browser-cdp-test")

    open_result = open_url("https://example.com", tool_context)

    assert open_result["status"] == "success"
    assert tool_context.state["browser"]["connection_mode"] == "cdp"
    assert tool_context.state["browser"]["cdp_url"] == "http://127.0.0.1:9222"

    close_result = close_browser(tool_context)
    assert close_result["status"] == "success"
    assert fake_playwright.stopped is True
