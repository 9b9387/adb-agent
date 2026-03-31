"""ADB automation agent definition."""

import os

from dotenv import load_dotenv
from google.adk.agents import Agent
from google.genai import types

load_dotenv()

from .callbacks import enforce_plan, inject_screenshot
from .prompts import SYSTEM_INSTRUCTION
from .tools import ALL_TOOLS

model_name = os.getenv("MODEL_NAME", "gemini-2.5-flash")

root_agent = Agent(
    name="adb_agent",
    model=model_name,
    instruction=SYSTEM_INSTRUCTION,
    tools=ALL_TOOLS,
    before_model_callback=inject_screenshot,
    before_tool_callback=enforce_plan,
    generate_content_config=types.GenerateContentConfig(temperature=0.2),
)
