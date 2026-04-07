import os
import json
import httpx
import asyncpg
from typing import Dict, Any, Optional
from urllib.parse import urlparse
from google.genai import types

# Import the extraction strategy from local crawl4ai package
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy

# Global cache to store raw data so the LLM doesn't have to pass it back
CRAWL_CACHE = {}

class Crawl4aiTool:
    """
    Tool to crawl a webpage using the crawl4ai service running on Docker.
    """
    
    def __init__(self, base_url: str = "http://localhost:11235"):
        self.base_url = base_url
        
    async def crawl_url(self, url: str, wait_for: Optional[str] = None, css_selector: Optional[str] = None, extraction_schema: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Crawls the given URL using crawl4ai and returns the extracted data.
        """
        endpoint = f"{self.base_url}/crawl"
        payload = {"urls": [url]}
        
        # 配置爬虫参数
        crawler_config = {
            "headers": {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            }
        }
        
        if css_selector:
            crawler_config["css_selector"] = css_selector
            
        if wait_for:
            crawler_config["wait_for"] = wait_for
            
        payload["crawler_config"] = crawler_config
            
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(endpoint, json=payload, timeout=60.0)
                response.raise_for_status()
                data = response.json()
                if data.get("success") and data.get("results"):
                    raw_result = data["results"][0]
                    
                    # 如果提供了 extraction_schema，我们在本地使用 crawl4ai 解析返回的 HTML
                    if extraction_schema:
                        try:
                            strategy = JsonCssExtractionStrategy(extraction_schema)
                            html_content = raw_result.get("html", "")
                            extracted_data = strategy.extract(url, html_content)
                            
                            simplified_result = {
                                "url": url,
                                "title": raw_result.get("metadata", {}).get("title", ""),
                                "extracted_data": extracted_data,
                                "error": raw_result.get("error_message", "")
                            }
                            
                            # 保存到全局缓存
                            CRAWL_CACHE[url] = simplified_result
                            
                            print("\n" + "="*50)
                            print(f"🚀 CRAWL RESULT (STRUCTURED) FOR LLM (URL: {url})")
                            print("="*50)
                            print(json.dumps(extracted_data, indent=2, ensure_ascii=False))
                            print("="*50 + "\n")
                            
                            return simplified_result
                        except Exception as parse_e:
                            return {"error": f"Failed to parse with schema: {parse_e}", "url": url}
                    
                    # 提取主要信息，避免将整个 HTML 塞给 LLM 导致 Token 超限
                    markdown_data = raw_result.get("markdown", {})
                    # 优先使用经过可读性过滤的 markdown，如果没有则使用原始 markdown
                    content = markdown_data.get("fit_markdown") or markdown_data.get("raw_markdown") or ""
                    
                    # 如果内容仍然过长，进行截断 (约 20000 字符)
                    if len(content) > 20000:
                        content = content[:20000] + "\n\n...[内容过长已截断]..."
                        
                    simplified_result = {
                        "url": raw_result.get("url") or url,
                        "title": raw_result.get("metadata", {}).get("title", ""),
                        "description": raw_result.get("metadata", {}).get("description", ""),
                        "content": content,
                        "error": raw_result.get("error_message", "")
                    }
                    
                    # 保存到全局缓存，避免 LLM 回传超大文本
                    CRAWL_CACHE[simplified_result["url"]] = simplified_result
                    CRAWL_CACHE[url] = simplified_result
                    
                    # 打印给 LLM 的内容，方便调试查看
                    print("\n" + "="*50)
                    print(f"🚀 CRAWL RESULT FOR LLM (URL: {url})")
                    print("="*50)
                    print(f"TITLE: {simplified_result['title']}")
                    print(f"DESCRIPTION: {simplified_result['description']}")
                    print(f"ERROR: {simplified_result['error']}")
                    print(f"CONTENT LENGTH: {len(simplified_result['content'])} characters")
                    print("-" * 50)
                    print(simplified_result['content'][:1500] + ("\n...[终端显示截断，实际发送给LLM的内容更长]..." if len(simplified_result['content']) > 1500 else ""))
                    print("="*50 + "\n")
                    
                    return simplified_result
                return data
            except Exception as e:
                return {"error": str(e), "url": url}

    def get_tool_definition(self) -> types.Tool:
        """Returns the ADK Tool definition for this tool."""
        return types.Tool(
            function_declarations=[
                types.FunctionDeclaration(
                    name="crawl_url",
                    description="Crawls a webpage using crawl4ai to extract its content.",
                    parameters=types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            "url": types.Schema(
                                type=types.Type.STRING,
                                description="The URL of the webpage to crawl."
                            ),
                            "wait_for": types.Schema(
                                type=types.Type.STRING,
                                description="Optional CSS selector to wait for before extracting data."
                            ),
                            "css_selector": types.Schema(
                                type=types.Type.STRING,
                                description="Optional CSS selector to extract only a specific part of the page (e.g., '#content > div > div.article')."
                            ),
                            "extraction_schema": types.Schema(
                                type=types.Type.OBJECT,
                                description="Optional JSON schema for structured extraction using CSS selectors (e.g., {'name': 'Book', 'baseSelector': '#wrapper', 'fields': [{'name': 'title', 'selector': 'h1', 'type': 'text'}]})."
                            )
                        },
                        required=["url"]
                    )
                )
            ]
        )


class DatabaseTool:
    """
    Tool to interact with the PostgreSQL database.
    """
    def __init__(self, db_url: str):
        self.db_url = db_url

    async def save_to_db(self, url: str, ai_content: Dict[str, Any], status: str = "ai_processed") -> Dict[str, Any]:
        """
        Saves the crawled data and AI content to the PostgreSQL database.
        """
        domain = urlparse(url).netloc
        ai_content_json = json.dumps(ai_content, ensure_ascii=False)
        
        # Retrieve raw_data from cache to avoid LLM token limits
        raw_data = CRAWL_CACHE.get(url, {})
        raw_data_json = json.dumps(raw_data, ensure_ascii=False)
        
        try:
            conn = await asyncpg.connect(self.db_url)
            await conn.execute('''
                INSERT INTO scraped_items (url, domain, raw_data, ai_content, status)
                VALUES ($1, $2, $3::jsonb, $4::jsonb, $5)
                ON CONFLICT (url) DO UPDATE SET
                    raw_data = EXCLUDED.raw_data,
                    ai_content = EXCLUDED.ai_content,
                    status = EXCLUDED.status,
                    updated_at = CURRENT_TIMESTAMP;
            ''', url, domain, raw_data_json, ai_content_json, status)
            await conn.close()
            return {"status": "success", "message": f"Successfully saved {url} to database."}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_tool_definition(self) -> types.Tool:
        """Returns the ADK Tool definition for this tool."""
        return types.Tool(
            function_declarations=[
                types.FunctionDeclaration(
                    name="save_to_db",
                    description="Saves the crawled raw data and generated AI content to the PostgreSQL database.",
                    parameters=types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            "url": types.Schema(
                                type=types.Type.STRING,
                                description="The URL of the webpage that was crawled."
                            ),
                            "ai_content": types.Schema(
                                type=types.Type.OBJECT,
                                description="The AI generated summary and tags."
                            ),
                            "status": types.Schema(
                                type=types.Type.STRING,
                                description="The status of the item, e.g., 'ai_processed'."
                            )
                        },
                        required=["url", "ai_content"]
                    )
                )
            ]
        )
