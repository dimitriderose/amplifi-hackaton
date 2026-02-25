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
from backend.services.brand_assets import get_brand_reference_images

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


def _build_prompt(caption: str, brand_profile: dict, platform: str,
                   has_brand_refs: bool = False) -> str:
    brand_name = brand_profile.get("business_name", "")
    tone = brand_profile.get("tone", "professional and engaging")
    niche = brand_profile.get("industry", "")
    colors = brand_profile.get("colors", [])
    visual_style = brand_profile.get("visual_style", "")
    image_style_directive = brand_profile.get("image_style_directive", "")

    parts = [
        f"Create a dynamic, eye-catching social media video clip for {platform}.",
    ]
    if brand_name:
        parts.append(f"Brand: {brand_name}.")
    if niche:
        parts.append(f"Industry: {niche}.")
    if tone:
        parts.append(f"Tone: {tone}.")
    if colors:
        parts.append(f"Brand colors: {', '.join(colors[:4])}.")
    if visual_style:
        parts.append(f"Visual style: {visual_style}.")
    if image_style_directive:
        short_directive = image_style_directive[:200]
        parts.append(f"Style guide: {short_directive}.")
    if caption:
        short_caption = caption[:200] + "..." if len(caption) > 200 else caption
        parts.append(f"Post context: {short_caption}")

    if has_brand_refs:
        parts.append(
            "The video should be visually compelling, smooth, and brand-consistent. "
            "Use the provided brand reference assets (logo, product images) faithfully — "
            f"the brand name is exactly \"{brand_name}\". "
            "Do NOT add any other text, watermarks, or made-up logos beyond what is in "
            "the reference assets. Cinematic quality with smooth motion."
        )
    else:
        parts.append(
            "The video should be visually compelling, smooth, and brand-consistent. "
            "CRITICAL: Do NOT include any text, words, brand names, logos, watermarks, "
            "or written content in the video. Pure visual content only — no typography. "
            "Cinematic quality with smooth motion."
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

    client = genai.Client(api_key=GOOGLE_API_KEY)

    # Build the image input for Veo
    hero_image = types.Image(image_bytes=hero_image_bytes, mime_type="image/jpeg")

    # Fetch brand reference images (logo, product photos, style ref) for Veo
    reference_images = []
    try:
        brand_refs = await get_brand_reference_images(brand_profile, max_images=3)
        for ref_bytes, ref_mime in brand_refs:
            reference_images.append(
                types.VideoGenerationReferenceImage(
                    image=types.Image(image_bytes=ref_bytes, mime_type=ref_mime),
                    reference_type="asset",
                )
            )
        if reference_images:
            logger.info("Passing %d brand reference images to Veo", len(reference_images))
    except Exception as e:
        logger.warning("Failed to load brand reference images: %s", e)

    # Build prompt — adapts instructions based on whether we have brand refs
    prompt = _build_prompt(caption, brand_profile, platform,
                           has_brand_refs=bool(reference_images))

    logger.info(
        "Starting Veo video generation: model=%s aspect=%s post_id=%s",
        model_name,
        aspect_ratio,
        post_id,
    )

    # Kick off the long-running video generation operation
    loop = asyncio.get_running_loop()

    config = types.GenerateVideosConfig(
        aspect_ratio=aspect_ratio,
        number_of_videos=1,
    )
    if reference_images:
        config.reference_images = reference_images

    operation = await loop.run_in_executor(
        None,
        lambda: client.models.generate_videos(
            model=model_name,
            prompt=prompt,
            image=hero_image,
            config=config,
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

    logger.info("Veo operation complete, downloading video via files API...")

    # Use client.files.download() — Veo doesn't populate video_bytes directly
    gen_video = operation.response.generated_videos[0]
    video_bytes = await loop.run_in_executor(
        None,
        lambda: client.files.download(file=gen_video),
    )

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
