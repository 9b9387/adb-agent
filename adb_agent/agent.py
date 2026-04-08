"""ADB automation agent definition."""

import os

from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.genai import types

load_dotenv()

# Remove SOCKS proxies from environment to prevent httpx from crashing
# when socksio is not installed.
for key in list(os.environ.keys()):
    if key.lower() in ('http_proxy', 'https_proxy', 'all_proxy'):
        if os.environ[key].lower().startswith('socks'):
            del os.environ[key]

from .callbacks import enforce_plan, inject_screenshot, observe_action_result
from .prompts import SYSTEM_INSTRUCTION
from .tools import ALL_TOOLS

model = os.getenv("MODEL_NAME", "gemini-3-flash-preview")
use_local_llm = os.getenv("USE_LOCAL_LLM", "false").lower() == "true"

if use_local_llm:
    vllm_base_url = os.getenv("VLLM_BASE_URL")
    model = LiteLlm(
        model=f"openai/{model}",
        api_base=vllm_base_url,
        api_key="dummy"
    )

root_agent = Agent(
    name="adb_agent",
    model=model,
    instruction=SYSTEM_INSTRUCTION,
    tools=ALL_TOOLS,
    before_model_callback=inject_screenshot,
    before_tool_callback=enforce_plan,
    after_tool_callback=observe_action_result,
    generate_content_config=types.GenerateContentConfig(temperature=0.2),
)
