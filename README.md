<p align="center">
  <img src="https://cdn.openworldregister.com/justwater/logo.png" alt="Just Water" height="60" />
</p>

<p align="center">
  Describe a scene. We'll paint it.
</p>

<p align="center">
  <a href="https://art.openworldregister.com">art.openworldregister.com</a>
</p>

---

<p align="center">
  <img src="static/images/92bfb2a0-b4ee-4cdd-9962-321cd836c1d0.png" alt="Example generation" width="480" style="border-radius:12px;" />
</p>

---

## What it does

Just Water turns a text prompt into two AI-painted images — one in traditional watercolor, one in East Asian ink wash (sumi-e) — using Google Gemini's image generation model.

## Features

- Two styles generated in parallel per prompt
- Personal gallery with public shareable URL
- Google OAuth + email/password auth
- PWA — installable on mobile
- Images stored on Cloudflare R2 in production

## Stack

- **Backend** — FastAPI + asyncpg (PostgreSQL)
- **AI** — Google Gemini (`gemini-2.5-flash-image`)
- **Storage** — Cloudflare R2 (prod) / local filesystem (dev)
- **Frontend** — Bootstrap 5 + jQuery

## Run locally

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

Needs a `.env` with `GEMINI_API_KEY`, `DATABASE_URL`, and `SECRET_KEY` at minimum.

---

Made by [Subham Sarangi](https://github.com/subhamsarangi)
