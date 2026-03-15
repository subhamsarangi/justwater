import asyncio
import os
import uuid
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, FastAPI, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from authlib.integrations.starlette_client import OAuth
from starlette.middleware.sessions import SessionMiddleware

from config import (
    IMAGE_DIR,
    SECRET_KEY,
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    TOKEN_LIMIT,
    WATERCOLOR_PROMPT,
    INK_WASH_PROMPT,
)
from database import (
    create_job,
    get_all_jobs,
    get_job,
    get_jobs_by_prompt_id,
    init_db,
    update_job_done,
    update_job_failed,
    get_user_by_email,
    get_user_by_google_id,
    create_user,
    get_user_by_id,
    get_user_stats,
    update_user_tokens,
    get_recent_images,
    delete_job,
    delete_jobs_by_prompt_id,
    count_recent_jobs,
)
from generate import _call_gemini, save_image, delete_image
from auth import (
    hash_password,
    verify_password,
    set_session,
    clear_session,
    get_current_user,
    SESSION_COOKIE,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if IMAGE_DIR:
        os.makedirs(IMAGE_DIR, exist_ok=True)
    await init_db()
    yield


app = FastAPI(lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

oauth = OAuth()
oauth.register(
    name="google",
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)


async def current_user(request: Request):
    return await get_current_user(request, get_user_by_id)


# ── Background tasks ───────────────────────────────────────────────────────


async def _run_single(job_id: str, style_prompt: str, prompt: str, user_id: str):
    from concurrent.futures import ThreadPoolExecutor

    loop = asyncio.get_event_loop()
    executor = ThreadPoolExecutor(max_workers=1)
    try:
        image_bytes, nsfw_flagged, duration_ms, tokens_used = (
            await loop.run_in_executor(executor, _call_gemini, style_prompt, prompt)
        )
        image_path, image_url, file_size_bytes = save_image(image_bytes)
        await update_job_done(
            job_id,
            image_path,
            image_url,
            duration_ms,
            nsfw_flagged,
            tokens_used,
            file_size_bytes,
        )
        if user_id and tokens_used:
            await update_user_tokens(user_id, tokens_used)
    except Exception as e:
        await update_job_failed(job_id, str(e))
    finally:
        executor.shutdown(wait=False)


async def run_generation(prompt: str, job_wc: str, job_ink: str, user_id: str = None):
    await asyncio.gather(
        _run_single(job_wc, WATERCOLOR_PROMPT, prompt, user_id),
        _run_single(job_ink, INK_WASH_PROMPT, prompt, user_id),
    )


# ── Auth routes ────────────────────────────────────────────────────────────


@app.get("/auth")
async def auth_page(request: Request):
    user = await current_user(request)
    if user:
        return RedirectResponse(url="/")
    return templates.TemplateResponse("auth.html", {"request": request, "error": None})


@app.post("/auth/signup")
async def signup(
    request: Request,
    email: str = Form(...),
    name: str = Form(...),
    password: str = Form(...),
):
    existing = await get_user_by_email(email)
    if existing:
        return templates.TemplateResponse(
            "auth.html",
            {"request": request, "error": "Email already registered.", "tab": "signup"},
        )
    user = await create_user(
        email=email, name=name, password_hash=hash_password(password)
    )
    response = RedirectResponse(url="/", status_code=303)
    set_session(response, user["id"])
    return response


@app.post("/auth/signin")
async def signin(request: Request, email: str = Form(...), password: str = Form(...)):
    user = await get_user_by_email(email)
    if (
        not user
        or not user.get("password_hash")
        or not verify_password(password, user["password_hash"])
    ):
        return templates.TemplateResponse(
            "auth.html",
            {
                "request": request,
                "error": "Invalid email or password.",
                "tab": "signin",
            },
        )
    response = RedirectResponse(url="/", status_code=303)
    set_session(response, user["id"])
    return response


@app.get("/auth/logout")
async def logout():
    response = RedirectResponse(url="/auth", status_code=303)
    clear_session(response)
    return response


@app.get("/auth/google")
async def google_login(request: Request):
    redirect_uri = str(request.url_for("google_callback"))
    return await oauth.google.authorize_redirect(request, redirect_uri)


@app.get("/auth/google/callback")
async def google_callback(request: Request):
    token = await oauth.google.authorize_access_token(request)
    info = token.get("userinfo") or await oauth.google.userinfo(token=token)
    google_id, email = info["sub"], info["email"]
    name, avatar = info.get("name", email), info.get("picture")

    user = await get_user_by_google_id(google_id)
    if not user:
        user = await get_user_by_email(email)
        if user:
            from database import get_pool

            pool = await get_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    "UPDATE users SET google_id=$1, avatar_url=$2 WHERE id=$3",
                    google_id,
                    avatar,
                    user["id"],
                )
        else:
            user = await create_user(
                email=email, name=name, google_id=google_id, avatar_url=avatar
            )

    response = RedirectResponse(url="/", status_code=303)
    set_session(response, user["id"])
    return response


# ── Profile ────────────────────────────────────────────────────────────────


@app.get("/profile")
async def profile(request: Request):
    user = await current_user(request)
    if not user:
        return RedirectResponse(url="/auth", status_code=303)
    stats = await get_user_stats(user["id"])
    return templates.TemplateResponse(
        "profile.html",
        {"request": request, "user": user, "stats": stats, "token_limit": TOKEN_LIMIT},
    )


# ── App routes ─────────────────────────────────────────────────────────────


@app.get("/")
async def index(request: Request):
    user = await current_user(request)
    if not user:
        return RedirectResponse(url="/auth", status_code=303)
    recent_images = await get_recent_images(10)
    return templates.TemplateResponse(
        "index.html", {"request": request, "user": user, "recent_images": recent_images}
    )


@app.post("/generate")
async def generate(
    request: Request, background_tasks: BackgroundTasks, prompt: str = Form(...)
):
    user = await current_user(request)
    if not user:
        return RedirectResponse(url="/auth", status_code=303)

    words = prompt.strip().split()
    if len(words) > 50:
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "user": user,
                "error": "Prompt must be 50 words or fewer.",
                "prompt": prompt,
            },
            status_code=422,
        )

    recent = await count_recent_jobs(user["id"], seconds=60)
    if recent >= 4:
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "user": user,
                "error": "You can only generate 4 images per minute. Please wait a moment.",
                "prompt": prompt,
            },
            status_code=429,
        )

    prompt_id = str(uuid.uuid4())
    job_wc = await create_job(
        prompt, user["id"], prompt_id=prompt_id, style="watercolor"
    )
    job_ink = await create_job(
        prompt, user["id"], prompt_id=prompt_id, style="ink_wash"
    )
    background_tasks.add_task(run_generation, prompt, job_wc, job_ink, user["id"])
    return RedirectResponse(url=f"/generating/{prompt_id}", status_code=303)


