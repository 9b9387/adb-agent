"""Database persistence tool — wraps db.py for use by the scraper agent."""

import json
from typing import Any, Dict, List

from google.adk.tools import ToolContext

from scraper_agent.db import (
    init_db,
    upsert_book,
    create_ingestion_run,
    finish_ingestion_run,
)


async def save_books_to_db(
    books: List[Dict[str, Any]],
    source_mode: str = "new_books",
    query: str = "",
    tool_context: ToolContext = None,
) -> Dict[str, Any]:
    """Save a list of book records to the PostgreSQL database.

    Each book dict should contain at minimum 'douban_url' and 'title'.
    Performs idempotent upserts keyed by douban_url.
    Records the ingestion run with stats.

    Args:
        books: List of normalized book dicts (from fetch/search/detail tools).
        source_mode: Either 'new_books', 'search', or 'detail'.
        query: The search query if source_mode is 'search'; empty otherwise.

    Returns:
        dict with status, total_fetched, inserted, updated, skipped counts,
        and a brief summary string.
    """
    await init_db()
    run_id = await create_ingestion_run(source_mode, query)

    inserted = 0
    updated = 0
    skipped = 0
    errors: List[str] = []

    for book in books:
        if not book.get("douban_url"):
            skipped += 1
            continue
        # Ensure raw_data is a JSON string
        if "raw_data" not in book:
            book["raw_data"] = json.dumps(book, ensure_ascii=False)
        book["source_mode"] = source_mode
        try:
            result = await upsert_book(book)
            if result == "inserted":
                inserted += 1
            else:
                updated += 1
        except Exception as e:
            skipped += 1
            errors.append(f"{book.get('title', 'unknown')}: {e}")

    total = len(books)
    status = "completed" if not errors else "partial"
    await finish_ingestion_run(run_id, total, inserted, updated, skipped, status)

    summary_lines = [
        f"📚 入库完成 ({source_mode})",
        f"  抓取: {total} 本, 新增: {inserted}, 更新: {updated}, 跳过: {skipped}",
    ]
    if query:
        summary_lines.insert(1, f"  关键词: {query}")
    if errors:
        summary_lines.append(f"  ⚠️ 失败: {'; '.join(errors[:5])}")

    summary = "\n".join(summary_lines)

    # Persist summary in session state if available
    if tool_context:
        tool_context.state["last_ingestion_summary"] = summary
        tool_context.state["last_ingestion_stats"] = {
            "total_fetched": total,
            "inserted": inserted,
            "updated": updated,
            "skipped": skipped,
            "source_mode": source_mode,
            "query": query,
        }

    return {
        "status": status,
        "total_fetched": total,
        "inserted": inserted,
        "updated": updated,
        "skipped": skipped,
        "summary": summary,
    }
