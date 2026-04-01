"""Playwright browser automation agent definition."""

import os

from dotenv import load_dotenv
from google.adk.agents import Agent
from google.genai import types

from agent_shared.callbacks import record_tool_usage

from .callbacks import inject_browser_observation
from .prompts import SYSTEM_INSTRUCTION
from .tools import ALL_TOOLS

load_dotenv()

model_name = os.getenv("MODEL_NAME", "gemini-3-flash-preview")

root_agent = Agent(
    name="browser_agent",
    model=model_name,
    instruction=SYSTEM_INSTRUCTION,
    tools=ALL_TOOLS,
    before_model_callback=inject_browser_observation,
    before_tool_callback=record_tool_usage,
    generate_content_config=types.GenerateContentConfig(temperature=0.2),
)
