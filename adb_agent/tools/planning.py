"""Planning tools for the agent loop."""

from google.adk.tools import ToolContext


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
