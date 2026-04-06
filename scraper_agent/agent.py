import os
from typing import Dict, Any, Optional

from google.adk.agents import Agent
from google.adk.tools import google_search

from scraper_agent.tools import Crawl4aiTool, DatabaseTool

# Initialize tools
crawler = Crawl4aiTool(os.getenv("CRAWL4AI_BASE_URL"))
db_tool = DatabaseTool(os.getenv("DATABASE_URL"))

# Create ADK-compatible tool functions
async def crawl_url(url: str, wait_for: Optional[str] = None, css_selector: Optional[str] = None, extraction_schema: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Crawls a webpage using crawl4ai to extract its content.
    
    Args:
        url: The URL of the webpage to crawl.
        wait_for: Optional CSS selector to wait for before extracting data.
        css_selector: Optional CSS selector to extract only a specific part of the page (e.g., '#content > div > div.article').
        extraction_schema: Optional JSON schema for structured extraction using CSS selectors.
    """
    return await crawler.crawl_url(url, wait_for, css_selector, extraction_schema)

async def save_to_db(url: str, ai_content: Dict[str, Any], status: str = "ai_processed") -> Dict[str, Any]:
    """
    Saves the crawled raw data and generated AI content to the PostgreSQL database.
    
    Args:
        url: The URL of the webpage that was crawled.
        ai_content: The AI generated summary and tags.
        status: The status of the item, e.g., 'ai_processed'.
    """
    return await db_tool.save_to_db(url, ai_content, status)

# Expose root_agent for ADK Web UI
root_agent = Agent(
    name="scraper_agent",
    model="gemini-2.5-flash",
    instruction=(
        "You are an intelligent web scraping and content processing agent. "
        "You have access to two tools: \n"
        "1. `crawl_url`: Use this to crawl web pages and extract raw data. You can optionally provide a `css_selector` to only extract a specific part of the page, or an `extraction_schema` (JSON schema) to extract structured data using CSS selectors directly.\n"
        "2. `save_to_db`: Use this to save the extracted raw data and your generated AI content (summary and tags) to a PostgreSQL database.\n\n"
        "When a user asks you to process a URL, you should:\n"
        "1. Call `crawl_url` to get the page content. If the user specifies a schema or fields to extract, use the `extraction_schema` argument.\n"
        "2. Analyze the crawled data to generate a short, engaging summary and relevant hashtags for social media.\n"
        "3. Call `save_to_db` with the `url` and `ai_content` (your summary and tags from step 2). The raw data is cached automatically and doesn't need to be passed.\n"
        "4. Give the user a friendly final response summarizing what you did."
    ),
    tools=[crawl_url, save_to_db]
)
