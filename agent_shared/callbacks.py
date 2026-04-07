"""Shared callback helpers for plan-loop agents."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

SENSITIVE_ARG_NAMES = {
    "file_path",
    "password",
    "secret",
    "text",
    "token",
    "value",
}

SENSITIVE_ARG_SUBSTRINGS = ("password", "secret", "token", "cookie", "api_key")


def _is_sensitive_arg(name: str) -> bool:
    lowered = name.lower()
    return lowered in SENSITIVE_ARG_NAMES or any(
        fragment in lowered for fragment in SENSITIVE_ARG_SUBSTRINGS
    )


def _safe_repr(value: Any) -> str:
    rendered = repr(value)
    return rendered if len(rendered) <= 80 else f"{rendered[:77]}..."


def redact_tool_args(args: Mapping[str, Any] | None) -> dict[str, Any]:
    """Return a redacted copy of tool args safe for prompts and logs."""
    if not args:
        return {}

    redacted: dict[str, Any] = {}
    for key, value in args.items():
        if _is_sensitive_arg(key):
            redacted[key] = "<redacted>"
        else:
            redacted[key] = value
    return redacted


def format_tool_call(tool_name: str, args: Mapping[str, Any] | None) -> str:
    """Format a tool call for prompt injection or terminal output."""
    safe_args = redact_tool_args(args)
    if not safe_args:
        return f"{tool_name}()"

    formatted_args = ", ".join(
        f"{key}={_safe_repr(value)}" for key, value in safe_args.items()
    )
    return f"{tool_name}({formatted_args})"


def record_tool_usage(tool, args, tool_context):
    """Track tool calls in session state for later prompt injection."""
    action_history = tool_context.state.get("action_history", [])
    action = format_tool_call(tool.name, args)
    action_history.append(action)
    tool_context.state["action_history"] = action_history
    tool_context.state["last_tool_name"] = tool.name
    return None
