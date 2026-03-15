import os
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, FastAPI, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from config import IMAGE_DIR
from database import (
    create_job,
    get_all_jobs,
    get_job,
    init_db,
    update_job_done,
    update_job_failed,
)
from generate import generate_watercolor, save_image


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(IMAGE_DIR, exist_ok=True)
    await init_db()
    yield


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


async def run_generation(job_id: str, prompt: str):
    try:
        image_bytes, nsfw_flagged, duration_ms = generate_watercolor(prompt)
        image_path, image_url = save_image(image_bytes)
        await update_job_done(job_id, image_path, image_url, duration_ms, nsfw_flagged)
    except Exception as e:
        await update_job_failed(job_id, str(e))


@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/generate")
async def generate(
    request: Request, background_tasks: BackgroundTasks, prompt: str = Form(...)
):
    words = prompt.strip().split()
    if len(words) > 50:
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "error": "Prompt must be 50 words or fewer.",
                "prompt": prompt,
            },
            status_code=422,
        )
    job_id = await create_job(prompt)
    background_tasks.add_task(run_generation, job_id, prompt)
    return RedirectResponse(url=f"/generating/{job_id}", status_code=303)


@app.get("/generating/{job_id}")
async def generating(request: Request, job_id: str):
    job = await get_job(job_id)
    if not job:
        return RedirectResponse(url="/gallery")
    return templates.TemplateResponse(
        "generating.html", {"request": request, "job": job}
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
    job = await get_job(job_id)
    if not job:
        return RedirectResponse(url="/gallery")
    return templates.TemplateResponse("result.html", {"request": request, "job": job})


@app.get("/gallery")
async def gallery(request: Request):
    jobs = await get_all_jobs()
    return templates.TemplateResponse(
        "gallery.html", {"request": request, "jobs": jobs}
    )
