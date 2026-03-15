# 🎨 Watercolor AI — Project Overview

A minimal web app where users generate AI watercolor art from text prompts using the Google Gemini image generation API.

---

## Tech Stack

| Layer        | Choice                                                      |
|---|---|
| Backend      | FastAPI (Python)                                            |
| Database     | PostgreSQL (via `asyncpg`)                                  |
| Image Storage| Local filesystem (`static/images/`)                        |
| Frontend     | jQuery 3 + Bootstrap 5                                      |
| AI           | Google Gemini (`gemini-2.0-flash-preview-image-generation`) |
| Fonts        | Google Fonts — display + body pairing                       |
| UI Theme     | Minimal light, paper-textured, warm palette                 |

---

## Key Features

1. **Prompt page** — Textarea capped at 50 words, live word counter, submit button.
2. **Generating page** — Dedicated `/generating/<job_id>` route; polls backend every 2 s for job status.
3. **Result display** — On success: image + toast showing generation time. On failure: toast with error reason.
4. **NSFW blur** — All images rendered with CSS blur initially; a "Reveal" toggle removes it.
5. **Gallery page** — `/gallery` lists all past jobs (thumbnail, prompt snippet, timestamp, status badge).
6. **No auth** — Fully open, single-user assumed.

---

## Project File Structure

```
watercolor-ai/
├── main.py                  # FastAPI app & all route handlers
├── database.py              # PostgreSQL schema + CRUD helpers (asyncpg)
├── generate.py              # Gemini API wrapper (prompt → image bytes)
├── config.py                # App settings loaded from .env
├── requirements.txt         # Python dependencies
├── .env.example             # Sample env file
│
├── static/
│   ├── images/              # Persisted generated images (UUID-named .png)
│   ├── css/
│   │   └── style.css        # Custom theme, texture, typography
│   └── js/
│       └── app.js           # Shared jQuery helpers, toast, polling
│
└── templates/
    ├── base.html            # Layout shell (navbar, CDN links, footer)
    ├── index.html           # Prompt entry form
    ├── generating.html      # Status polling page
    ├── result.html          # Final result (image or error)
    └── gallery.html         # All past generations
```

---

## Environment Setup

```bash
# .env
GEMINI_API_KEY=your_key_here
IMAGE_DIR=static/images
DATABASE_URL=postgresql://user:password@localhost:5432/watercolor_ai
```

---

## Run Locally

```bash
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Open → `http://localhost:8000`
