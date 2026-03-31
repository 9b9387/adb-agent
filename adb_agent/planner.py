"""Standalone planning step: generates a structured plan before the agent loop."""

import json
import os

from google import genai
from google.genai import types

PLANNING_PROMPT = """You are a phone automation planning assistant. Decompose the following task into clear ordered steps for an Android automation agent.

Return valid JSON only:
{{
  "goal": "<concise restatement of the task>",
  "steps": ["<step 1 action>", "<step 2 action>", ...],
  "done_conditions": ["<observable visual fact confirming step 1 is done>", ...]
}}

Rules:
- 1–5 steps maximum
- Each done_condition must be a concrete visual fact verifiable from a screenshot (e.g. "Search results page is showing", "Red heart icon is visible")
- steps and done_conditions must have the same length

Task: {task}"""


def generate_plan(task: str) -> dict:
    """Call the LLM to generate a structured execution plan.

    Returns a plan dict ready to insert into ADK session state.
    """
    client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
    model_name = os.getenv("MODEL_NAME", "gemini-2.5-flash")

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
