import os
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, FastAPI, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse
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
)
from database import (
    create_job,
    get_all_jobs,
    get_job,
    init_db,
    update_job_done,
    update_job_failed,
    get_user_by_email,
    get_user_by_google_id,
    create_user,
    get_user_by_id,
    get_user_stats,
    update_user_tokens,
)
from generate import generate_watercolor, save_image
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


def require_auth(request: Request):
    token = request.cookies.get(SESSION_COOKIE)
    return token is not None


# ── Background task ────────────────────────────────────────────────────────


async def run_generation(job_id: str, prompt: str, user_id: str = None):
    try:
        image_bytes, nsfw_flagged, duration_ms, tokens_used = generate_watercolor(
            prompt
        )
        image_path, image_url = save_image(image_bytes)
        await update_job_done(
            job_id, image_path, image_url, duration_ms, nsfw_flagged, tokens_used
        )
        if user_id and tokens_used:
            await update_user_tokens(user_id, tokens_used)
    except Exception as e:
        await update_job_failed(job_id, str(e))


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
    google_id = info["sub"]
    email = info["email"]
    name = info.get("name", email)
    avatar = info.get("picture")

    user = await get_user_by_google_id(google_id)
    if not user:
        user = await get_user_by_email(email)
        if user:
            # link google to existing account
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
        {
            "request": request,
            "user": user,
            "stats": stats,
            "token_limit": TOKEN_LIMIT,
        },
    )


# ── App routes ─────────────────────────────────────────────────────────────


@app.get("/")
async def index(request: Request):
    user = await current_user(request)
    if not user:
        return RedirectResponse(url="/auth", status_code=303)
    return templates.TemplateResponse("index.html", {"request": request, "user": user})


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
    job_id = await create_job(prompt, user["id"])
    background_tasks.add_task(run_generation, job_id, prompt, user["id"])
    return RedirectResponse(url=f"/generating/{job_id}", status_code=303)


@app.get("/generating/{job_id}")
async def generating(request: Request, job_id: str):
    user = await current_user(request)
    if not user:
        return RedirectResponse(url="/auth", status_code=303)
    job = await get_job(job_id)
    if not job:
        return RedirectResponse(url="/gallery")
    return templates.TemplateResponse(
        "generating.html", {"request": request, "job": job, "user": user}
    )


@app.get("/api/status/{job_id}")
async def api_status(job_id: str):
    job = await get_job(job_id)
    if not job:
        return JSONResponse({"error": "Job not found"}, status_code=404)
    data: dict = {"status": job["status"]}
    if job["status"] == "done":
        data["image_url"] = job["image_url"]
        data["duration_ms"] = job["duration_ms"]
    elif job["status"] == "failed":
        data["error"] = job["error_message"]
    return JSONResponse(data)


@app.get("/result/{job_id}")
async def result(request: Request, job_id: str):
    user = await current_user(request)
    if not user:
        return RedirectResponse(url="/auth", status_code=303)
    job = await get_job(job_id)
    if not job:
        return RedirectResponse(url="/gallery")
    return templates.TemplateResponse(
        "result.html", {"request": request, "job": job, "user": user}
    )


@app.get("/gallery")
async def gallery(request: Request):
    user = await current_user(request)
    if not user:
        return RedirectResponse(url="/auth", status_code=303)
    jobs = await get_all_jobs(user["id"])
    return templates.TemplateResponse(
        "gallery.html", {"request": request, "jobs": jobs, "user": user}
    )
