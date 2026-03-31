"""CLI entry point for the ADB automation agent."""

import asyncio
import os
import shutil
import subprocess
import sys

from dotenv import load_dotenv
load_dotenv()

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from adb_agent.agent import root_agent
from adb_agent.callbacks import MAX_STEPS

APP_NAME = "adb_agent"
USER_ID = "user"


async def run_task(task: str):
    """Run the agent with the given task prompt."""
    session_service = InMemorySessionService()
    runner = Runner(
        agent=root_agent,
        app_name=APP_NAME,
        session_service=session_service,
    )

    session = await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
    )

    message = types.Content(
        role="user",
        parts=[types.Part.from_text(text=task)],
    )

    print(f"Task: {task}")
    print("-" * 60)

    step_count = 0
    max_steps = MAX_STEPS

    async for event in runner.run_async(
        user_id=USER_ID,
        session_id=session.id,
        new_message=message,
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    print(f"[{event.author}] {part.text}")
                elif part.function_call:
                    step_count += 1
                    print(f"[Step {step_count}/{max_steps}] Tool Call: {part.function_call.name}({part.function_call.args})")
                    
                    if step_count >= max_steps:
                        print(f"\n[!] Reached maximum step limit ({max_steps}). Forcing exit to prevent infinite loops.")
                        return
                elif part.function_response:
                    print(f"[Tool Result] {part.function_response.response}")


def check_environment():
    """Check if the environment is properly configured before running."""
    # 1. Check API Key
    if not os.getenv("GOOGLE_API_KEY") or os.getenv("GOOGLE_API_KEY") == "your-api-key-here":
        print("[!] 错误: GOOGLE_API_KEY 未配置或无效。请检查 .env 文件。")
        sys.exit(1)
        
    # 2. Check if ADB is installed
    if not shutil.which("adb"):
        print("[!] 错误: 未找到 adb 命令。请先确保已安装 Android SDK Platform-Tools 并且已加入环境变量。")
        sys.exit(1)
        
    # 3. Check if any Android devices are connected
    try:
        result = subprocess.run(["adb", "devices"], capture_output=True, text=True, check=True)
        lines = result.stdout.strip().splitlines()
        # Header is "List of devices attached", valid devices follow that line
        devices = [line for line in lines[1:] if line.strip() and not line.startswith("*")]
        if not devices:
            print("[!] 错误: 未检测到连接的 Android 设备。")
            print("请确认：\n 1. 数据线已连接\n 2. 手机已开启“开发者选项”及“USB调试”\n 3. 手机屏幕上已允许本机的调试授权")
            sys.exit(1)
    except Exception as e:
        print(f"[!] 错误: 执行 adb devices 时发生异常: {e}")
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
