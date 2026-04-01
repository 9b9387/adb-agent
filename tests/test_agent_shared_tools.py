"""Tests for shared plan-loop tools."""

from agent_shared.memo import read_memo
from agent_shared.memo import write_memo
from agent_shared.planning import advance_plan


class FakeToolContext:
    """Minimal ToolContext stand-in for unit tests."""

    def __init__(self, state=None):
        self.state = state or {}


def test_advance_plan_moves_to_next_step():
    tool_context = FakeToolContext(
        {
            "plan": {
                "goal": "Complete a task",
                "steps": ["Open page", "Submit form"],
                "done_conditions": ["Page is visible", "Success message is visible"],
                "current_step": 0,
                "completed_observations": [],
            }
        }
    )

    result = advance_plan("Page is visible", tool_context)

    assert result["status"] == "success"
    assert tool_context.state["plan"]["current_step"] == 1
    assert tool_context.state["plan"]["completed_observations"] == ["Page is visible"]
    assert result["current_action"] == "Submit form"


def test_memo_round_trip():
    tool_context = FakeToolContext()

    write_memo("target_url", "https://example.com", tool_context)
    result = read_memo("target_url", tool_context)

    assert result == {
        "status": "success",
        "key": "target_url",
        "value": "https://example.com",
    }
