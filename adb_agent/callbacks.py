"""Callback functions for the ADB automation agent."""

import asyncio
import os
import time

from google.adk.models import LlmResponse
from google.genai import types

from .tools.adb import resize_screenshot, take_screenshot

MAX_STEPS = 30

# Tools after which screenshot injection is skipped (non-visual operations).
NO_SCREENSHOT_TOOLS = {"push_file", "pull_file", "write_memo", "read_memo", "update_plan", "create_plan"}


async def enforce_plan(tool, args, tool_context):
    """before_tool_callback: tracks action history and last tool name in session state."""
    action_history = tool_context.state.get("action_history", [])
    action_str = f"{tool.name}({', '.join(f'{k}={v}' for k, v in args.items())})"
    action_history.append(action_str)
    tool_context.state["action_history"] = action_history
    return None  # allow tool execution


async def inject_screenshot(callback_context, llm_request):
    """before_model_callback: injects screenshot + plan context.

    If plan is complete, returns Content directly to short-circuit the LLM
    and terminate the runner loop.
    """
    plan = callback_context.state.get("plan")

    # Short-circuit: plan complete → end turn without calling LLM
    if plan and plan["current_step"] >= len(plan["steps"]):
        observations = "\n".join(plan["completed_observations"])
        summary = f"✅ 任务完成: {plan['goal']}\n步骤回顾: {observations}"
        return LlmResponse(
            content=types.Content(role="model", parts=[types.Part.from_text(text=summary)]),
            turn_complete=True,
        )

    step_count = callback_context.state.get("step_count", 0) + 1
    callback_context.state["step_count"] = step_count

    action_history = callback_context.state.get("action_history", [])

    image_part = None
    
    if not action_history:
        # First turn: take the initial screenshot
        try:
            png_bytes = await asyncio.to_thread(take_screenshot)
            jpeg_bytes = await asyncio.to_thread(resize_screenshot, png_bytes, 640)
            image_part = types.Part.from_bytes(data=jpeg_bytes, mime_type="image/jpeg")
        except Exception as e:
            llm_request.contents.append(types.Content(
                role="user",
                parts=[types.Part.from_text(text=f"[Screenshot failed: {e}]")],
            ))
            return None
    else:
        # Not the first turn: ALWAYS take a fresh screenshot
        # We no longer reuse the screenshot from observe_action_result
        try:
            png_bytes = await asyncio.to_thread(take_screenshot)
            jpeg_bytes = await asyncio.to_thread(resize_screenshot, png_bytes, 640)
            image_part = types.Part.from_bytes(data=jpeg_bytes, mime_type="image/jpeg")
        except Exception as e:
            llm_request.contents.append(types.Content(
                role="user",
                parts=[types.Part.from_text(text=f"[Screenshot failed: {e}]")],
            ))
            return None
    # Else: Not the first turn, and no cached screenshot -> it was a NO_SCREENSHOT_TOOL, skip screenshot.

    lines = [f"[Step {step_count}/{MAX_STEPS}]"]
    if plan:
        step_display = plan["current_step"] + 1
        total = len(plan["steps"])
        lines += [
            f'📋 PLAN: "{plan["goal"]}" (Step {step_display}/{total})',
            f'   Current: "{plan["steps"][plan["current_step"]]}"',
        ]
        # Show last 3 completed steps
        start_idx = max(0, len(plan["completed_observations"]) - 3)
        for j, obs in enumerate(plan["completed_observations"][-3:]):
            idx = start_idx + j
            lines.append(f'   ✅ Step {idx + 1}: "{plan["steps"][idx]}" → "{obs}"')
    else:
        lines += [
            "📋 PLAN: No plan created yet. You MUST call `create_plan` first."
        ]

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


async def observe_action_result(tool, args, tool_response, tool_context) -> dict | None:
    """after_tool_callback: uses a vision model to observe the result of the action."""
    tool_name = tool.name
    ctx = tool_context
    
    if tool_name in NO_SCREENSHOT_TOOLS:
        return None
        
    try:
        from google import genai
        
        await asyncio.sleep(1)
        png_bytes = await asyncio.to_thread(take_screenshot)
        jpeg_bytes = await asyncio.to_thread(resize_screenshot, png_bytes, 640)
        image_part = types.Part.from_bytes(data=jpeg_bytes, mime_type="image/jpeg")
        
        use_local_llm = os.getenv("USE_LOCAL_LLM", "false").lower() == "true"
        model_name = os.getenv("MODEL_NAME", "gemini-3-flash-preview")
        
        prompt = f"The agent just executed the tool `{tool_name}`. Look at the current screenshot. Briefly describe what changed or what the current screen shows, and whether the action seemed successful. Keep it under 2 sentences."
        
        if use_local_llm:
            from litellm import acompletion
            import base64
            vllm_base_url = os.getenv("VLLM_BASE_URL")
            
            base64_image = base64.b64encode(jpeg_bytes).decode('utf-8')
            image_url = f"data:image/jpeg;base64,{base64_image}"
            
            response = await acompletion(
                model=f"openai/{model_name}",
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_url}}
                    ]
                }],
                api_base=vllm_base_url,
                api_key="dummy",
                temperature=0.1
            )
            observation = response.choices[0].message.content
        else:
            client = genai.Client(api_key=os.environ.get("GOOGLE_API_KEY", "dummy"))
            # Use asyncio.to_thread for the synchronous genai client to avoid blocking the event loop
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=model_name,
                contents=[prompt, image_part],
                config=types.GenerateContentConfig(temperature=0.1),
            )
            observation = response.text
            
        print(f"\n[Observation] {observation}\n")
        
        # Update the last action in action_history with the observation
        action_history = ctx.state.get("action_history", [])
        if action_history:
            last_action = action_history[-1]
            action_history[-1] = f"{last_action} -> Observation: {observation}"
            ctx.state["action_history"] = action_history
            
        # Add observation to the tool result
        if isinstance(tool_response, dict):
            new_result = dict(tool_response)
            new_result["visual_observation"] = observation
            return new_result
        else:
            return tool_response
            
    except Exception as e:
        print(f"Observation failed: {e}")
        obs_text = f"[观测模型调用失败: {e}]"
        
        action_history = ctx.state.get("action_history", [])
        if action_history:
            last_action = action_history[-1]
            action_history[-1] = f"{last_action} -> Observation: {obs_text}"
            ctx.state["action_history"] = action_history
            
        if isinstance(tool_response, dict):
            new_result = dict(tool_response)
            new_result["visual_observation"] = obs_text
            return new_result
        return tool_response
