"""CLI entry point for the Playwright browser automation agent."""

import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

from agent_shared.runtime import run_planned_task
from browser_agent.agent import root_agent
from browser_agent.planner import generate_plan

load_dotenv()

APP_NAME = "browser_agent"
USER_ID = "user"


async def run_task(task: str):
    """Run the browser agent with the given task prompt."""
    await run_planned_task(
        task,
        app_name=APP_NAME,
        user_id=USER_ID,
        agent=root_agent,
        planner=generate_plan,
    )


def check_environment():
    """Check whether the browser automation environment is usable."""
    if not os.getenv("GOOGLE_API_KEY") or os.getenv("GOOGLE_API_KEY") == "your-api-key-here":
        print("[!] Error: GOOGLE_API_KEY is not set or invalid. Please check your .env file.")
        sys.exit(1)

    cdp_url = os.getenv("BROWSER_CDP_URL")
    if cdp_url:
        return

    try:
        with sync_playwright() as playwright:
            executable_path = Path(playwright.chromium.executable_path)
            if not executable_path.exists():
                print(
                    "[!] Error: Chromium is not installed for Playwright.\n"
                    "Run: uv run playwright install chromium"
                )
                sys.exit(1)
    except Exception as exc:
        print(f"[!] Error: Failed to initialize Playwright: {exc}")
        sys.exit(1)


def main():
    check_environment()

    if len(sys.argv) < 2:
        print("Usage: python browser_main.py <task>")
        print('Example: python browser_main.py "打开 GitHub 并搜索 google/adk"')
        sys.exit(1)

    task = " ".join(sys.argv[1:])
    try:
        asyncio.run(run_task(task))
    except KeyboardInterrupt:
        print("\n\n[!] Task manually terminated by user.")
        sys.exit(0)


if __name__ == "__main__":
    main()
