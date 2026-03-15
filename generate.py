import io
import os
import time
import uuid

from google import genai
from google.genai import types
from PIL import Image

from config import GEMINI_API_KEY, IMAGE_DIR, WATERCOLOR_PROMPT

_client = genai.Client(api_key=GEMINI_API_KEY)
_MODEL = "gemini-2.5-flash-image"


def generate_watercolor(prompt: str) -> tuple[bytes, bool, int]:
    full_prompt = WATERCOLOR_PROMPT + prompt

    start = time.time()
    try:
        response = _client.models.generate_content(
            model=_MODEL,
            contents=full_prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                safety_settings=[
                    types.SafetySetting(
                        category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
                        threshold="BLOCK_NONE",
                    ),
                    types.SafetySetting(
                        category="HARM_CATEGORY_HATE_SPEECH",
                        threshold="BLOCK_MEDIUM_AND_ABOVE",
                    ),
                    types.SafetySetting(
                        category="HARM_CATEGORY_HARASSMENT",
                        threshold="BLOCK_MEDIUM_AND_ABOVE",
                    ),
                    types.SafetySetting(
                        category="HARM_CATEGORY_DANGEROUS_CONTENT",
                        threshold="BLOCK_MEDIUM_AND_ABOVE",
                    ),
                ],
            ),
        )
    except Exception as e:
        raise RuntimeError(str(e))
    duration_ms = int((time.time() - start) * 1000)

    if not response.candidates:
        raise RuntimeError("No image returned")

    candidate = response.candidates[0]

    if candidate.finish_reason and str(candidate.finish_reason) == "SAFETY":
        raise RuntimeError("Content blocked by safety filter")

    image_bytes = None
    for part in candidate.content.parts:
        if part.inline_data is not None:
            image_bytes = part.inline_data.data
            break

    if image_bytes is None:
        raise RuntimeError("Unexpected response format")

    nsfw_flagged = any(
        str(r.category) == "HARM_CATEGORY_SEXUALLY_EXPLICIT"
        and str(r.probability) in ("MEDIUM", "HIGH")
        for r in (candidate.safety_ratings or [])
    )

    return image_bytes, nsfw_flagged, duration_ms


def save_image(image_bytes: bytes) -> tuple[str, str]:
    os.makedirs(IMAGE_DIR, exist_ok=True)
    filename = f"{uuid.uuid4()}.png"
    filepath = os.path.join(IMAGE_DIR, filename)
    Image.open(io.BytesIO(image_bytes)).save(filepath, format="PNG")
    return filepath, f"/static/images/{filename}"