@app.get("/generating/{prompt_id}")
async def generating(request: Request, prompt_id: str):
    user = await current_user(request)
    if not user:
        return RedirectResponse(url="/auth", status_code=303)
    jobs = await get_jobs_by_prompt_id(prompt_id)
    if not jobs:
        return RedirectResponse(url="/gallery")
    return templates.TemplateResponse(
        "generating.html",
        {"request": request, "job": jobs[0], "prompt_id": prompt_id, "user": user},
    )


@app.get("/api/status/{prompt_id}")
async def api_status(prompt_id: str):
    jobs = await get_jobs_by_prompt_id(prompt_id)
    if not jobs:
        return JSONResponse({"error": "Not found"}, status_code=404)
    statuses = [j["status"] for j in jobs]
    if all(s == "done" for s in statuses):
        return JSONResponse({"status": "done"})
    if any(s == "failed" for s in statuses):
        return JSONResponse({"status": "failed"})
    return JSONResponse({"status": "pending"})


@app.get("/result/{prompt_id}")
async def result(request: Request, prompt_id: str):
    user = await current_user(request)
    if not user:
        return RedirectResponse(url="/auth", status_code=303)
    jobs = await get_jobs_by_prompt_id(prompt_id)
    if not jobs:
        return RedirectResponse(url="/gallery")
    job_wc = next((j for j in jobs if j["style"] == "watercolor"), jobs[0])
    job_ink = next((j for j in jobs if j["style"] == "ink_wash"), jobs[-1])
    return templates.TemplateResponse(
        "result.html",
        {
            "request": request,
            "job_wc": job_wc,
            "job_ink": job_ink,
            "prompt_id": prompt_id,
            "user": user,
        },
    )


@app.get("/gallery")
async def gallery_redirect(request: Request):
    user = await current_user(request)
    if not user:
        return RedirectResponse(url="/auth", status_code=303)
    return RedirectResponse(url=f"/gallery/{user['id']}", status_code=302)


@app.get("/gallery/{user_id}")
async def gallery(request: Request, user_id: str):
    viewer = await current_user(request)
    owner = await get_user_by_id(user_id)
    if not owner:
        return RedirectResponse(url="/")
    jobs = await get_all_jobs(user_id)
    return templates.TemplateResponse(
        "gallery.html",
        {"request": request, "jobs": jobs, "user": viewer, "owner": owner},
    )


@app.get("/privacy")
async def privacy(request: Request):
    user = await current_user(request)
    return templates.TemplateResponse(
        "privacy.html", {"request": request, "user": user}
    )


@app.post("/delete/{job_id}")
async def delete(request: Request, job_id: str):
    user = await current_user(request)
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    job = await get_job(job_id)
    if not job:
        return JSONResponse({"error": "Not found"}, status_code=404)
    if job["user_id"] != user["id"]:
        return JSONResponse({"error": "Forbidden"}, status_code=403)
    # delete both jobs in the pair
    prompt_id = job.get("prompt_id")
    if prompt_id:
        pair = await get_jobs_by_prompt_id(prompt_id)
        for j in pair:
            if j.get("image_path"):
                delete_image(j["image_path"])
        await delete_jobs_by_prompt_id(prompt_id)
    else:
        if job.get("image_path"):
            delete_image(job["image_path"])
        await delete_job(job_id)
    return RedirectResponse(url=f"/gallery/{user['id']}", status_code=303)
