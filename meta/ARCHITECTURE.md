# 🏗️ Architecture & Data Flow

## Request Lifecycle

```
User submits prompt
        │
        ▼
POST /generate
  - Validate word count (≤ 50)
  - Insert job row → SQLite (status: "pending")
  - Kick off background task (FastAPI BackgroundTasks)
  - Redirect → GET /generating/<job_id>
        │
        ▼
GET /generating/<job_id>          ← user lands here
  - Render generating.html
  - jQuery polls GET /api/status/<job_id> every 2 s
        │
        │   [Background task running in parallel]
        │   generate.py → Gemini API
        │   On success:
        │     - Save image bytes → static/images/<uuid>.png
        │     - UPDATE job: status="done", image_path, duration_ms
        │   On failure:
        │     - UPDATE job: status="failed", error_message
        │
        ▼
GET /api/status/<job_id>  →  JSON { status, image_url?, duration_ms?, error? }
  - jQuery checks status:
      "pending"  → keep polling
      "done"     → redirect to /result/<job_id>
      "failed"   → redirect to /result/<job_id>
        │
        ▼
GET /result/<job_id>
  - Render result.html
  - If done:   show image (blurred) + success toast (Xms)
  - If failed: show error toast with reason
        │
        ▼
GET /gallery
  - Query all jobs ORDER BY created_at DESC
  - Render gallery.html with cards
```

---

## PostgreSQL Schema

### Table: `jobs`

| Column         | Type     | Notes                                    |
|---|---|---|
| `id`           | TEXT PK   | UUID v4                                  |
| `prompt`       | TEXT      | Raw user prompt                          |
| `status`       | TEXT      | `pending` / `done` / `failed`            |
| `image_path`   | TEXT      | Relative path, e.g. `static/images/x.png` |
| `image_url`    | TEXT      | `/static/images/x.png` served by FastAPI |
| `duration_ms`  | INTEGER   | Time from job start to Gemini response   |
| `error_message`| TEXT      | Populated on failure                     |
| `nsfw_flagged` | BOOLEAN   | false or true (Gemini safety metadata)   |
| `created_at`   | TIMESTAMPTZ | UTC timestamp with timezone            |

---

## API Endpoints

| Method | Path                    | Description                        |
|---|---|---|
| GET    | `/`                     | Prompt entry page                  |
| POST   | `/generate`             | Submit prompt, create job, redirect|
| GET    | `/generating/<job_id>`  | Status polling UI page             |
| GET    | `/api/status/<job_id>`  | JSON status for polling            |
| GET    | `/result/<job_id>`      | Final result page                  |
| GET    | `/gallery`              | All past generations               |
| GET    | `/static/images/<file>` | Served by FastAPI StaticFiles      |

---

## Background Task Strategy

FastAPI's `BackgroundTasks` is used (not Celery/Redis) to keep the stack simple.

- The task is fired immediately after the job row is inserted.
- PostgreSQL writes from the background task are the single writer; no concurrent write conflicts expected at this scale.
- If the server restarts mid-generation, that job remains `pending` forever → gallery will show it as stuck. Acceptable for v1 (no auth, single user).

---

## Gemini Integration

- Model: `gemini-2.0-flash-preview-image-generation`
- System prompt (injected always, not user-editable):

```
You are a watercolor illustration engine.
Every image you generate must be rendered exclusively as a traditional watercolor painting.
Requirements:
- Soft, translucent watercolor washes with visible paper texture
- Loose, expressive linework as underdrawing
- Painterly, bleeding edges — no sharp digital cuts
- Limited, harmonious palette typical of watercolor work
- Leave some areas of white paper showing through
Apply these rules regardless of the subject matter of the user's prompt.
```

- NSFW: Gemini may block or flag prompts. If it returns a safety error, `status` → `failed`, error surfaced to user. If image is returned but metadata flags it, `nsfw_flagged = 1` → blur applied in UI.

---

## Frontend Polling Detail

```javascript
// generating.html — simplified logic
function poll(jobId) {
  $.getJSON(`/api/status/${jobId}`, function(data) {
    if (data.status === 'pending') {
      setTimeout(() => poll(jobId), 2000);
    } else {
      window.location.href = `/result/${jobId}`;
    }
  });
}
poll(JOB_ID);  // JOB_ID injected by Jinja2
```

---

## NSFW Blur Implementation

```css
/* Applied to all generated images by default */
.generated-image {
  filter: blur(18px);
  transition: filter 0.4s ease;
}
.generated-image.revealed {
  filter: blur(0);
}
```

```javascript
$('#reveal-btn').on('click', function() {
  $('.generated-image').toggleClass('revealed');
  $(this).text($(this).text() === 'Reveal' ? 'Blur' : 'Reveal');
});
```
