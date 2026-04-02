"""
Optional live CDP smoke test against an already-running Chrome.
"""

import pytest
from playwright.sync_api import sync_playwright

CDP_URL = "ws://127.0.0.1:9222/devtools/browser"

def test_connect_to_existing_cdp_browser_and_capture_current_page(tmp_path):
    screenshot_path = tmp_path / "current_screen.png"

    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.connect_over_cdp(CDP_URL)
        except Exception as exc:
            pytest.fail(
                f"Failed to connect to CDP URL {CDP_URL}.\n"
                f"If using ws://, did you accept the Chrome prompt?\n"
                f"Error: {exc}"
            )

        assert browser.contexts, "No browser contexts found on the remote Chrome instance."
        default_context = browser.contexts[0]

        assert default_context.pages, "No open pages found in the remote Chrome instance."
        page = default_context.pages[0]

        title = page.title()
        print(f"当前页面标题: {title}")

        page.screenshot(path=str(screenshot_path))
        print(f"截图已保存: {screenshot_path}")

        assert screenshot_path.exists()
