"""In-process Playwright runtime registry keyed by ADK session id."""

from __future__ import annotations

import atexit
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from playwright.sync_api import Browser
from playwright.sync_api import BrowserContext
from playwright.sync_api import Page
from playwright.sync_api import Playwright
from playwright.sync_api import sync_playwright

DEFAULT_VIEWPORT = {"width": 1440, "height": 900}
DEFAULT_TIMEOUT_MS = 5_000
DEFAULT_USER_DATA_DIR = ".browser-profile/playwright"


@dataclass
class BrowserRuntime:
    """Live Playwright objects for a single ADK session."""

    session_id: str
    playwright: Playwright
    browser: Browser | None
    context: BrowserContext
    page: Page
    user_data_dir: str
    headless: bool
    channel: str | None
    connection_mode: str
    cdp_url: str | None


_RUNTIMES: dict[str, BrowserRuntime] = {}
_REGISTERED_ATEXIT = False


def _env_flag(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def _resolve_user_data_dir(user_data_dir: str | None = None) -> str:
    raw_path = user_data_dir or os.getenv("BROWSER_USER_DATA_DIR") or DEFAULT_USER_DATA_DIR
    return str(Path(raw_path).expanduser().resolve())


def _resolve_channel(channel: str | None = None) -> str | None:
    value = channel or os.getenv("BROWSER_CHANNEL")
    return value or None


def _resolve_headless(headless: bool | None = None) -> bool:
    if headless is not None:
        return headless
    return _env_flag("BROWSER_HEADLESS", False)


def _resolve_start_url(start_url: str | None = None) -> str | None:
    if start_url is not None:
        return start_url or None
    return os.getenv("BROWSER_START_URL") or None


def _resolve_cdp_url(cdp_url: str | None = None) -> str | None:
    value = cdp_url or os.getenv("BROWSER_CDP_URL")
    return value or None


def _all_open_pages(runtime: BrowserRuntime) -> list[Page]:
    pages: list[Page] = []
    for context in [runtime.context, *[ctx for ctx in runtime.browser.contexts if ctx is not runtime.context]] if runtime.browser else [runtime.context]:
        pages.extend(page for page in context.pages if not page.is_closed())
    return pages


def _get_active_page(runtime: BrowserRuntime) -> Page:
    if not runtime.page.is_closed():
        return runtime.page

    open_pages = _all_open_pages(runtime)
    runtime.page = open_pages[-1] if open_pages else runtime.context.new_page()
    runtime.page.set_default_timeout(DEFAULT_TIMEOUT_MS)
    return runtime.page


def _snapshot_page(page: Page, *, element_limit: int, text_limit: int) -> dict[str, Any]:
    return page.evaluate(
        """
        ({ elementLimit, textLimit }) => {
          const normalize = (value) => (value || "").replace(/\\s+/g, " ").trim();
          const isVisible = (element) => {
            if (!element) return false;
            const style = window.getComputedStyle(element);
            const rect = element.getBoundingClientRect();
            return style.display !== "none" && style.visibility !== "hidden" && rect.width > 0 && rect.height > 0;
          };

          const selectorSuggestions = (element) => {
            const tag = element.tagName.toLowerCase();
            const testId = normalize(element.getAttribute("data-testid"));
            const id = normalize(element.id);
            const name = normalize(element.getAttribute("name"));
            const placeholder = normalize(element.getAttribute("placeholder"));
            const ariaLabel = normalize(element.getAttribute("aria-label"));
            const text = normalize(element.innerText || element.textContent);
            const selectors = [];

            if (testId) selectors.push(`[data-testid="${testId}"]`);
            if (id) selectors.push(`[id="${id}"]`);
            if (name && ["input", "textarea", "select"].includes(tag)) selectors.push(`${tag}[name="${name}"]`);
            if (placeholder) selectors.push(`[placeholder="${placeholder}"]`);
            if (ariaLabel) selectors.push(`[aria-label="${ariaLabel}"]`);
            if (text) selectors.push(`text=${text.slice(0, 80)}`);
            return selectors.slice(0, 3);
          };

          const focus = document.activeElement
            ? {
                tag: document.activeElement.tagName.toLowerCase(),
                text: normalize(document.activeElement.innerText || document.activeElement.textContent).slice(0, 120),
                ariaLabel: normalize(document.activeElement.getAttribute("aria-label")).slice(0, 120),
                name: normalize(document.activeElement.getAttribute("name")).slice(0, 120),
                placeholder: normalize(document.activeElement.getAttribute("placeholder")).slice(0, 120),
              }
            : null;

          const candidates = Array.from(
            document.querySelectorAll(
              'button, a[href], input, textarea, select, [role="button"], [role="link"], [role="textbox"], [data-testid], [aria-label]'
            )
          );

          const elements = [];
          const seen = new Set();

          for (const element of candidates) {
            if (!isVisible(element)) continue;

            const entry = {
              tag: element.tagName.toLowerCase(),
              text: normalize(element.innerText || element.textContent).slice(0, 120),
              ariaLabel: normalize(element.getAttribute("aria-label")).slice(0, 120),
              placeholder: normalize(element.getAttribute("placeholder")).slice(0, 120),
              testId: normalize(element.getAttribute("data-testid")).slice(0, 120),
              id: normalize(element.id).slice(0, 120),
              name: normalize(element.getAttribute("name")).slice(0, 120),
            };

            const signature = JSON.stringify(entry);
            if (seen.has(signature)) continue;
            seen.add(signature);

            elements.push({
              ...entry,
              suggestedSelectors: selectorSuggestions(element),
            });

            if (elements.length >= elementLimit) break;
          }

          return {
            url: window.location.href,
            title: document.title,
            textExcerpt: normalize(document.body ? document.body.innerText : "").slice(0, textLimit),
            focusedElement: focus,
            elements,
          };
        }
        """,
        {"elementLimit": element_limit, "textLimit": text_limit},
    )


def has_runtime(session_id: str) -> bool:
    """Return whether a live Playwright runtime exists for the session."""
    return session_id in _RUNTIMES


def get_runtime(session_id: str) -> BrowserRuntime:
    """Return the live Playwright runtime for the session."""
    runtime = _RUNTIMES.get(session_id)
    if runtime is None:
        raise RuntimeError("No live browser session. Launch the browser first.")
    runtime.page = _get_active_page(runtime)
    return runtime


def launch_browser_session(
    session_id: str,
    *,
    start_url: str | None = None,
    user_data_dir: str | None = None,
    headless: bool | None = None,
    channel: str | None = None,
    cdp_url: str | None = None,
) -> BrowserRuntime:
    """Launch or attach to a browser session for the given ADK session."""
    if session_id in _RUNTIMES:
        runtime = get_runtime(session_id)
        target_url = _resolve_start_url(start_url)
        if target_url:
            runtime.page.goto(target_url, wait_until="domcontentloaded")
        return runtime

    playwright = sync_playwright().start()
    resolved_user_data_dir = _resolve_user_data_dir(user_data_dir)
    resolved_headless = _resolve_headless(headless)
    resolved_channel = _resolve_channel(channel)
    resolved_cdp_url = _resolve_cdp_url(cdp_url)

    try:
        if resolved_cdp_url:
            browser = playwright.chromium.connect_over_cdp(resolved_cdp_url)
            context = browser.contexts[0] if browser.contexts else browser.new_context(viewport=DEFAULT_VIEWPORT)
            context.set_default_timeout(DEFAULT_TIMEOUT_MS)
            open_pages = [page for page in context.pages if not page.is_closed()]
            page = open_pages[-1] if open_pages else context.new_page()
            connection_mode = "cdp"
            runtime = BrowserRuntime(
                session_id=session_id,
                playwright=playwright,
                browser=browser,
                context=context,
                page=page,
                user_data_dir="",
                headless=False,
                channel=resolved_channel,
                connection_mode=connection_mode,
                cdp_url=resolved_cdp_url,
            )
        else:
            Path(resolved_user_data_dir).mkdir(parents=True, exist_ok=True)
            context = playwright.chromium.launch_persistent_context(
                user_data_dir=resolved_user_data_dir,
                headless=resolved_headless,
                channel=resolved_channel,
                viewport=DEFAULT_VIEWPORT,
            )
            context.set_default_timeout(DEFAULT_TIMEOUT_MS)
            page = context.pages[0] if context.pages else context.new_page()
            connection_mode = "persistent"
            runtime = BrowserRuntime(
                session_id=session_id,
                playwright=playwright,
                browser=None,
                context=context,
                page=page,
                user_data_dir=resolved_user_data_dir,
                headless=resolved_headless,
                channel=resolved_channel,
                connection_mode=connection_mode,
                cdp_url=None,
            )
    except Exception:
        playwright.stop()
        raise

    page.set_default_timeout(DEFAULT_TIMEOUT_MS)
    _RUNTIMES[session_id] = runtime

    global _REGISTERED_ATEXIT
    if not _REGISTERED_ATEXIT:
        atexit.register(close_all_sessions)
        _REGISTERED_ATEXIT = True

    target_url = _resolve_start_url(start_url)
    if target_url:
        runtime.page.goto(target_url, wait_until="domcontentloaded")

    return runtime


def close_browser_session(session_id: str) -> bool:
    """Close and remove the browser session for the given ADK session."""
    runtime = _RUNTIMES.pop(session_id, None)
    if runtime is None:
        return False

    try:
        if runtime.connection_mode == "persistent":
            runtime.context.close()
    finally:
        runtime.playwright.stop()
    return True


def close_all_sessions() -> None:
    """Close all tracked browser sessions."""
    for session_id in list(_RUNTIMES):
        close_browser_session(session_id)


def capture_observation(
    session_id: str,
    *,
    include_screenshot: bool = True,
    element_limit: int = 8,
    text_limit: int = 1_200,
) -> dict[str, Any] | None:
    """Capture a lightweight observation of the current page state."""
    runtime = _RUNTIMES.get(session_id)
    if runtime is None:
        return None

    page = _get_active_page(runtime)
    observation = _snapshot_page(page, element_limit=element_limit, text_limit=text_limit)
    observation["screenshot_bytes"] = (
        page.screenshot(type="jpeg", quality=70) if include_screenshot else None
    )
    observation["headless"] = runtime.headless
    observation["user_data_dir"] = runtime.user_data_dir
    observation["channel"] = runtime.channel
    observation["connection_mode"] = runtime.connection_mode
    observation["cdp_url"] = runtime.cdp_url
    return observation


def build_browser_state(runtime: BrowserRuntime, observation: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build a JSON-serializable browser summary for ADK session state."""
    if observation is None:
        observation = capture_observation(runtime.session_id, include_screenshot=False)

    return {
        "active": True,
        "connection_mode": runtime.connection_mode,
        "cdp_url": runtime.cdp_url or "",
        "user_data_dir": runtime.user_data_dir,
        "headless": runtime.headless,
        "channel": runtime.channel or "",
        "current_url": observation["url"] if observation else runtime.page.url,
        "title": observation["title"] if observation else runtime.page.title(),
    }
