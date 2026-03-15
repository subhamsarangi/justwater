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
                id            TEXT PRIMARY KEY,
                email         TEXT UNIQUE NOT NULL,
                name          TEXT,
                avatar_url    TEXT,
                password_hash TEXT,
                google_id     TEXT UNIQUE,
                role          TEXT NOT NULL DEFAULT 'user',
                tokens_used   INTEGER NOT NULL DEFAULT 0,
                onboarding_done BOOLEAN NOT NULL DEFAULT FALSE,
                created_at    TIMESTAMPTZ NOT NULL
            )
        """
        )
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS onboarding_answers (
                id         TEXT PRIMARY KEY,
                user_id    TEXT REFERENCES users(id) ON DELETE CASCADE,
                question   TEXT NOT NULL,
                answer     TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL
            )
        """
        )
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id              TEXT PRIMARY KEY,
                user_id         TEXT REFERENCES users(id),
                prompt_id       TEXT,
                style           TEXT DEFAULT 'watercolor',
                prompt          TEXT NOT NULL,
                status          TEXT NOT NULL DEFAULT 'pending',
                image_path      TEXT,
                image_url       TEXT,
                duration_ms     INTEGER,
                error_message   TEXT,
                nsfw_flagged    BOOLEAN DEFAULT FALSE,
                tokens_used     INTEGER DEFAULT 0,
                file_size_bytes BIGINT DEFAULT 0,
                created_at      TIMESTAMPTZ NOT NULL
            )
        """
        )
        await conn.execute(
            """ALTER TABLE users ADD COLUMN IF NOT EXISTS onboarding_done BOOLEAN NOT NULL DEFAULT FALSE"""
        )
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS onboarding_answers (
                id         TEXT PRIMARY KEY,
                user_id    TEXT REFERENCES users(id) ON DELETE CASCADE,
                question   TEXT NOT NULL,
                answer     TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL
            )
        """
        )
        if OWNER_EMAIL:
            existing = await conn.fetchrow(
                "SELECT id FROM users WHERE email=$1", OWNER_EMAIL
            )
            if not existing:
                await conn.execute(
                    "INSERT INTO users (id, email, name, role, created_at) VALUES ($1,$2,'Owner','owner',$3)",
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
        total_size = await conn.fetchval(
            "SELECT COALESCE(SUM(file_size_bytes), 0) FROM jobs WHERE user_id=$1 AND status='done'",
            user_id,
        )
    return {
        "total": total,
        "done": done,
        "failed": failed,
        "tokens_used": tokens or 0,
        "total_size_bytes": total_size or 0,
    }


# ── Jobs ───────────────────────────────────────────────────────────────────


async def create_job(
    prompt: str, user_id: str = None, prompt_id: str = None, style: str = "watercolor"
) -> str:
    job_id = str(uuid.uuid4())
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO jobs (id, user_id, prompt_id, style, prompt, status, created_at)
               VALUES ($1,$2,$3,$4,$5,'pending',$6)""",
            job_id,
            user_id,
            prompt_id,
            style,
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
    file_size_bytes: int = 0,
):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """UPDATE jobs SET status='done', image_path=$1, image_url=$2,
               duration_ms=$3, nsfw_flagged=$4, tokens_used=$5, file_size_bytes=$6 WHERE id=$7""",
            image_path,
            image_url,
            duration_ms,
            nsfw_flagged,
            tokens_used,
            file_size_bytes,
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


async def get_jobs_by_prompt_id(prompt_id: str) -> list[dict]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM jobs WHERE prompt_id=$1 ORDER BY style", prompt_id
        )
    return [dict(r) for r in rows]


async def get_all_jobs(user_id: str = None) -> list[dict]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        if user_id:
            rows = await conn.fetch(
                """SELECT * FROM jobs WHERE user_id=$1 ORDER BY created_at DESC""",
                user_id,
            )
        else:
            rows = await conn.fetch("SELECT * FROM jobs ORDER BY created_at DESC")

    jobs = [dict(r) for r in rows]

    if not user_id:
        return jobs

    # group by prompt_id, keep one merged dict per prompt with both image_urls
    seen = {}
    ordered = []
    for job in jobs:
        pid = job.get("prompt_id") or job["id"]
        if pid not in seen:
            seen[pid] = job.copy()
            seen[pid]["image_url_wc"] = None
            seen[pid]["image_url_ink"] = None
            ordered.append(pid)
        entry = seen[pid]
        if job["style"] == "watercolor":
            entry["image_url_wc"] = job["image_url"]
        elif job["style"] == "ink_wash":
            entry["image_url_ink"] = job["image_url"]
        # surface the worst status
        if job["status"] == "failed":
            entry["status"] = "failed"
            entry["error_message"] = job.get("error_message")
        elif job["status"] == "pending" and entry["status"] != "failed":
            entry["status"] = "pending"

    return [seen[pid] for pid in ordered]


async def get_recent_images(limit: int = 10) -> list[dict]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT image_url FROM jobs
               WHERE status='done' AND image_url IS NOT NULL AND nsfw_flagged=FALSE
               ORDER BY created_at DESC LIMIT $1""",
            limit,
        )
    return [dict(r) for r in rows]


async def delete_job(job_id: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM jobs WHERE id=$1", job_id)


async def delete_jobs_by_prompt_id(prompt_id: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM jobs WHERE prompt_id=$1", prompt_id)


async def count_recent_jobs(user_id: str, seconds: int = 60) -> int:
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchval(
            """SELECT COUNT(DISTINCT prompt_id) FROM jobs
               WHERE user_id=$1 AND created_at > NOW() - ($2 || ' seconds')::interval""",
            user_id,
            str(seconds),
        )


async def save_onboarding_answer(user_id: str, question: str, answer: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO onboarding_answers (id, user_id, question, answer, created_at)
               VALUES ($1,$2,$3,$4,$5)""",
            str(uuid.uuid4()),
            user_id,
            question,
            answer,
            datetime.now(timezone.utc),
        )
        await conn.execute("UPDATE users SET onboarding_done=TRUE WHERE id=$1", user_id)
