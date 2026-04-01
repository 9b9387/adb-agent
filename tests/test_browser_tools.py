"""Tests for Playwright-backed browser tools."""

import asyncio
from types import SimpleNamespace

import browser_agent.runtime_registry as runtime_registry
from browser_agent.tools.browser import click
from browser_agent.tools.browser import close_browser
from browser_agent.tools.browser import launch_browser
from browser_agent.tools.browser import open_url
from browser_agent.tools.browser import press_key
from browser_agent.tools.browser import read_page
from browser_agent.tools.browser import scroll
from browser_agent.tools.browser import set_file_input
from browser_agent.tools.browser import type_text
from browser_agent.tools.browser import wait_for


def run(coro):
    return asyncio.run(coro)


class FakeKeyboard:
    def __init__(self, page):
        self.page = page
        self.pressed = []

    async def press(self, key):
        self.pressed.append(key)


class FakeMouse:
    def __init__(self, page):
        self.page = page
        self.scroll_events = []

    async def wheel(self, delta_x, delta_y):
        self.scroll_events.append((delta_x, delta_y))


class FakeLocator:
    def __init__(self, page, selector):
        self.page = page
        self.selector = selector

    @property
    def first(self):
        return self

    async def click(self):
        self.page.last_clicked = self.selector
        if self.selector == "text=Continue":
            self.page.title_value = "Continue clicked"

    async def fill(self, text):
        self.page.filled[self.selector] = text

    async def set_input_files(self, file_path):
        self.page.selected_files[self.selector] = file_path

    async def wait_for(self, state, timeout):
        self.page.waited_for = (self.selector, state, timeout)


class FakePage:
    def __init__(
        self,
        url="https://current.example/upload",
        title="Upload form",
        *,
        visibility="visible",
        has_focus=True,
    ):
        self.url = url
        self.title_value = title
        self.closed = False
        self.filled = {}
        self.selected_files = {}
        self.last_clicked = None
        self.waited_for = None
        self.goto_calls = []
        self.visibility = visibility
        self.has_focus = has_focus
        self.keyboard = FakeKeyboard(self)
        self.mouse = FakeMouse(self)

    def is_closed(self):
        return self.closed

    def set_default_timeout(self, timeout_ms):
        self.timeout_ms = timeout_ms

    async def goto(self, url, wait_until):
        self.goto_calls.append(url)
        self.url = url
        if "example" in url:
            self.title_value = "Example Domain"
        else:
            self.title_value = "Loaded page"

    async def title(self):
        return self.title_value

    async def screenshot(self, type, quality):
        return b"fake-jpeg"

    async def evaluate(self, script, args=None):
        if "visibilityState" in script or "hasFocus" in script:
            return {
                "visibility": self.visibility,
                "hasFocus": self.has_focus,
            }
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
                    "inputType": "search",
                    "testId": "",
                    "id": "",
                    "name": "search",
                    "selectedFiles": [],
                    "suggestedSelectors": ['input[name="search"]', '[placeholder="Search"]'],
                },
                {
                    "tag": "input",
                    "text": "",
                    "ariaLabel": "",
                    "placeholder": "",
                    "inputType": "file",
                    "testId": "",
                    "id": "file-upload",
                    "name": "file",
                    "selectedFiles": [self.selected_files.get('input[type="file"]', "").split("/")[-1]]
                    if self.selected_files.get('input[type="file"]')
                    else [],
                    "suggestedSelectors": ['input[type="file"]', '[id="file-upload"]'],
                },
            ],
        }

    def locator(self, selector):
        return FakeLocator(self, selector)


class FakeContext:
    def __init__(self, pages=None):
        self.pages = pages or [FakePage()]
        self.page = self.pages[-1]
        self.closed = False

    def set_default_timeout(self, timeout_ms):
        self.timeout_ms = timeout_ms

    async def new_page(self):
        self.page = FakePage()
        self.pages.append(self.page)
        return self.page

    async def close(self):
        self.closed = True
        for page in self.pages:
            page.closed = True


class FakeBrowser:
    def __init__(self, context):
        self.contexts = [context]


class FakeChromium:
    def __init__(self):
        self.last_context = None
        self.cdp_pages = None

    async def launch_persistent_context(self, **kwargs):
        self.launch_kwargs = kwargs
        self.last_context = FakeContext()
        return self.last_context

    async def connect_over_cdp(self, endpoint_url):
        self.endpoint_url = endpoint_url
        self.last_context = FakeContext(self.cdp_pages)
        return FakeBrowser(self.last_context)


class FakePlaywright:
    def __init__(self):
        self.chromium = FakeChromium()
        self.stopped = False

    async def stop(self):
        self.stopped = True


