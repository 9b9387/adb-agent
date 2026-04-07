"""Team coordinator agent — routes user requests to specialist sub-agents."""

import os

from dotenv import load_dotenv
from google.adk.agents import Agent
from google.genai import types

load_dotenv()

from .prompts import SYSTEM_INSTRUCTION

# Import the specialist agents
from adb_agent.agent import root_agent as adb_agent
from skills_agent.agent import root_agent as skills_agent
from scraper_agent.agent import root_agent as scraper_agent

model_name = os.getenv("MODEL_NAME", "gemini-2.5-flash")

root_agent = Agent(
    name="agent_team",
    model=model_name,
    description="Team coordinator that delegates tasks to specialist agents.",
    instruction=SYSTEM_INSTRUCTION,
    sub_agents=[adb_agent, skills_agent, scraper_agent],
    generate_content_config=types.GenerateContentConfig(temperature=0.2),
)
