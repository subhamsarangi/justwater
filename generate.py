import io
import os
import time
import uuid

import google.generativeai as genai
from google.generativeai import types
from google.generativeai.types import HarmBlockThreshold, HarmCategory
from PIL import Image

from config import GEMINI_API_KEY, IMAGE_DIR, WATERCOLOR_PROMPT

genai.configure(api_key=GEMINI_API_KEY)

_model = genai.GenerativeModel(model_name="gemini-2.0-flash-preview-image-generation")

_safety = {
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
}


def generate_watercolor(prompt: str) -> tuple[bytes, bool, int]:
    full_prompt = WATERCOLOR_PROMPT + prompt

    start = time.time()
    try:
        response = _model.generate_content(
            contents=full_prompt,
            generation_config=types.GenerationConfig(response_modalities=["IMAGE"]),
            safety_settings=_safety,
        )
    except Exception as e:
        raise RuntimeError(str(e))
    duration_ms = int((time.time() - start) * 1000)

    if not response.candidates:
        raise RuntimeError("No image returned")

    candidate = response.candidates[0]

    if str(candidate.finish_reason) == "SAFETY":
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
        for r in candidate.safety_ratings
    )

    return image_bytes, nsfw_flagged, duration_ms


def save_image(image_bytes: bytes) -> tuple[str, str]:
    os.makedirs(IMAGE_DIR, exist_ok=True)
    filename = f"{uuid.uuid4()}.png"
    filepath = os.path.join(IMAGE_DIR, filename)
    Image.open(io.BytesIO(image_bytes)).save(filepath, format="PNG")
    return filepath, f"/static/images/{filename}"
