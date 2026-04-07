"""PostgreSQL connection management, schema initialization, and upsert helpers."""

import os
import re
import asyncpg
from dotenv import load_dotenv

load_dotenv()

_pool: asyncpg.Pool | None = None


def _get_database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL not set. Example: postgresql://agent:passowrd@192.168.8.109:5432/agent_db"
        )
    return url


async def get_pool() -> asyncpg.Pool:
    """Return (and lazily create) a connection pool."""
    global _pool
    if _pool is None or _pool._closed:
        _pool = await asyncpg.create_pool(_get_database_url(), min_size=1, max_size=5)
    return _pool


async def close_pool():
    global _pool
    if _pool and not _pool._closed:
        await _pool.close()
        _pool = None


async def init_db():
    """Create tables and indexes if they don't exist."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto";')

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS douban_books (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                douban_url VARCHAR(2048) NOT NULL UNIQUE,
                title VARCHAR(512) NOT NULL,
                subtitle VARCHAR(512) DEFAULT '',
                author TEXT DEFAULT '',
                translator TEXT DEFAULT '',
                publisher VARCHAR(256) DEFAULT '',
                publish_date VARCHAR(64) DEFAULT '',
                pages VARCHAR(32) DEFAULT '',
                price VARCHAR(64) DEFAULT '',
                isbn VARCHAR(32) DEFAULT '',
                rating VARCHAR(16) DEFAULT '',
                rating_count VARCHAR(32) DEFAULT '',
                summary TEXT DEFAULT '',
                cover_url VARCHAR(2048) DEFAULT '',
                tags TEXT DEFAULT '',
                info_block TEXT DEFAULT '',
                source_mode VARCHAR(32) NOT NULL DEFAULT 'new_books',
                raw_data JSONB DEFAULT '{}'::jsonb,
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            );
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS douban_ingestion_runs (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                source_mode VARCHAR(32) NOT NULL,
                query TEXT DEFAULT '',
                total_fetched INT DEFAULT 0,
                total_inserted INT DEFAULT 0,
                total_updated INT DEFAULT 0,
                total_skipped INT DEFAULT 0,
                status VARCHAR(32) DEFAULT 'running',
                started_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                finished_at TIMESTAMPTZ
            );
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_douban_books_source ON douban_books(source_mode);
            CREATE INDEX IF NOT EXISTS idx_douban_books_rating ON douban_books(rating);
        """)


async def upsert_book(book: dict) -> str:
    """Insert or update a book record. Returns 'inserted' or 'updated'."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        existing = await conn.fetchval(
            "SELECT id FROM douban_books WHERE douban_url = $1", book["douban_url"]
        )
        if existing:
            await conn.execute(
                """
                UPDATE douban_books SET
                    title=$2, subtitle=$3, author=$4, translator=$5,
                    publisher=$6, publish_date=$7, pages=$8, price=$9, isbn=$10,
                    rating=$11, rating_count=$12, summary=$13, cover_url=$14,
                    tags=$15, info_block=$16, source_mode=$17, raw_data=$18,
                    updated_at=CURRENT_TIMESTAMP
                WHERE douban_url=$1
                """,
                book["douban_url"], book.get("title", ""), book.get("subtitle", ""),
                book.get("author", ""), book.get("translator", ""),
                book.get("publisher", ""), book.get("publish_date", ""),
                book.get("pages", ""), book.get("price", ""), book.get("isbn", ""),
                book.get("rating", ""), book.get("rating_count", ""),
                book.get("summary", ""), book.get("cover_url", ""),
                book.get("tags", ""), book.get("info_block", ""),
                book.get("source_mode", "new_books"), book.get("raw_data", "{}"),
            )
            return "updated"
        else:
            await conn.execute(
                """
                INSERT INTO douban_books (
                    douban_url, title, subtitle, author, translator,
                    publisher, publish_date, pages, price, isbn,
                    rating, rating_count, summary, cover_url,
                    tags, info_block, source_mode, raw_data
                ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18)
                """,
                book["douban_url"], book.get("title", ""), book.get("subtitle", ""),
                book.get("author", ""), book.get("translator", ""),
                book.get("publisher", ""), book.get("publish_date", ""),
                book.get("pages", ""), book.get("price", ""), book.get("isbn", ""),
                book.get("rating", ""), book.get("rating_count", ""),
                book.get("summary", ""), book.get("cover_url", ""),
                book.get("tags", ""), book.get("info_block", ""),
                book.get("source_mode", "new_books"), book.get("raw_data", "{}"),
            )
            return "inserted"


async def get_existing_subject_ids() -> set[str]:
    """Return the set of all Douban subject IDs already stored in the database.

    Extracts the numeric ID from each stored douban_url so the scraper can
    deduplicate against the local database without fetching remote pages.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT douban_url FROM douban_books")
    ids: set[str] = set()
    for row in rows:
        m = re.search(r'/subject/(\d+)/', row["douban_url"])
        if m:
            ids.add(m.group(1))
    return ids


async def create_ingestion_run(source_mode: str, query: str = "") -> str:
    """Create a new ingestion run record and return its id."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO douban_ingestion_runs (source_mode, query)
            VALUES ($1, $2) RETURNING id
            """,
            source_mode, query,
        )
        return str(row["id"])


async def finish_ingestion_run(run_id: str, total_fetched: int, inserted: int, updated: int, skipped: int, status: str = "completed"):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE douban_ingestion_runs SET
                total_fetched=$2, total_inserted=$3, total_updated=$4,
                total_skipped=$5, status=$6, finished_at=CURRENT_TIMESTAMP
            WHERE id=$1::uuid
            """,
            run_id, total_fetched, inserted, updated, skipped, status,
        )
