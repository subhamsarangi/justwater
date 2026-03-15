import io
import os
import time
import uuid
import asyncio
from concurrent.futures import ThreadPoolExecutor

import boto3
from google import genai
from google.genai import types
from PIL import Image

from config import (
    GEMINI_API_KEY,
    IMAGE_DIR,
    WATERCOLOR_PROMPT,
    INK_WASH_PROMPT,
    IS_LOCAL,
    R2_ACCOUNT_ID,
    R2_ACCESS_KEY_ID,
    R2_SECRET_ACCESS_KEY,
    R2_BUCKET_NAME,
    R2_PUBLIC_URL,
)

_client = genai.Client(api_key=GEMINI_API_KEY)
_MODEL = "gemini-2.5-flash-image"

_r2 = None
if not IS_LOCAL:
    _r2 = boto3.client(
        "s3",
        endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        region_name="auto",
    )


_executor = ThreadPoolExecutor(max_workers=2)


def _call_gemini(style_prompt: str, user_prompt: str) -> tuple[bytes, bool, int, int]:
    full_prompt = style_prompt + user_prompt
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
    tokens_used = 0
    if response.usage_metadata:
        tokens_used = (response.usage_metadata.prompt_token_count or 0) + (
            response.usage_metadata.candidates_token_count or 0
        )

    return image_bytes, nsfw_flagged, duration_ms, tokens_used


async def generate_both(prompt: str):
    loop = asyncio.get_event_loop()
    result1, result2 = await asyncio.gather(
        loop.run_in_executor(_executor, _call_gemini, WATERCOLOR_PROMPT, prompt),
        loop.run_in_executor(_executor, _call_gemini, INK_WASH_PROMPT, prompt),
    )
    return result1, result2


def save_image(image_bytes: bytes) -> tuple[str, str, int]:
    filename = f"{uuid.uuid4()}.png"
    size = len(image_bytes)
    if IS_LOCAL:
        os.makedirs(IMAGE_DIR, exist_ok=True)
        filepath = os.path.join(IMAGE_DIR, filename)
        Image.open(io.BytesIO(image_bytes)).save(filepath, format="PNG")
        return filepath, f"/static/images/{filename}", size
    else:
        key = f"justwater/images/{filename}"
        _r2.put_object(
            Bucket=R2_BUCKET_NAME,
            Key=key,
            Body=image_bytes,
            ContentType="image/png",
        )
        return key, f"{R2_PUBLIC_URL}/{key}", size


def delete_image(image_path: str):
    if IS_LOCAL:
        try:
            os.remove(image_path)
        except FileNotFoundError:
            pass
    else:
        try:
            _r2.delete_object(Bucket=R2_BUCKET_NAME, Key=image_path)
        except Exception:
            pass
