import asyncio
import base64
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
    custom_photo_bytes: bytes | None = None,
    custom_photo_mime: str = "image/jpeg",
) -> AsyncIterator[dict]:
    """
    Generate a social media post using Gemini 2.5 Flash.

    If custom_photo_bytes is provided (BYOP mode): Gemini vision analyzes the
    photo and writes a caption; the photo is used as the hero image (no image
    generation budget consumed).

    Otherwise: interleaved TEXT+IMAGE generation (normal mode).

    Yields SSE-compatible event dicts: {"event": str, "data": dict}

    Events emitted (in order):
      {"event": "status",  "data": {"message": "..."}}
      {"event": "caption", "data": {"text": "...", "chunk": True}}   # streamed chunks
      {"event": "caption", "data": {"text": "...", "chunk": False, "hashtags": [...]}}  # final
      {"event": "image",   "data": {"url": "...", "mime_type": "image/png"}}
      {"event": "complete","data": {"post_id": "...", "caption": "...", "hashtags": [...], "image_url": "..."}}
      {"event": "error",   "data": {"message": "..."}}  # on failure
    """

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

    # ── BYOP mode ─────────────────────────────────────────────────────────────
    if custom_photo_bytes:
        yield {"event": "status", "data": {"message": "Analyzing your photo..."}}

        byop_prompt = f"""You are a world-class social media content creator for {business_name}.

Brand tone: {tone}
Visual style: {visual_style}
{caption_style_directive}

Analyze this photo and write a {platform} post caption that:
- Complements and describes what's in the photo
- Fits the "{content_theme}" theme for the "{pillar}" content pillar
- Starts with this hook: "{caption_hook}"
- Carries this key message: {key_message}
- Ends with a call to action
- Is 2-4 sentences, engaging and on-brand

After the caption, add 5-8 relevant hashtags on a new line starting with HASHTAGS:
"""

        try:
            image_part = types.Part(
                inline_data=types.Blob(data=custom_photo_bytes, mime_type=custom_photo_mime)
            )

            response = await asyncio.to_thread(
                client.models.generate_content,
                model="gemini-2.5-flash",
                contents=[image_part, byop_prompt],
                config=types.GenerateContentConfig(
                    response_modalities=["TEXT"],
                    temperature=0.9,
                ),
            )

            full_text = "".join(
                part.text for part in response.candidates[0].content.parts if part.text
            )

            if "HASHTAGS:" in full_text:
                caption_part, hashtag_part = full_text.split("HASHTAGS:", 1)
                full_caption = caption_part.strip()
                raw_tags = hashtag_part.strip().replace("\n", " ")
                parsed_hashtags = [t.strip().lstrip("#") for t in raw_tags.split() if t.strip()]
            else:
                full_caption = full_text.strip()
                parsed_hashtags = hashtags_hint

            yield {
                "event": "caption",
                "data": {"text": full_caption, "chunk": False, "hashtags": parsed_hashtags},
            }

            # Save the user's photo under the post's GCS path
            yield {"event": "status", "data": {"message": "Saving your photo..."}}
            image_url = None
            try:
                image_url = await upload_image_to_gcs(custom_photo_bytes, custom_photo_mime, post_id)
                yield {"event": "image", "data": {"url": image_url, "mime_type": custom_photo_mime}}
            except Exception as upload_err:
                logger.error("BYOP photo upload failed: %s", upload_err)
                b64 = base64.b64encode(custom_photo_bytes).decode()
                yield {
                    "event": "image",
                    "data": {
                        "url": f"data:{custom_photo_mime};base64,{b64}",
                        "mime_type": custom_photo_mime,
                        "fallback": True,
                    },
                }

            yield {
                "event": "complete",
                "data": {
                    "post_id": post_id,
                    "caption": full_caption,
                    "hashtags": parsed_hashtags,
                    "image_url": image_url,
                },
            }

        except Exception as e:
            logger.error("BYOP generation error for post %s: %s", post_id, e)
            yield {"event": "error", "data": {"message": str(e)}}

        return  # Do not fall through to normal generation

    # ── Normal mode (interleaved TEXT + IMAGE) ────────────────────────────────

    # Check budget
    if not bt.budget_tracker.can_generate_image():
        yield {"event": "error", "data": {"message": "Image budget exhausted"}}
        return

    yield {"event": "status", "data": {"message": f"Crafting {platform} post..."}}

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

    full_caption = ""
    image_bytes = None
    image_mime = "image/png"
    image_url = None
    parsed_hashtags = None

    try:
        response = await asyncio.to_thread(
            client.models.generate_content,
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["TEXT", "IMAGE"],
                temperature=0.9,
            ),
        )

        for part in response.candidates[0].content.parts:
            if part.text:
                text = part.text
                if "HASHTAGS:" in text:
                    caption_part, hashtag_part = text.split("HASHTAGS:", 1)
                    full_caption += caption_part.strip()
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

                try:
                    image_url = await upload_image_to_gcs(image_bytes, image_mime, post_id)
                    bt.budget_tracker.record_image()
                    yield {
                        "event": "image",
                        "data": {"url": image_url, "mime_type": image_mime}
                    }
                except Exception as upload_err:
                    logger.error("Image upload failed: %s", upload_err)
                    b64 = base64.b64encode(image_bytes).decode()
                    yield {
                        "event": "image",
                        "data": {
                            "url": f"data:{image_mime};base64,{b64}",
                            "mime_type": image_mime,
                            "fallback": True,
                        }
                    }

        final_hashtags = parsed_hashtags if parsed_hashtags else hashtags_hint
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
        logger.error("Content generation error for post %s: %s", post_id, e)
        yield {"event": "error", "data": {"message": str(e)}}
