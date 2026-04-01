"""Tests for browser agent callbacks."""

import asyncio
from types import SimpleNamespace

from browser_agent.callbacks import inject_browser_observation


def run(coro):
    return asyncio.run(coro)


def test_browser_callback_injects_page_summary(monkeypatch):
    callback_context = SimpleNamespace(
        state={
            "plan": {
                "goal": "Search the page",
                "steps": ["Open the page", "Use the search box"],
                "done_conditions": ["Page title is visible", "Search results are visible"],
                "current_step": 0,
                "completed_observations": [],
            },
            "action_history": ['open_url(url="https://example.com")'],
        },
        session=SimpleNamespace(id="browser-callback-test"),
    )
    llm_request = SimpleNamespace(contents=[])

    async def fake_capture_observation(session_id, include_screenshot=True):
        return {
            "url": "https://example.com",
            "title": "Example Domain",
            "textExcerpt": "Welcome to the example page",
            "focusedElement": {
                "tag": "input",
                "text": "",
                "ariaLabel": "",
                "name": "search",
                "placeholder": "Search",
            },
            "elements": [
                {
                    "tag": "button",
                    "text": "Continue",
                    "ariaLabel": "",
                    "placeholder": "",
                    "testId": "",
                    "id": "",
                    "name": "",
                    "suggestedSelectors": ["text=Continue"],
                }
            ],
            "screenshot_bytes": b"fake-jpeg",
        }

    monkeypatch.setattr(
        "browser_agent.callbacks.capture_observation",
        fake_capture_observation,
    )

    result = run(inject_browser_observation(callback_context, llm_request))

    assert result is None
    assert len(llm_request.contents) == 1
    text_part = llm_request.contents[0].parts[0].text
    assert 'Current page title: "Example Domain"' in text_part
    assert "Suggested interactive elements:" in text_part
    assert "text=Continue" in text_part


def test_browser_callback_short_circuits_when_plan_complete():
    callback_context = SimpleNamespace(
        state={
            "plan": {
                "goal": "Finish task",
                "steps": ["Only step"],
                "done_conditions": ["Complete"],
                "current_step": 1,
                "completed_observations": ["Everything is done"],
            }
        },
        session=SimpleNamespace(id="done-session"),
    )
    llm_request = SimpleNamespace(contents=[])

    response = run(inject_browser_observation(callback_context, llm_request))

    assert response is not None
    assert response.turn_complete is True
    assert "任务完成" in response.content.parts[0].text
