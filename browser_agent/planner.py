"""Standalone planning step for browser automation tasks."""

import json
import os

from google import genai
from google.genai import types

PLANNING_PROMPT = """You are a browser automation planning assistant. Decompose the following task into clear ordered steps for a Playwright-based browser automation agent.

Return valid JSON only:
{{
  "goal": "<concise restatement of the task>",
  "steps": ["<step 1 action>", "<step 2 action>", ...],
  "done_conditions": ["<observable browser fact confirming step 1 is done>", ...]
}}

Rules:
- 1–5 steps maximum
- Each done_condition must be a concrete fact verifiable from the current page state, such as URL, title, visible text, button state, or form contents
- steps and done_conditions must have the same length
- Avoid vague done_conditions like "probably logged in" or "looks correct"

Task: {task}"""


def generate_plan(task: str) -> dict:
    """Call the LLM to generate a structured browser execution plan."""
    client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
    model_name = os.getenv("MODEL_NAME", "gemini-3-flash-preview")

    response = client.models.generate_content(
        model=model_name,
        contents=PLANNING_PROMPT.format(task=task),
        config=types.GenerateContentConfig(
            temperature=0.1,
            response_mime_type="application/json",
        ),
    )

    data = json.loads(response.text)
    return {
        "goal": data["goal"],
        "steps": data["steps"],
        "done_conditions": data["done_conditions"],
        "current_step": 0,
        "completed_observations": [],
    }
