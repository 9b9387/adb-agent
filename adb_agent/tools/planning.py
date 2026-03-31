"""Planning tools for the Plan-as-Tool architecture."""

from google.adk.tools import ToolContext


def create_plan(
    task_goal: str,
    steps: list[str],
    done_conditions: list[str],
    tool_context: ToolContext,
) -> dict:
    """Create an execution plan. MUST be called before any tap/swipe/type actions.

    Analyze the current screenshot, decompose the task into ordered steps,
    and define observable done_conditions for each step.

    Args:
        task_goal: What we're trying to accomplish.
        steps: Ordered action steps. Each step = one UI interaction or verification.
        done_conditions: One per step. Observable visual facts that confirm the step is done.
                        Must be verifiable from screenshot (e.g. "Search results page loaded").
                        NOT subjective (e.g. "User is satisfied").
        tool_context: ADK ToolContext — provides session state access.
    Returns:
        dict with plan confirmation and step summary.
    """
    if len(steps) != len(done_conditions):
        return {
            "status": "error",
            "error_message": f"steps ({len(steps)}) and done_conditions ({len(done_conditions)}) must have same length",
        }
    if len(steps) == 0:
        return {"status": "error", "error_message": "Plan must have at least 1 step"}

    tool_context.state["plan"] = {
        "goal": task_goal,
        "steps": steps,
        "done_conditions": done_conditions,
        "current_step": 0,
        "completed_observations": [],
    }
    return {
        "status": "success",
        "message": f"Plan created: {len(steps)} steps",
        "current_step": 0,
        "current_action": steps[0],
        "current_done_condition": done_conditions[0],
    }


def advance_plan(observation: str, tool_context: ToolContext) -> dict:
    """Mark the current plan step as done and advance to the next step.

    Call this when the current step's done_condition is visually confirmed
    in the screenshot.

    Args:
        observation: Brief description of what you see that confirms the step is done.
        tool_context: ADK ToolContext — provides session state access.
    Returns:
        dict with next step info, or signal that all steps are complete.
    """
    plan = tool_context.state.get("plan")
    if plan is None:
        return {"status": "error", "error_message": "No plan exists. Call create_plan first."}
    if plan["current_step"] >= len(plan["steps"]):
        return {"status": "error", "error_message": "All steps already complete."}

    plan["completed_observations"].append(observation)
    plan["current_step"] += 1
    tool_context.state["plan"] = plan  # write back to session state

    if plan["current_step"] >= len(plan["steps"]):
        return {
            "status": "all_steps_complete",
            "message": "All plan steps completed. Task will terminate automatically.",
        }

    i = plan["current_step"]
    return {
        "status": "success",
        "message": f"Advanced to step {i + 1}/{len(plan['steps'])}",
        "current_action": plan["steps"][i],
        "current_done_condition": plan["done_conditions"][i],
    }
