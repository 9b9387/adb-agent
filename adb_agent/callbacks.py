"""Callback functions for the ADB automation agent."""

import time

from google.adk.models import LlmResponse
from google.genai import types

from .tools.screen import resize_screenshot, take_screenshot

MAX_STEPS = 30

# Tools that require a plan before execution (mutating actions)
GATED_TOOLS = {
    "adb_shell", "tap", "long_press", "double_tap", "swipe", "type_text", "press_keycode",
    "push_file", "pull_file",
}


def enforce_plan(tool, args, tool_context):
    """before_tool_callback: blocks gated tools if no plan exists, tracks action history."""
    tool_name = tool.name

    # Track action in session state
    action_history = tool_context.state.get("action_history", [])
    action_str = f"{tool_name}({', '.join(f'{k}={v}' for k, v in args.items())})"
    action_history.append(action_str)
    tool_context.state["action_history"] = action_history

    # Enforce plan gating
    if tool_name in GATED_TOOLS and tool_context.state.get("plan") is None:
        return {
            "status": "error",
            "error_message": "No plan created yet. You MUST call create_plan before any action.",
        }
    return None  # allow tool execution


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

    # Normal path: take screenshot and inject context
    step_count = callback_context.state.get("step_count", 0) + 1
    callback_context.state["step_count"] = step_count

    action_history = callback_context.state.get("action_history", [])

    try:
        time.sleep(1)  # wait for screen to settle after ADB actions
        png_bytes = take_screenshot()
        jpeg_bytes = resize_screenshot(png_bytes, max_size=640)
        image_part = types.Part.from_bytes(data=jpeg_bytes, mime_type="image/jpeg")
    except Exception as e:
        error_content = types.Content(
            role="user",
            parts=[types.Part.from_text(text=f"[Screenshot failed: {e}]")],
        )
        llm_request.contents.append(error_content)
        return None

    lines = [f"[Step {step_count}/{MAX_STEPS}]"]

    # Plan context injection
    if plan is None:
        lines.append("⚠️ NO PLAN — you MUST call create_plan before any other action.")
    else:
        step_display = plan["current_step"] + 1
        total = len(plan["steps"])
        lines.append(f'📋 PLAN: "{plan["goal"]}" (Step {step_display}/{total})')
        lines.append(f'   Current: "{plan["steps"][plan["current_step"]]}"')
        lines.append(f'   Done when: "{plan["done_conditions"][plan["current_step"]]}"')
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

    lines.append("")
    lines.append("Current phone screen:")

    context_text = "\n".join(lines)
    text_part = types.Part.from_text(text=context_text)

    screenshot_content = types.Content(
        role="user",
        parts=[text_part, image_part],
    )
    llm_request.contents.append(screenshot_content)
    return None
