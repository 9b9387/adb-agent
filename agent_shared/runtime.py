"""Shared runtime loop for plan-first ADK agents."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from .constants import MAX_STEPS


async def run_planned_task(
    task: str,
    *,
    app_name: str,
    user_id: str,
    agent,
    planner: Callable[[str], dict[str, Any]],
    initial_state: dict[str, Any] | None = None,
    max_steps: int = MAX_STEPS,
) -> None:
    """Run a plan-first ADK agent from task planning through tool loop."""
    print(f"Task: {task}")
    print("Planning...")
    plan = planner(task)
    print(f"Plan: {plan['goal']} ({len(plan['steps'])} steps)")
    for index, (step, done_condition) in enumerate(
        zip(plan["steps"], plan["done_conditions"]),
        start=1,
    ):
        print(f"  {index}. {step} → done when: {done_condition}")
    print("-" * 60)

    session_service = InMemorySessionService()
    runner = Runner(
        agent=agent,
        app_name=app_name,
        session_service=session_service,
    )

    state = {"plan": plan}
    if initial_state:
        state.update(initial_state)

    session = await session_service.create_session(
        app_name=app_name,
        user_id=user_id,
        state=state,
    )

    message = types.Content(
        role="user",
        parts=[types.Part.from_text(text=task)],
    )

    step_count = 0
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session.id,
        new_message=message,
    ):
        if not event.content or not event.content.parts:
            continue

        for part in event.content.parts:
            if part.text:
                print(f"[{event.author}] {part.text}")
                continue

            if part.function_call:
                step_count += 1
                print(
                    f"[Step {step_count}/{max_steps}] Tool Call: "
                    f"{part.function_call.name}({part.function_call.args})"
                )
                if step_count >= max_steps:
                    print(
                        f"\n[!] Reached maximum step limit ({max_steps}). "
                        "Forcing exit to prevent infinite loops."
                    )
                    return
                continue

            if part.function_response:
                print(f"[Tool Result] {part.function_response.response}")
