# 🤖 Gemini API — Integration Notes

## Model

```
gemini-2.0-flash-preview-image-generation
```

This model supports **interleaved text + image output**. We request it in image-only mode by setting `response_modalities=["IMAGE"]` (or `["IMAGE", "TEXT"]` if we want a caption too — skip for now).

---

## Python SDK

```bash
pip install google-generativeai
```

### Basic Call Pattern

```python
import google.generativeai as genai
from google.generativeai import types

genai.configure(api_key=GEMINI_API_KEY)

model = genai.GenerativeModel(
    model_name="gemini-2.0-flash-preview-image-generation",
)

response = model.generate_content(
    contents=FULL_PROMPT,          # system_style_prompt + user_prompt combined
    generation_config=types.GenerationConfig(
        response_modalities=["IMAGE"],
    ),
)
```

### Extracting Image Bytes

```python
for part in response.candidates[0].content.parts:
    if part.inline_data is not None:
        image_bytes = part.inline_data.data          # bytes
        mime_type   = part.inline_data.mime_type     # e.g. "image/png"
        break
```

---

## System Prompt Strategy

Gemini image generation doesn't support a separate `system_instruction` for image output. Instead, prepend the style directive directly into the `contents` string:

```python
WATERCOLOR_SYSTEM_PROMPT = """
Generate this as a traditional watercolor painting with the following qualities:
- Soft, translucent watercolor washes with visible paper grain showing through
- Loose ink or pencil linework as underdrawing visible beneath the color
- Bleeding, painterly edges — avoid sharp digital edges or gradients
- A limited, harmonious watercolor palette (avoid oversaturation)
- Natural white paper areas left unpainted for highlights

Subject to paint:
"""

full_prompt = WATERCOLOR_SYSTEM_PROMPT + user_prompt
```

---

## Safety / NSFW Handling

### When Gemini Blocks the Request

`response.candidates` may be empty, or `response.candidates[0].finish_reason` may be `SAFETY`.

```python
from google.generativeai.types import HarmBlockThreshold, HarmCategory

# Optionally lower safety thresholds for NSFW allowance:
safety_settings = {
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH:       HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_HARASSMENT:        HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
}
```

Pass `safety_settings=safety_settings` to `generate_content()`.

> ⚠️ **Note:** `BLOCK_NONE` for sexually explicit content may still result in blocks depending on Gemini's current policy. Test this during development and handle gracefully.

### Detecting NSFW Flag

Check `response.candidates[0].safety_ratings` for any rating with `probability` of `HIGH` or `MEDIUM` on `HARM_CATEGORY_SEXUALLY_EXPLICIT`. Set `nsfw_flagged = 1` in DB if so.

---

## Error Handling Matrix

| Gemini Response Condition           | Action                                         |
|---|---|
| `finish_reason == SAFETY`           | `status=failed`, error = "Content blocked by safety filter" |
| Empty `candidates` list             | `status=failed`, error = "No image returned"   |
| No `inline_data` in parts           | `status=failed`, error = "Unexpected response format" |
| Network / API timeout               | `status=failed`, error = "API request timed out" |
| `google.api_core.exceptions.*`      | `status=failed`, error = exception message      |

---

## Saving the Image

```python
import uuid, os
from PIL import Image
import io

filename  = f"{uuid.uuid4()}.png"
filepath  = os.path.join(IMAGE_DIR, filename)

image = Image.open(io.BytesIO(image_bytes))
image.save(filepath, format="PNG")

image_url = f"/static/images/{filename}"
```

---

## Timing

Wrap the API call with `time.time()`:

```python
import time

start = time.time()
response = model.generate_content(...)
duration_ms = int((time.time() - start) * 1000)
```

Store `duration_ms` in the `jobs` table.

---

## Known Limitations

- Gemini image generation can take 5–20 seconds; the polling approach handles this fine.
- The model generates 1 image per call. No batch for v1.
- Images are returned inline (base64 bytes), not as URLs — save to local disk immediately.
- Free-tier API quotas may apply; watch for `ResourceExhausted` errors.
