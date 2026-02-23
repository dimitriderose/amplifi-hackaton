"""Veo 3.1 video generation agent.

Generates a short video clip from the post's hero image using the Veo API,
uploads the MP4 to GCS, and returns the signed URL.
"""

import asyncio
import logging
import uuid
from google import genai
from google.genai import types

from backend.config import GOOGLE_API_KEY
from backend.services.storage_client import upload_video_to_gcs

logger = logging.getLogger(__name__)

# Veo polling ceiling: 20 minutes
_VEO_POLL_TIMEOUT_S = 20 * 60

# Platforms that use 9:16 (portrait) aspect ratio
_PORTRAIT_PLATFORMS = {"instagram", "tiktok", "reels", "story", "stories"}


def _get_model_and_aspect(platform: str, tier: str) -> tuple[str, str]:
    model = (
        "veo-3.1-fast-generate-preview"
        if tier == "fast"
        else "veo-3.1-generate-preview"
    )
    aspect_ratio = "9:16" if platform.lower() in _PORTRAIT_PLATFORMS else "16:9"
    return model, aspect_ratio


def _build_prompt(caption: str, brand_profile: dict, platform: str) -> str:
    brand_name = brand_profile.get("business_name", "")
    tone = brand_profile.get("tone", "professional and engaging")
    niche = brand_profile.get("industry", "")

    parts = [
        f"Create a dynamic, eye-catching social media video clip for {platform}.",
    ]
    if brand_name:
        parts.append(f"Brand: {brand_name}.")
    if niche:
        parts.append(f"Niche: {niche}.")
    if tone:
        parts.append(f"Tone: {tone}.")
    if caption:
        # Include a condensed version of the caption for context
        short_caption = caption[:200] + "..." if len(caption) > 200 else caption
        parts.append(f"Post context: {short_caption}")
    parts.append(
        "The video should be visually compelling, smooth, and brand-consistent. "
        "No text overlays. Cinematic quality."
    )
    return " ".join(parts)


async def generate_video_clip(
    hero_image_bytes: bytes,
    caption: str,
    brand_profile: dict,
    platform: str,
    post_id: str,
    tier: str = "fast",
) -> dict:
    """Generate a video clip using Veo 3.1, upload to GCS, and return metadata.

    Returns:
        {
            "video_url": str,           # signed GCS URL
            "video_gcs_uri": str,       # gs:// URI
            "duration_seconds": 8,
            "model": str,
            "aspect_ratio": str,
        }
    """
    model_name, aspect_ratio = _get_model_and_aspect(platform, tier)
    prompt = _build_prompt(caption, brand_profile, platform)

    logger.info(
        "Starting Veo video generation: model=%s aspect=%s post_id=%s",
        model_name,
        aspect_ratio,
        post_id,
    )

    client = genai.Client(api_key=GOOGLE_API_KEY)

    # Build the image input for Veo
    hero_image = types.Image(image_bytes=hero_image_bytes, mime_type="image/jpeg")

    # Kick off the long-running video generation operation
    loop = asyncio.get_running_loop()

    operation = await loop.run_in_executor(
        None,
        lambda: client.models.generate_videos(
            model=model_name,
            prompt=prompt,
            image=hero_image,
            config=types.GenerateVideosConfig(
                aspect_ratio=aspect_ratio,
                number_of_videos=1,
            ),
        ),
    )

    logger.info("Veo operation started, polling for completion...")

    # Poll until the operation is complete, with a hard timeout ceiling
    import time as _time
    poll_start = _time.monotonic()
    while not operation.done:
        if _time.monotonic() - poll_start > _VEO_POLL_TIMEOUT_S:
            raise TimeoutError(
                f"Veo video generation timed out after {_VEO_POLL_TIMEOUT_S}s "
                f"for post {post_id}"
            )
        await asyncio.sleep(10)
        operation = await loop.run_in_executor(
            None,
            lambda: client.operations.get(operation),
        )
        logger.info("Veo operation status: done=%s", operation.done)

    logger.info("Veo operation complete, extracting video bytes...")

    # Extract the generated video bytes
    video_bytes = operation.response.generated_videos[0].video.video_bytes

    # Upload MP4 to GCS and get signed URL + GCS URI
    video_url, video_gcs_uri = await upload_video_to_gcs(video_bytes, post_id)

    logger.info("Video uploaded to GCS: %s", video_gcs_uri)

    return {
        "video_url": video_url,
        "video_gcs_uri": video_gcs_uri,
        "duration_seconds": 8,
        "model": model_name,
        "aspect_ratio": aspect_ratio,
    }
