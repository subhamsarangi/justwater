import asyncpg
import uuid
from datetime import datetime, timezone
from config import DATABASE_URL, OWNER_EMAIL

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
            CREATE TABLE IF NOT EXISTS users (
                id           TEXT PRIMARY KEY,
                email        TEXT UNIQUE NOT NULL,
                name         TEXT,
                avatar_url   TEXT,
                password_hash TEXT,
                google_id    TEXT UNIQUE,
                role         TEXT NOT NULL DEFAULT 'user',
                tokens_used  INTEGER NOT NULL DEFAULT 0,
                created_at   TIMESTAMPTZ NOT NULL
            )
        """
        )
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id            TEXT PRIMARY KEY,
                user_id       TEXT REFERENCES users(id),
                prompt        TEXT NOT NULL,
                status        TEXT NOT NULL DEFAULT 'pending',
                image_path    TEXT,
                image_url     TEXT,
                duration_ms   INTEGER,
                error_message TEXT,
                nsfw_flagged  BOOLEAN DEFAULT FALSE,
                tokens_used   INTEGER DEFAULT 0,
                created_at    TIMESTAMPTZ NOT NULL
            )
        """
        )
        # seed owner row
        if OWNER_EMAIL:
            existing = await conn.fetchrow(
                "SELECT id FROM users WHERE email=$1", OWNER_EMAIL
            )
            if not existing:
                await conn.execute(
                    """INSERT INTO users (id, email, name, role, created_at)
                       VALUES ($1, $2, 'Owner', 'owner', $3)""",
                    str(uuid.uuid4()),
                    OWNER_EMAIL,
                    datetime.now(timezone.utc),
                )


# ── Users ──────────────────────────────────────────────────────────────────


async def get_user_by_id(user_id: str) -> dict | None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM users WHERE id=$1", user_id)
    return dict(row) if row else None


async def get_user_by_email(email: str) -> dict | None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM users WHERE email=$1", email)
    return dict(row) if row else None


async def get_user_by_google_id(google_id: str) -> dict | None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM users WHERE google_id=$1", google_id)
    return dict(row) if row else None


async def create_user(
    email: str,
    name: str = None,
    password_hash: str = None,
    google_id: str = None,
    avatar_url: str = None,
) -> dict:
    pool = await get_pool()
    user_id = str(uuid.uuid4())
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """INSERT INTO users (id, email, name, password_hash, google_id, avatar_url, created_at)
               VALUES ($1,$2,$3,$4,$5,$6,$7) RETURNING *""",
            user_id,
            email,
            name,
            password_hash,
            google_id,
            avatar_url,
            datetime.now(timezone.utc),
        )
    return dict(row)


async def update_user_tokens(user_id: str, tokens: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET tokens_used = tokens_used + $1 WHERE id=$2",
            tokens,
            user_id,
        )


async def get_user_stats(user_id: str) -> dict:
    pool = await get_pool()
    async with pool.acquire() as conn:
        total = await conn.fetchval(
            "SELECT COUNT(*) FROM jobs WHERE user_id=$1", user_id
        )
        done = await conn.fetchval(
            "SELECT COUNT(*) FROM jobs WHERE user_id=$1 AND status='done'", user_id
        )
        failed = await conn.fetchval(
            "SELECT COUNT(*) FROM jobs WHERE user_id=$1 AND status='failed'", user_id
        )
        tokens = await conn.fetchval(
            "SELECT tokens_used FROM users WHERE id=$1", user_id
        )
    return {"total": total, "done": done, "failed": failed, "tokens_used": tokens or 0}


# ── Jobs ───────────────────────────────────────────────────────────────────


async def create_job(prompt: str, user_id: str = None) -> str:
    job_id = str(uuid.uuid4())
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO jobs (id, user_id, prompt, status, created_at)
               VALUES ($1, $2, 'pending', $3, $4)""",
            job_id,
            user_id,
            prompt,
            datetime.now(timezone.utc),
        )
    return job_id


async def update_job_done(
    job_id: str,
    image_path: str,
    image_url: str,
    duration_ms: int,
    nsfw_flagged: bool,
    tokens_used: int = 0,
):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """UPDATE jobs SET status='done', image_path=$1, image_url=$2,
               duration_ms=$3, nsfw_flagged=$4, tokens_used=$5 WHERE id=$6""",
            image_path,
            image_url,
            duration_ms,
            nsfw_flagged,
            tokens_used,
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


async def get_all_jobs(user_id: str = None) -> list[dict]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        if user_id:
            rows = await conn.fetch(
                "SELECT * FROM jobs WHERE user_id=$1 ORDER BY created_at DESC", user_id
            )
        else:
            rows = await conn.fetch("SELECT * FROM jobs ORDER BY created_at DESC")
    return [dict(r) for r in rows]
