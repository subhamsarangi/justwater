# ✅ Implementation Checklist

Work through these in order. Each section should be fully working before moving to the next.

---

## Phase 1 — Backend Foundation

- [ ] `config.py` — load `.env`, define `IMAGE_DIR`, `DATABASE_URL`, `GEMINI_API_KEY`, system prompt constant
- [ ] `database.py`
  - [ ] `init_db()` — create `jobs` table if not exists (uses `asyncpg` connection pool)
  - [ ] `create_job(prompt)` → returns `job_id`
  - [ ] `update_job_done(job_id, image_path, image_url, duration_ms, nsfw_flagged)`
  - [ ] `update_job_failed(job_id, error_message)`
  - [ ] `get_job(job_id)` → returns job dict
  - [ ] `get_all_jobs()` → returns list ordered by `created_at DESC`
- [ ] `generate.py`
  - [ ] `generate_watercolor(prompt)` → calls Gemini, returns `(image_bytes, nsfw_flagged, duration_ms)` or raises exception with message
  - [ ] Prepend system/style prompt to user prompt before API call
  - [ ] Handle Gemini safety blocks gracefully (catch and re-raise with readable message)
- [ ] `main.py`
  - [ ] Init FastAPI app, mount `StaticFiles` at `/static`
  - [ ] Mount `Jinja2Templates`
  - [ ] Call `init_db()` on startup
  - [ ] `GET /` → render `index.html`
  - [ ] `POST /generate` → validate word count, create job, fire background task, redirect to `/generating/<job_id>`
  - [ ] `GET /generating/<job_id>` → render `generating.html` with job_id + prompt
  - [ ] `GET /api/status/<job_id>` → return JSON status
  - [ ] `GET /result/<job_id>` → render `result.html` with job data
  - [ ] `GET /gallery` → render `gallery.html` with all jobs
  - [ ] Background task `run_generation(job_id, prompt)` → calls `generate.py`, updates DB
- [ ] `requirements.txt` — fastapi, uvicorn, jinja2, python-dotenv, google-generativeai, aiofiles, pillow, asyncpg

---

## Phase 2 — Templates

- [ ] `base.html` — Bootstrap 5 CDN, Google Fonts, jQuery CDN, navbar, `app.js` link, content block, footer
- [ ] `index.html` — textarea, word counter, submit button
- [ ] `generating.html` — loader animation, elapsed timer, polling JS
- [ ] `result.html` — image with blur, reveal/download/new buttons, toast trigger
- [ ] `gallery.html` — responsive grid of job cards

---

## Phase 3 — Static Assets

- [ ] `static/css/style.css` — CSS variables, paper texture, typography, component overrides
- [ ] `static/js/app.js` — toast helper, word counter utility, any shared functions
- [ ] `static/images/paper-texture.jpg` — subtle grain image (can use a CC0 asset or generate via CSS)

---

## Phase 4 — Polish & Edge Cases

- [ ] Word count validation fires client-side AND server-side (POST /generate checks too)
- [ ] If `job_id` not found → 404 page or redirect to gallery
- [ ] Stuck `pending` jobs in gallery shown with a spinner badge (not broken state)
- [ ] Image download button uses `<a download>` pointing to static URL
- [ ] `static/images/` directory auto-created if missing on startup
- [ ] Toast on result page fires on DOM ready (not on image load)
- [ ] Gallery thumbnails also blurred by default; reveal per-card
- [ ] Mobile responsive check on all pages

---

## Phase 5 — Testing

- [ ] Test successful generation end-to-end
- [ ] Test with a prompt > 50 words (should be blocked)
- [ ] Test with an NSFW prompt (blur should appear, reveal toggle works)
- [ ] Test a prompt that triggers Gemini safety block (failure path)
- [ ] Test gallery shows correct status badges
- [ ] Test direct URL access to `/result/<bad_id>` (graceful 404)
- [ ] Test server restart with a `pending` job in DB (gallery shows it as pending)
