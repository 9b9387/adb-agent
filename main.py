"""CLI entry point for the ADB automation agent."""

import asyncio
import os
import shutil
import subprocess
import sys

from dotenv import load_dotenv
load_dotenv()

from adb_agent.agent import root_agent
from adb_agent.planner import generate_plan
from agent_shared.runtime import run_planned_task

APP_NAME = "adb_agent"
USER_ID = "user"


async def run_task(task: str):
    """Run the agent with the given task prompt."""
    await run_planned_task(
        task,
        app_name=APP_NAME,
        user_id=USER_ID,
        agent=root_agent,
        planner=generate_plan,
    )


def check_environment():
    """Check if the environment is properly configured before running."""
    # 1. Check API Key
    if not os.getenv("GOOGLE_API_KEY") or os.getenv("GOOGLE_API_KEY") == "your-api-key-here":
        print("[!] Error: GOOGLE_API_KEY is not set or invalid. Please check your .env file.")
        sys.exit(1)

    # 2. Check if ADB is installed
    if not shutil.which("adb"):
        print("[!] Error: 'adb' command not found. Please install Android SDK Platform-Tools and add it to your PATH.")
        sys.exit(1)

    # 3. Check if any Android devices are connected
    try:
        result = subprocess.run(["adb", "devices"], capture_output=True, text=True, check=True)
        lines = result.stdout.strip().splitlines()
        # Header is "List of devices attached", valid devices follow that line
        devices = [line for line in lines[1:] if line.strip() and not line.startswith("*")]
        if not devices:
            print("[!] Error: No Android device detected.")
            print(
                "Please check:\n"
                "  1. USB cable is connected\n"
                "  2. Developer Options and USB Debugging are enabled on the device\n"
                "  3. USB debugging authorization has been granted on the device screen"
            )
            sys.exit(1)
    except Exception as e:
        print(f"[!] Error: Failed to run 'adb devices': {e}")
        sys.exit(1)


def main():
    check_environment()
    
    if len(sys.argv) < 2:
        print("Usage: python main.py <task>")
        print('Example: python main.py "打开设置应用"')
        sys.exit(1)

    task = " ".join(sys.argv[1:])
    try:
        asyncio.run(run_task(task))
    except KeyboardInterrupt:
        print("\n\n[!] Task manually terminated by user.")
        sys.exit(0)


if __name__ == "__main__":
    main()
