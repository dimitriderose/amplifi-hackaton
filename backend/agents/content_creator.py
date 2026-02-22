import asyncio
import base64
import json
import logging
from typing import AsyncIterator

from google import genai
from google.genai import types

from backend.config import GOOGLE_API_KEY
from backend.services import budget_tracker as bt
from backend.services.storage_client import upload_image_to_gcs

logger = logging.getLogger(__name__)
client = genai.Client(api_key=GOOGLE_API_KEY)


async def generate_post(
    plan_id: str,
    day_brief: dict,
    brand_profile: dict,
    post_id: str,
) -> AsyncIterator[dict]:
    """
    Generate a social media post using Gemini 2.5 Flash interleaved TEXT+IMAGE.
    Yields SSE-compatible event dicts: {"event": str, "data": dict}

    Events emitted (in order):
      {"event": "status",  "data": {"message": "..."}}
      {"event": "caption", "data": {"text": "...", "chunk": True}}   # streamed chunks
      {"event": "caption", "data": {"text": "...", "chunk": False, "hashtags": [...]}}  # final
      {"event": "image",   "data": {"url": "...", "mime_type": "image/png"}}
      {"event": "complete","data": {"post_id": "...", "caption": "...", "hashtags": [...], "image_url": "..."}}
      {"event": "error",   "data": {"message": "..."}}  # on failure
    """

    # Check budget
    if not bt.budget_tracker.can_generate_image():
        yield {"event": "error", "data": {"message": "Image budget exhausted"}}
        return

    platform = day_brief.get("platform", "instagram")
    pillar = day_brief.get("pillar", "education")
    content_theme = day_brief.get("content_theme", "")
    caption_hook = day_brief.get("caption_hook", "")
    key_message = day_brief.get("key_message", "")
    image_prompt = day_brief.get("image_prompt", "")
    hashtags_hint = day_brief.get("hashtags", [])

    business_name = brand_profile.get("business_name", "Brand")
    tone = brand_profile.get("tone", "professional")
    visual_style = brand_profile.get("visual_style", "")
    image_style_directive = brand_profile.get("image_style_directive", "")
    caption_style_directive = brand_profile.get("caption_style_directive", "")
    colors = brand_profile.get("colors", [])

    yield {"event": "status", "data": {"message": f"Crafting {platform} post..."}}

    # Build the prompt
    color_hint = f"Brand colors: {', '.join(colors[:3])}." if colors else ""
    prompt = f"""You are a world-class social media content creator for {business_name}.

Brand tone: {tone}
Visual style: {visual_style}
{caption_style_directive}
{image_style_directive}

Create a {platform} post for the "{pillar}" content pillar on the theme: "{content_theme}".

Start with this hook: "{caption_hook}"
Key message: {key_message}

Write the caption first (2-4 sentences, engaging, on-brand, ends with a call to action).
Then generate a stunning {platform}-optimized image.

{color_hint}
Image visual: {image_prompt}

After the caption, add 5-8 relevant hashtags on a new line starting with HASHTAGS:
"""

    # Call Gemini with interleaved TEXT + IMAGE
    full_caption = ""
    image_bytes = None
    image_mime = "image/png"
    image_url = None
    parsed_hashtags = None  # Set when we find the HASHTAGS: split

    try:
        # Run in thread since the SDK is synchronous
        response = await asyncio.to_thread(
            client.models.generate_content,
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["TEXT", "IMAGE"],
                temperature=0.9,
            ),
        )

        # Process response parts
        for part in response.candidates[0].content.parts:
            if part.text:
                text = part.text
                # Separate caption from hashtags
                if "HASHTAGS:" in text:
                    caption_part, hashtag_part = text.split("HASHTAGS:", 1)
                    full_caption += caption_part.strip()
                    # Parse hashtags
                    raw_tags = hashtag_part.strip().replace("\n", " ")
                    parsed_hashtags = [
                        t.strip().lstrip("#")
                        for t in raw_tags.split()
                        if t.strip()
                    ]
                    yield {
                        "event": "caption",
                        "data": {
                            "text": full_caption,
                            "chunk": False,
                            "hashtags": parsed_hashtags if parsed_hashtags else hashtags_hint,
                        }
                    }
                else:
                    full_caption += text
                    yield {
                        "event": "caption",
                        "data": {"text": text, "chunk": True}
                    }

            elif part.inline_data:
                image_bytes = part.inline_data.data
                image_mime = part.inline_data.mime_type or "image/png"

                yield {"event": "status", "data": {"message": "Uploading image..."}}

                # Upload to GCS
                try:
                    image_url = await upload_image_to_gcs(image_bytes, image_mime, post_id)
                    bt.budget_tracker.record_image()
                    yield {
                        "event": "image",
                        "data": {"url": image_url, "mime_type": image_mime}
                    }
                except Exception as upload_err:
                    logger.error(f"Image upload failed: {upload_err}")
                    # Emit as base64 fallback
                    b64 = base64.b64encode(image_bytes).decode()
                    yield {
                        "event": "image",
                        "data": {
                            "url": f"data:{image_mime};base64,{b64}",
                            "mime_type": image_mime,
                            "fallback": True,
                        }
                    }

        # Final complete event — use parsed_hashtags if available, else fall back to hint
        final_hashtags = parsed_hashtags if parsed_hashtags is not None else hashtags_hint
        yield {
            "event": "complete",
            "data": {
                "post_id": post_id,
                "caption": full_caption.strip(),
                "hashtags": final_hashtags,
                "image_url": image_url,
            }
        }

    except Exception as e:
        logger.error(f"Content generation error for post {post_id}: {e}")
        yield {"event": "error", "data": {"message": str(e)}}
