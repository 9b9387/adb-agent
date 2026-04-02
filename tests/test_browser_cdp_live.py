"""Optional live CDP smoke test against an already-running Chrome."""

import os
import urllib.request

import pytest
from playwright.sync_api import sync_playwright

DEFAULT_CDP_URL = "http://127.0.0.1:9222"


def _require_live_cdp() -> str:
    """Skip unless the user explicitly enables the live CDP smoke test."""
    if os.getenv("RUN_LIVE_CDP_TEST") != "1":
        pytest.skip("Set RUN_LIVE_CDP_TEST=1 to run the live CDP smoke test.")

    cdp_url = os.getenv("BROWSER_CDP_URL", DEFAULT_CDP_URL).rstrip("/")
    
    # If the user provided a raw WebSocket URL (e.g. from Chrome M144+ autoConnect),
    # we bypass the HTTP /json/version check and assume it's valid.
    if cdp_url.startswith("ws://") or cdp_url.startswith("wss://"):
        return cdp_url

    version_url = f"{cdp_url}/json/version"

    try:
        with urllib.request.urlopen(version_url, timeout=3) as response:
            if response.status != 200:
                pytest.skip(f"CDP endpoint is unavailable at {version_url}.")
    except Exception as exc:
        pytest.skip(f"CDP endpoint is unavailable at {version_url}: {exc}")

    return cdp_url


def test_connect_to_existing_cdp_browser_and_capture_current_page(tmp_path):
    cdp_url = _require_live_cdp()
    screenshot_path = tmp_path / "current_screen.png"

    with sync_playwright() as playwright:
        browser = playwright.chromium.connect_over_cdp(cdp_url)

        assert browser.contexts, "No browser contexts found on the remote Chrome instance."
        default_context = browser.contexts[0]

        assert default_context.pages, "No open pages found in the remote Chrome instance."
        page = default_context.pages[0]

        title = page.title()
        print(f"当前页面标题: {title}")

        page.screenshot(path=str(screenshot_path))
        print(f"截图已保存: {screenshot_path}")

        assert screenshot_path.exists()

        # Python sync API does not expose browser.disconnect().
        # Exiting sync_playwright() tears down the local client without calling browser.close().
