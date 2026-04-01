"""Session-scoped key-value blackboard for plan-loop agents."""

from google.adk.tools import ToolContext


def write_memo(key: str, value: str, tool_context: ToolContext) -> dict:
    """Save a value to the session blackboard so it can be retrieved later.

    Args:
        key: A short identifier for the stored value.
        value: The string value to store.

    Returns:
        dict with status and the key that was written.
    """
    memo = tool_context.state.get("memo", {})
    memo[key] = value
    tool_context.state["memo"] = memo
    return {"status": "success", "key": key}


def read_memo(key: str, tool_context: ToolContext) -> dict:
    """Retrieve a value previously saved with write_memo.

    Args:
        key: The identifier used when the value was stored.

    Returns:
        dict with the stored value, or status "not_found".
    """
    memo = tool_context.state.get("memo", {})
    if key not in memo:
        return {"status": "not_found", "key": key}
    return {"status": "success", "key": key, "value": memo[key]}