class FakePlaywrightManager:
    def __init__(self, playwright):
        self.playwright = playwright

    async def start(self):
        return self.playwright


class FakeToolContext:
    def __init__(self, session_id="browser-test", state=None):
        self.session = SimpleNamespace(id=session_id)
        self.state = state or {}


def test_browser_tools_round_trip(monkeypatch):
    fake_playwright = FakePlaywright()
    run(runtime_registry.close_all_sessions())
    monkeypatch.setattr(
        runtime_registry,
        "async_playwright",
        lambda: FakePlaywrightManager(fake_playwright),
    )

    tool_context = FakeToolContext()

    open_result = run(open_url("https://example.com", tool_context))
    assert open_result["status"] == "success"
    assert tool_context.state["browser"]["current_url"] == "https://example.com"

    click_result = run(click("text=Continue", tool_context))
    assert click_result["status"] == "success"
    assert click_result["title"] == "Continue clicked"

    type_result = run(type_text('input[name="search"]', "playwright", False, tool_context))
    assert type_result["status"] == "success"

    wait_result = run(wait_for("", "Welcome", 2.0, tool_context))
    assert wait_result["status"] == "success"

    scroll_result = run(scroll("down", 500, tool_context))
    assert scroll_result["status"] == "success"

    key_result = run(press_key("Enter", tool_context))
    assert key_result["status"] == "success"

    page_result = run(read_page(tool_context))
    assert page_result["status"] == "success"
    assert page_result["url"] == "https://example.com"
    assert page_result["elements"][0]["suggestedSelectors"][0] == "text=Continue"

    close_result = run(close_browser(tool_context))
    assert close_result["status"] == "success"
    assert tool_context.state["browser"] == {"active": False}
    assert fake_playwright.stopped is True


def test_browser_tools_support_cdp(monkeypatch):
    fake_playwright = FakePlaywright()
    run(runtime_registry.close_all_sessions())
    async def fake_resolve_cdp_connect_target(_cdp_url):
        return "ws://127.0.0.1:9222/devtools/browser/mock"

    monkeypatch.setattr(
        runtime_registry,
        "async_playwright",
        lambda: FakePlaywrightManager(fake_playwright),
    )
    monkeypatch.setattr(
        runtime_registry,
        "_resolve_cdp_connect_target",
        fake_resolve_cdp_connect_target,
    )
    monkeypatch.setenv("BROWSER_CDP_URL", "http://127.0.0.1:9222")

    tool_context = FakeToolContext(session_id="browser-cdp-test")

    open_result = run(open_url("https://example.com", tool_context))

    assert open_result["status"] == "success"
    assert tool_context.state["browser"]["connection_mode"] == "cdp"
    assert tool_context.state["browser"]["cdp_url"] == "http://127.0.0.1:9222"
    assert fake_playwright.chromium.endpoint_url == "ws://127.0.0.1:9222/devtools/browser/mock"

    close_result = run(close_browser(tool_context))
    assert close_result["status"] == "success"
    assert fake_playwright.stopped is True


def test_launch_browser_about_blank_preserves_current_cdp_page(monkeypatch):
    fake_playwright = FakePlaywright()
    run(runtime_registry.close_all_sessions())

    async def fake_resolve_cdp_connect_target(_cdp_url):
        return "ws://127.0.0.1:9222/devtools/browser/mock"

    monkeypatch.setattr(
        runtime_registry,
        "async_playwright",
        lambda: FakePlaywrightManager(fake_playwright),
    )
    monkeypatch.setattr(
        runtime_registry,
        "_resolve_cdp_connect_target",
        fake_resolve_cdp_connect_target,
    )
    monkeypatch.setenv("BROWSER_CDP_URL", "http://127.0.0.1:9222")

    tool_context = FakeToolContext(session_id="browser-current-page-test")

    launch_result = run(launch_browser("about:blank", tool_context))

    assert launch_result["status"] == "success"
    assert launch_result["current_url"] == "https://current.example/upload"
    assert tool_context.state["browser"]["current_url"] == "https://current.example/upload"
    assert fake_playwright.chromium.last_context.page.goto_calls == []


