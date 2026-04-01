"""Callback functions for the ADB automation agent."""

import time

from google.adk.models import LlmResponse
from google.genai import types

from agent_shared.callbacks import record_tool_usage
from agent_shared.constants import MAX_STEPS

from .tools.screen import resize_screenshot, take_screenshot

# Tools after which screenshot injection is skipped (non-visual operations).
NO_SCREENSHOT_TOOLS = {"push_file", "pull_file", "write_memo", "read_memo"}


def enforce_plan(tool, args, tool_context):
    """before_tool_callback: tracks action history and last tool name in session state."""
    return record_tool_usage(tool, args, tool_context)


def inject_screenshot(callback_context, llm_request):
    """before_model_callback: injects screenshot + plan context.

    If plan is complete, returns Content directly to short-circuit the LLM
    and terminate the runner loop.
    """
    plan = callback_context.state.get("plan")

    # Short-circuit: plan complete → end turn without calling LLM
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

    # Skip screenshot for non-visual tools (file transfers, etc.)
    skip_screenshot = callback_context.state.get("last_tool_name") in NO_SCREENSHOT_TOOLS

    image_part = None
    if not skip_screenshot:
        # Take screenshot + wait for screen to settle after ADB actions
        try:
            time.sleep(1)
            png_bytes = take_screenshot()
            jpeg_bytes = resize_screenshot(png_bytes, max_size=640)
            image_part = types.Part.from_bytes(data=jpeg_bytes, mime_type="image/jpeg")
        except Exception as e:
            llm_request.contents.append(types.Content(
                role="user",
                parts=[types.Part.from_text(text=f"[Screenshot failed: {e}]")],
            ))
            return None

    lines = [f"[Step {step_count}/{MAX_STEPS}]"]
    if plan:
        step_display = plan["current_step"] + 1
        total = len(plan["steps"])
        lines += [
            f'📋 PLAN: "{plan["goal"]}" (Step {step_display}/{total})',
            f'   Current: "{plan["steps"][plan["current_step"]]}"',
            f'   Done when: "{plan["done_conditions"][plan["current_step"]]}"',
        ]
        # Show last 3 completed steps
        start_idx = max(0, len(plan["completed_observations"]) - 3)
        for j, obs in enumerate(plan["completed_observations"][-3:]):
            idx = start_idx + j
            lines.append(f'   ✅ Step {idx + 1}: "{plan["steps"][idx]}" → "{obs}"')

    # Action history (last 10)
    if action_history:
        lines.append("[Action History]:")
        for i, action in enumerate(action_history[-10:], 1):
            lines.append(f"  {i}. {action}")

    if image_part is not None:
        lines.append("")
        lines.append("Current phone screen:")
        parts = [types.Part.from_text(text="\n".join(lines)), image_part]
    else:
        lines.append("")
        lines.append("[Screenshot skipped — non-visual operation]")
        parts = [types.Part.from_text(text="\n".join(lines))]

    llm_request.contents.append(types.Content(role="user", parts=parts))
    return None
