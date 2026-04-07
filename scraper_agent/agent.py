"""Scraper agent — Douban book ingestion specialist."""

import os

from dotenv import load_dotenv
from google.adk.agents import Agent
from google.genai import types

load_dotenv()

from .prompts import SYSTEM_INSTRUCTION
from .tools import ALL_TOOLS

model_name = os.getenv("MODEL_NAME", "gemini-2.5-flash")

root_agent = Agent(
    name="scraper_agent",
    model=model_name,
    description=(
        "An agent that collects book information from Douban (book.douban.com). "
        "It can fetch the latest new books, search by keyword, extract detailed "
        "book metadata, and persist everything to the database. "
        "Delegate to this agent when the user asks about collecting, scraping, "
        "or ingesting Douban book data."
    ),
    instruction=SYSTEM_INSTRUCTION,
    tools=ALL_TOOLS,
    generate_content_config=types.GenerateContentConfig(temperature=0.2),
)
