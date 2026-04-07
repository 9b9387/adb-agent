import asyncio
import os
import asyncpg
from dotenv import load_dotenv

load_dotenv()

async def init_db():
    # Ensure you have DATABASE_URL in your .env file
    # e.g., DATABASE_URL=postgresql://user:password@localhost:5432/dbname
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL not found in environment variables.")
        return

    print(f"Connecting to database...")
    conn = await asyncpg.connect(db_url)
    
    try:
        print("Creating extension pgcrypto...")
        await conn.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto";')
        
        print("Creating table scraped_items...")
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS scraped_items (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                url VARCHAR(2048) NOT NULL UNIQUE,
                domain VARCHAR(255) NOT NULL,
                raw_data JSONB NOT NULL DEFAULT '{}'::jsonb,
                ai_content JSONB DEFAULT '{}'::jsonb,
                status VARCHAR(50) NOT NULL DEFAULT 'pending',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        
        print("Creating indexes...")
        await conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_scraped_items_domain ON scraped_items(domain);
            CREATE INDEX IF NOT EXISTS idx_scraped_items_status ON scraped_items(status);
        ''')
        
        print("Database initialization completed successfully.")
    except Exception as e:
        print(f"Error initializing database: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(init_db())
