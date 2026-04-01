"""Shared callback helpers for plan-loop agents."""


def record_tool_usage(tool, args, tool_context):
    """Track tool calls in session state for later prompt injection."""
    action_history = tool_context.state.get("action_history", [])
    formatted_args = ", ".join(f"{key}={value}" for key, value in args.items())
    action = f"{tool.name}({formatted_args})" if formatted_args else f"{tool.name}()"
    action_history.append(action)
    tool_context.state["action_history"] = action_history
    tool_context.state["last_tool_name"] = tool.name
    return None
