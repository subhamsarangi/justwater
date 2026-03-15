import asyncpg
import uuid
from datetime import datetime, timezone
from config import DATABASE_URL

_pool: asyncpg.Pool = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(DATABASE_URL)
    return _pool


async def init_db():
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id           TEXT PRIMARY KEY,
                prompt       TEXT NOT NULL,
                status       TEXT NOT NULL DEFAULT 'pending',
                image_path   TEXT,
                image_url    TEXT,
                duration_ms  INTEGER,
                error_message TEXT,
                nsfw_flagged BOOLEAN DEFAULT FALSE,
                created_at   TIMESTAMPTZ NOT NULL
            )
        """
        )


async def create_job(prompt: str) -> str:
    job_id = str(uuid.uuid4())
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO jobs (id, prompt, status, created_at)
               VALUES ($1, $2, 'pending', $3)""",
            job_id,
            prompt,
            datetime.now(timezone.utc),
        )
    return job_id


async def update_job_done(
    job_id: str, image_path: str, image_url: str, duration_ms: int, nsfw_flagged: bool
):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """UPDATE jobs SET status='done', image_path=$1, image_url=$2,
               duration_ms=$3, nsfw_flagged=$4 WHERE id=$5""",
            image_path,
            image_url,
            duration_ms,
            nsfw_flagged,
            job_id,
        )


async def update_job_failed(job_id: str, error_message: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE jobs SET status='failed', error_message=$1 WHERE id=$2",
            error_message,
            job_id,
        )


async def get_job(job_id: str) -> dict | None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM jobs WHERE id=$1", job_id)
    return dict(row) if row else None


async def get_all_jobs() -> list[dict]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM jobs ORDER BY created_at DESC")
    return [dict(r) for r in rows]