def test_launch_browser_prefers_focused_cdp_page(monkeypatch):
    fake_playwright = FakePlaywright()
    fake_playwright.chromium.cdp_pages = [
        FakePage(
            url="https://focused.example/upload",
            title="Focused Upload",
            visibility="visible",
            has_focus=True,
        ),
        FakePage(
            url="https://background.example/upload",
            title="Background Upload",
            visibility="hidden",
            has_focus=False,
        ),
    ]
    run(runtime_registry.close_all_sessions())

    async def fake_resolve_cdp_connect_target(_cdp_url):
        return "ws://127.0.0.1:9222/devtools/browser/mock"

    monkeypatch.setattr(
        runtime_registry,
        "async_playwright",
        lambda: FakePlaywrightManager(fake_playwright),
    )
    monkeypatch.setattr(
        runtime_registry,
        "_resolve_cdp_connect_target",
        fake_resolve_cdp_connect_target,
    )
    monkeypatch.setenv("BROWSER_CDP_URL", "http://127.0.0.1:9222")

    tool_context = FakeToolContext(session_id="browser-focused-page-test")

    launch_result = run(launch_browser("", tool_context))

    assert launch_result["status"] == "success"
    assert launch_result["current_url"] == "https://focused.example/upload"


def test_click_retargets_newly_focused_cdp_page(monkeypatch):
    fake_playwright = FakePlaywright()
    first_page = FakePage(
        url="https://first.example/upload",
        title="First Upload",
        visibility="visible",
        has_focus=True,
    )
    second_page = FakePage(
        url="https://second.example/upload",
        title="Second Upload",
        visibility="hidden",
        has_focus=False,
    )
    fake_playwright.chromium.cdp_pages = [first_page, second_page]
    run(runtime_registry.close_all_sessions())

    async def fake_resolve_cdp_connect_target(_cdp_url):
        return "ws://127.0.0.1:9222/devtools/browser/mock"

    monkeypatch.setattr(
        runtime_registry,
        "async_playwright",
        lambda: FakePlaywrightManager(fake_playwright),
    )
    monkeypatch.setattr(
        runtime_registry,
        "_resolve_cdp_connect_target",
        fake_resolve_cdp_connect_target,
    )
    monkeypatch.setenv("BROWSER_CDP_URL", "http://127.0.0.1:9222")

    tool_context = FakeToolContext(session_id="browser-retarget-test")
    launch_result = run(launch_browser("", tool_context))
    assert launch_result["status"] == "success"
    assert launch_result["current_url"] == "https://first.example/upload"

    first_page.has_focus = False
    first_page.visibility = "hidden"
    second_page.has_focus = True
    second_page.visibility = "visible"

    click_result = run(click("text=Continue", tool_context))

    assert click_result["status"] == "success"
    assert click_result["current_url"] == "https://second.example/upload"
    assert first_page.last_clicked is None
    assert second_page.last_clicked == "text=Continue"


def test_set_file_input_attaches_local_file(monkeypatch, tmp_path):
    fake_playwright = FakePlaywright()
    run(runtime_registry.close_all_sessions())
    monkeypatch.setattr(
        runtime_registry,
        "async_playwright",
        lambda: FakePlaywrightManager(fake_playwright),
    )
    monkeypatch.setenv("BROWSER_CDP_URL", "http://127.0.0.1:9222")

    upload_file = tmp_path / "image2.png"
    upload_file.write_bytes(b"fake-image")
    tool_context = FakeToolContext(
        session_id="browser-file-upload",
        state={"user_task": f"Upload {upload_file} to the page"},
    )

    run(open_url("https://example.com/upload", tool_context))
    result = run(set_file_input('input[type="file"]', str(upload_file), tool_context))

    assert result["status"] == "success"
    assert result["file_name"] == "image2.png"
    assert "file_path" not in result

    page_result = run(read_page(tool_context))
    file_inputs = [element for element in page_result["elements"] if element.get("inputType") == "file"]
    assert file_inputs[0]["selectedFiles"] == ["image2.png"]


def test_set_file_input_rejects_unapproved_local_file(monkeypatch, tmp_path):
    fake_playwright = FakePlaywright()
    run(runtime_registry.close_all_sessions())
    monkeypatch.setattr(
        runtime_registry,
        "async_playwright",
        lambda: FakePlaywrightManager(fake_playwright),
    )
    monkeypatch.setenv("BROWSER_CDP_URL", "http://127.0.0.1:9222")

    approved_file = tmp_path / "approved.png"
    approved_file.write_bytes(b"approved")
    secret_file = tmp_path / "secret.png"
    secret_file.write_bytes(b"secret")
    tool_context = FakeToolContext(
        session_id="browser-file-authz",
        state={"user_task": f"Upload only {approved_file}"},
    )

    run(open_url("https://example.com/upload", tool_context))
    result = run(set_file_input('input[type="file"]', str(secret_file), tool_context))

    assert result == {
        "status": "error",
        "error_message": "File path is not explicitly authorized by the original user task.",
    }
