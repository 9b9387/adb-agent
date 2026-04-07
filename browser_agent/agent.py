"""Playwright browser automation agent definition."""

import os

from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.genai import types

from agent_shared.callbacks import record_tool_usage

from .callbacks import inject_browser_observation
from .prompts import SYSTEM_INSTRUCTION
from .tools import ALL_TOOLS

load_dotenv()

model_name = os.getenv("MODEL_NAME", "gemini-3-flash-preview")
vllm_base_url = os.getenv("VLLM_BASE_URL")

if vllm_base_url:
    model = LiteLlm(model=f"openai/{model_name}", api_base=vllm_base_url, api_key="dummy")
else:
    model = model_name

root_agent = Agent(
    name="browser_agent",
    model=model,
    instruction=SYSTEM_INSTRUCTION,
    tools=ALL_TOOLS,
    before_model_callback=inject_browser_observation,
    before_tool_callback=record_tool_usage,
    generate_content_config=types.GenerateContentConfig(temperature=0.2),
)
