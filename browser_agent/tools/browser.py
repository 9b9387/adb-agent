"""Playwright-backed browser tools for the browser agent."""

from __future__ import annotations

from google.adk.tools import ToolContext

from browser_agent.runtime_registry import build_browser_state
from browser_agent.runtime_registry import capture_observation
from browser_agent.runtime_registry import close_browser_session
from browser_agent.runtime_registry import get_runtime
from browser_agent.runtime_registry import has_runtime
from browser_agent.runtime_registry import launch_browser_session


async def _sync_browser_state(
    tool_context: ToolContext,
    observation: dict | None = None,
) -> dict | None:
    if not has_runtime(tool_context.session.id):
        return None

    runtime = get_runtime(tool_context.session.id)
    tool_context.state["browser"] = await build_browser_state(runtime, observation)
    return tool_context.state["browser"]


async def launch_browser(start_url: str, tool_context: ToolContext) -> dict:
    """Launch a persistent Chromium session for this task.

    Args:
        start_url: Optional URL to open immediately. Pass an empty string to just open the browser.

    Returns:
        dict with browser session status and current page details.
    """
    try:
        runtime = await launch_browser_session(tool_context.session.id, start_url=start_url)
        observation = await capture_observation(
            tool_context.session.id,
            include_screenshot=False,
        )
        tool_context.state["browser"] = await build_browser_state(runtime, observation)
        return {
            "status": "success",
            "message": "Browser launched.",
            "current_url": observation["url"] if observation else runtime.page.url,
            "title": observation["title"] if observation else await runtime.page.title(),
            "user_data_dir": runtime.user_data_dir,
            "headless": runtime.headless,
        }
    except Exception as exc:
        return {"status": "error", "error_message": str(exc)}


async def open_url(url: str, tool_context: ToolContext) -> dict:
    """Open a URL in the current browser session.

    Args:
        url: Fully qualified URL to navigate to.

    Returns:
        dict with navigation status and page metadata.
    """
    if not url:
        return {"status": "error", "error_message": "URL is required."}

    try:
        if has_runtime(tool_context.session.id):
            runtime = get_runtime(tool_context.session.id)
            await runtime.page.goto(url, wait_until="domcontentloaded")
        else:
            runtime = await launch_browser_session(tool_context.session.id, start_url=url)
        observation = await capture_observation(
            tool_context.session.id,
            include_screenshot=False,
        )
        tool_context.state["browser"] = await build_browser_state(runtime, observation)
        return {
            "status": "success",
            "message": f"Opened {url}",
            "current_url": observation["url"],
            "title": observation["title"],
        }
    except Exception as exc:
        return {"status": "error", "error_message": str(exc)}


async def click(selector: str, tool_context: ToolContext) -> dict:
    """Click the first visible element that matches a selector.

    Args:
        selector: Playwright selector, usually copied from the page summary or read_page.

    Returns:
        dict with click status and the resulting page metadata.
    """
    if not selector:
        return {"status": "error", "error_message": "Selector is required."}

    try:
        runtime = get_runtime(tool_context.session.id)
        await runtime.page.locator(selector).first.click()
        if runtime.context.pages:
            runtime.page = runtime.context.pages[-1]
        observation = await capture_observation(
            tool_context.session.id,
            include_screenshot=False,
        )
        await _sync_browser_state(tool_context, observation)
        return {
            "status": "success",
            "message": f"Clicked {selector}",
            "current_url": observation["url"],
            "title": observation["title"],
        }
    except Exception as exc:
        return {"status": "error", "error_message": str(exc)}


async def type_text(selector: str, text: str, press_enter: bool, tool_context: ToolContext) -> dict:
    """Fill an input-like element with text.

    Args:
        selector: Playwright selector for the target input element.
        text: Text to enter into the element.
        press_enter: Whether to press Enter after filling the text.

    Returns:
        dict with input status and the resulting page metadata.
    """
    if not selector:
        return {"status": "error", "error_message": "Selector is required."}

    try:
        runtime = get_runtime(tool_context.session.id)
        locator = runtime.page.locator(selector).first
        await locator.fill(text)
        if press_enter:
            await runtime.page.keyboard.press("Enter")
        observation = await capture_observation(
            tool_context.session.id,
            include_screenshot=False,
        )
        await _sync_browser_state(tool_context, observation)
        return {
            "status": "success",
            "message": f"Filled {selector}",
            "current_url": observation["url"],
            "title": observation["title"],
        }
    except Exception as exc:
        return {"status": "error", "error_message": str(exc)}


