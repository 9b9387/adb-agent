"""Callback functions for the Playwright browser automation agent."""

from google.adk.models import LlmResponse
from google.genai import types

from agent_shared.constants import MAX_STEPS
from browser_agent.runtime_registry import capture_observation


def _describe_element(element: dict) -> str:
    label = element.get("text") or element.get("ariaLabel") or element.get("placeholder") or element.get("name") or element.get("id") or "unnamed"
    selectors = ", ".join(element.get("suggestedSelectors", [])[:2])
    if selectors:
        return f'{element["tag"]}: "{label}" | selectors: {selectors}'
    return f'{element["tag"]}: "{label}"'


def inject_browser_observation(callback_context, llm_request):
    """Inject browser observation and plan context before each model turn."""
    plan = callback_context.state.get("plan")

    if plan and plan["current_step"] >= len(plan["steps"]):
        observations = "; ".join(plan["completed_observations"])
        summary = f"✅ 任务完成: {plan['goal']}\n步骤回顾: {observations}"
        return LlmResponse(
            content=types.Content(role="model", parts=[types.Part.from_text(text=summary)]),
            turn_complete=True,
        )

    step_count = callback_context.state.get("step_count", 0) + 1
    callback_context.state["step_count"] = step_count

    action_history = callback_context.state.get("action_history", [])
    lines = [f"[Step {step_count}/{MAX_STEPS}]"]

    if plan:
        current_index = plan["current_step"]
        total_steps = len(plan["steps"])
        lines.extend(
            [
                f'📋 PLAN: "{plan["goal"]}" (Step {current_index + 1}/{total_steps})',
                f'   Current: "{plan["steps"][current_index]}"',
                f'   Done when: "{plan["done_conditions"][current_index]}"',
            ]
        )

        start_index = max(0, len(plan["completed_observations"]) - 3)
        for offset, observation in enumerate(plan["completed_observations"][-3:]):
            plan_index = start_index + offset
            lines.append(
                f'   ✅ Step {plan_index + 1}: "{plan["steps"][plan_index]}" → "{observation}"'
            )

    if action_history:
        lines.append("[Action History]:")
        for index, action in enumerate(action_history[-10:], start=1):
            lines.append(f"  {index}. {action}")

    try:
        observation = capture_observation(callback_context.session.id, include_screenshot=True)
    except Exception as exc:
        llm_request.contents.append(
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=f"[Browser observation failed: {exc}]")],
            )
        )
        return None

    if observation is None:
        lines.extend(
            [
                "",
                "[No active browser session]",
                "Use `launch_browser` or `open_url` to start the browser for this plan.",
            ]
        )
        parts = [types.Part.from_text(text="\n".join(lines))]
        llm_request.contents.append(types.Content(role="user", parts=parts))
        return None

    lines.extend(
        [
            "",
            f'Current page title: "{observation["title"]}"',
            f'Current URL: {observation["url"]}',
        ]
    )

    if observation.get("focusedElement"):
        focused = observation["focusedElement"]
        focused_label = (
            focused.get("text")
            or focused.get("ariaLabel")
            or focused.get("placeholder")
            or focused.get("name")
            or "unnamed"
        )
        lines.append(f'Focused element: {focused["tag"]} "{focused_label}"')

    if observation.get("textExcerpt"):
        lines.append(f'Visible text excerpt: "{observation["textExcerpt"]}"')

    if observation.get("elements"):
        lines.append("Suggested interactive elements:")
        for element in observation["elements"][:6]:
            lines.append(f"  - {_describe_element(element)}")

    parts = [types.Part.from_text(text="\n".join(lines))]
    if observation.get("screenshot_bytes") is not None:
        parts.append(
            types.Part.from_bytes(
                data=observation["screenshot_bytes"],
                mime_type="image/jpeg",
            )
        )

    llm_request.contents.append(types.Content(role="user", parts=parts))
    return None
