"""Skills agent definition — discovers, loads, and applies agent skills."""

import os

from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.tools.load_web_page import load_web_page
from google.genai import types

load_dotenv()

from .prompts import SYSTEM_INSTRUCTION
from .tools import ALL_TOOLS

model_name = os.getenv("MODEL_NAME", "gemini-2.5-flash")

root_agent = Agent(
    name="skills_agent",
    model=model_name,
    description=(
        "An agent that discovers, loads, and applies agent skills (SKILL.md files) "
        "to help users accomplish domain-specific tasks."
    ),
    instruction=SYSTEM_INSTRUCTION,
    tools=[*ALL_TOOLS, load_web_page],
    generate_content_config=types.GenerateContentConfig(temperature=0.2),
)