async def press_key(key: str, tool_context: ToolContext) -> dict:
    """Press a keyboard key in the active page.

    Args:
        key: Playwright key name such as Enter, Tab, Escape, ArrowDown, or Control+L.

    Returns:
        dict with key press status and page metadata.
    """
    if not key:
        return {"status": "error", "error_message": "Key is required."}

    try:
        runtime = get_runtime(tool_context.session.id)
        await runtime.page.keyboard.press(key)
        observation = await capture_observation(
            tool_context.session.id,
            include_screenshot=False,
        )
        await _sync_browser_state(tool_context, observation)
        return {
            "status": "success",
            "message": f"Pressed {key}",
            "current_url": observation["url"],
            "title": observation["title"],
        }
    except Exception as exc:
        return {"status": "error", "error_message": str(exc)}


async def scroll(direction: str, amount: int, tool_context: ToolContext) -> dict:
    """Scroll the active page vertically.

    Args:
        direction: Either "down" or "up".
        amount: Number of pixels to scroll.

    Returns:
        dict with scroll status and page metadata.
    """
    direction_normalized = direction.strip().lower()
    if direction_normalized not in {"down", "up"}:
        return {"status": "error", "error_message": 'Direction must be "down" or "up".'}

    try:
        runtime = get_runtime(tool_context.session.id)
        delta = amount if direction_normalized == "down" else -amount
        await runtime.page.mouse.wheel(0, delta)
        observation = await capture_observation(
            tool_context.session.id,
            include_screenshot=False,
        )
        await _sync_browser_state(tool_context, observation)
        return {
            "status": "success",
            "message": f"Scrolled {direction_normalized} by {amount}px",
            "current_url": observation["url"],
            "title": observation["title"],
        }
    except Exception as exc:
        return {"status": "error", "error_message": str(exc)}


async def wait_for(selector: str, text: str, seconds: float, tool_context: ToolContext) -> dict:
    """Wait for a selector or visible text to appear.

    Args:
        selector: Selector to wait for. Pass an empty string if waiting by text instead.
        text: Visible text to wait for. Pass an empty string if waiting by selector instead.
        seconds: Maximum wait time in seconds.

    Returns:
        dict with wait status and page metadata.
    """
    if not selector and not text:
        return {
            "status": "error",
            "error_message": "Provide either a selector or text to wait for.",
        }

    try:
        runtime = get_runtime(tool_context.session.id)
        timeout_ms = int(seconds * 1000)
        if selector:
            await runtime.page.locator(selector).first.wait_for(
                state="visible",
                timeout=timeout_ms,
            )
        else:
            await runtime.page.locator(f"text={text}").first.wait_for(
                state="visible",
                timeout=timeout_ms,
            )
        observation = await capture_observation(
            tool_context.session.id,
            include_screenshot=False,
        )
        await _sync_browser_state(tool_context, observation)
        target = selector if selector else f"text={text}"
        return {
            "status": "success",
            "message": f"Waited for {target}",
            "current_url": observation["url"],
            "title": observation["title"],
        }
    except Exception as exc:
        return {"status": "error", "error_message": str(exc)}


async def read_page(tool_context: ToolContext) -> dict:
    """Return a structured summary of the current page for planning and debugging.

    Returns:
        dict with URL, title, visible text excerpt, focused element, and suggested selectors.
    """
    try:
        observation = await capture_observation(
            tool_context.session.id,
            include_screenshot=False,
        )
        if observation is None:
            return {
                "status": "error",
                "error_message": "No live browser session. Launch the browser first.",
            }
        await _sync_browser_state(tool_context, observation)
        return {
            "status": "success",
            "url": observation["url"],
            "title": observation["title"],
            "text_excerpt": observation["textExcerpt"],
            "focused_element": observation["focusedElement"],
            "elements": observation["elements"],
        }
    except Exception as exc:
        return {"status": "error", "error_message": str(exc)}


async def close_browser(tool_context: ToolContext) -> dict:
    """Close the current browser session and release Playwright resources.

    Returns:
        dict with close status.
    """
    closed = await close_browser_session(tool_context.session.id)
    tool_context.state["browser"] = {"active": False}
    if not closed:
        return {"status": "not_found", "message": "Browser session was not running."}
    return {"status": "success", "message": "Browser session closed."}
