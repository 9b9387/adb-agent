"""Session-scoped key-value blackboard for the ADB automation agent."""

from agent_shared.memo import read_memo, write_memo

__all__ = ["write_memo", "read_memo"]
