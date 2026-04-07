"""CLI entry point for the agent team coordinator."""

import asyncio
import os
import sys

from dotenv import load_dotenv

load_dotenv()

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from agent_team.agent import root_agent

APP_NAME = "agent_team"
USER_ID = "user"


async def run_task(task: str):
    """Run the team coordinator with the given task prompt."""
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
                    print(f"[{event.author}] Tool: {part.function_call.name}({part.function_call.args})")
                elif part.function_response:
                    resp = str(part.function_response.response)
                    if len(resp) > 500:
                        resp = resp[:500] + "..."
                    print(f"[Tool Result] {resp}")


def check_environment():
    """Check if the environment is properly configured."""
    if not os.getenv("GOOGLE_API_KEY") or os.getenv("GOOGLE_API_KEY") == "your-api-key-here":
        print("[!] Error: GOOGLE_API_KEY is not set. Please check your .env file.")
        sys.exit(1)


def main():
    check_environment()

    if len(sys.argv) < 2:
        print("Usage: agent-team <task>")
        print('Example: agent-team "帮我收集豆瓣最新的新书信息"')
        sys.exit(1)

    task = " ".join(sys.argv[1:])
    try:
        asyncio.run(run_task(task))
    except KeyboardInterrupt:
        print("\n\n[!] Task manually terminated by user.")
        sys.exit(0)


if __name__ == "__main__":
    main()
