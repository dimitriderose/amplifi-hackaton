import asyncio
import base64
import logging
from typing import AsyncIterator

from google import genai
from google.genai import types

from backend.config import GOOGLE_API_KEY, GEMINI_MODEL
from backend.services import budget_tracker as bt
from backend.services.storage_client import upload_image_to_gcs

logger = logging.getLogger(__name__)
client = genai.Client(api_key=GOOGLE_API_KEY)

# Platform-specific formatting guides injected into every generation prompt
PLATFORM_PROMPTS: dict[str, str] = {
    "instagram": (
        "PLATFORM FORMAT: Instagram caption.\n"
        "- Hook in first line (appears above fold)\n"
        "- 2-3 short paragraphs with line breaks for readability\n"
        "- Call to action (comment, save, share)\n"
        "- 20-30 relevant hashtags at the end, separated from body\n"
        "- Emoji use: moderate, on-brand\n"
        "Max: 2200 characters"
    ),
    "linkedin": (
        "PLATFORM FORMAT: LinkedIn post.\n"
        "- Strong opening hook — first 140 chars appear above \"see more\", make them count\n"
        "- Professional but personable tone\n"
        "- 3-5 short paragraphs with line breaks\n"
        "- End with a question or CTA to drive comments\n"
        "- 3-5 hashtags maximum (LinkedIn penalises over-hashtagging)\n"
        "- Emoji: 1-2 per post max, never decorative\n"
        "Max: 3000 characters"
    ),
    "twitter": (
        "PLATFORM FORMAT: X (Twitter) post.\n"
        "- Concise, punchy, conversational\n"
        "- One clear idea per post\n"
        "- Thread format if content needs more than 280 chars (indicate with \U0001f9f5)\n"
        "- 1-3 hashtags integrated naturally into text (not appended as a block)\n"
        "Max: 280 characters per tweet"
    ),
    "tiktok": (
        "PLATFORM FORMAT: TikTok caption.\n"
        "- Ultra-casual, trend-aware voice\n"
        "- Hook immediately — first 3 words matter most\n"
        "- Mix brand hashtags with trending tags\n"
        "- CTA: 'Follow for more' or 'Save this for later'\n"
        "Max: 2200 characters"
    ),
    "facebook": (
        "PLATFORM FORMAT: Facebook post.\n"
        "- Conversational, community-oriented tone\n"
        "- Ask questions to drive comments\n"
        "- Longer form acceptable; storytelling works well\n"
        "- 1-3 hashtags or none\n"
        "- Emoji use: moderate"
    ),
}


async def generate_post(
    plan_id: str,
    day_brief: dict,
    brand_profile: dict,
    post_id: str,
    custom_photo_bytes: bytes | None = None,
    custom_photo_mime: str = "image/jpeg",
    instructions: str | None = None,
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
    derivative_type = day_brief.get("derivative_type", "original")

    business_name = brand_profile.get("business_name", "Brand")
    tone = brand_profile.get("tone", "professional")
    visual_style = brand_profile.get("visual_style", "")
    image_style_directive = brand_profile.get("image_style_directive", "")
    caption_style_directive = brand_profile.get("caption_style_directive", "")
    colors = brand_profile.get("colors", [])
    style_reference_gcs_uri = brand_profile.get("style_reference_gcs_uri")

    # Format-specific instructions for derivative post types
    _DERIVATIVE_INSTRUCTIONS: dict[str, str] = {
        "carousel": (
            "FORMAT: Instagram/LinkedIn CAROUSEL\n"
            "Structure the caption as slide-by-slide copy:\n"
            "  Slide 1: Hook (compelling, ≤10 words — this becomes the cover)\n"
            "  Slide 2–5: One punchy insight per slide with a bold heading + 1-line body\n"
            "  Final slide: Key takeaway + call to action\n"
            "Label each slide clearly: 'Slide 1:', 'Slide 2:', etc."
        ),
        "thread_hook": (
            "FORMAT: Twitter/X THREAD\n"
            "Write 5 tweets, numbered:\n"
            "  1/ Hook that stops the scroll (≤280 chars, must create curiosity)\n"
            "  2/ – 4/ One key insight per tweet, concise and punchy (≤280 chars each)\n"
            "  5/ Takeaway + call to action (≤280 chars)\n"
            "Separate each tweet with a blank line. Each must stand alone."
        ),
        "blog_snippet": (
            "FORMAT: LinkedIn THOUGHT LEADERSHIP excerpt\n"
            "Write 150–200 words total:\n"
            "  - Bold opening statement (opinion-forward, 1 sentence)\n"
            "  - 2–3 short paragraphs expanding the idea with a real insight or example\n"
            "  - Closing question to spark discussion in the comments\n"
            "Professional but conversational tone."
        ),
        "story": (
            "FORMAT: Instagram/Facebook STORY\n"
            "Write ≤50 words total — short, punchy, immediate:\n"
            "  - First line: big emotion, bold question, or surprising statement\n"
            "  - One clear call to action (swipe up / reply / DM us)\n"
            "No hashtags in the body — add them in the HASHTAGS section only."
        ),
    }
    derivative_instruction = _DERIVATIVE_INSTRUCTIONS.get(derivative_type, "")
    platform_format = PLATFORM_PROMPTS.get(platform, "")
    instruction_hint = (
        f"\n\nAdditional instructions for this generation: {instructions.strip()}"
        if instructions and instructions.strip()
        else ""
    )

    # ── BYOP mode ─────────────────────────────────────────────────────────────
    if custom_photo_bytes:
        yield {"event": "status", "data": {"message": "Analyzing your photo..."}}

        byop_prompt = f"""You are a world-class social media content creator for {business_name}.

Brand tone: {tone}
Visual style: {visual_style}
{caption_style_directive}
{f"CONTENT FORMAT:{chr(10)}{derivative_instruction}{chr(10)}" if derivative_instruction else ""}{f"{platform_format}{chr(10)}" if platform_format else ""}
Analyze this photo and write a {platform} post caption that:
- Complements and describes what's in the photo
- Fits the "{content_theme}" theme for the "{pillar}" content pillar
- Starts with this hook: "{caption_hook}"
- Carries this key message: {key_message}
- Ends with a call to action
{instruction_hint}
After the caption, add 5-8 relevant hashtags on a new line starting with HASHTAGS:
"""

        try:
            image_part = types.Part(
                inline_data=types.Blob(data=custom_photo_bytes, mime_type=custom_photo_mime)
            )
            text_part = types.Part(text=byop_prompt)

            response = await asyncio.to_thread(
                client.models.generate_content,
                model=GEMINI_MODEL,
                contents=[image_part, text_part],
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
            image_gcs_uri = None
            try:
                image_url, image_gcs_uri = await upload_image_to_gcs(
                    custom_photo_bytes, custom_photo_mime, post_id
                )
                yield {
                    "event": "image",
                    "data": {"url": image_url, "mime_type": custom_photo_mime, "gcs_uri": image_gcs_uri},
                }
            except Exception as upload_err:
                logger.error("BYOP photo upload failed: %s", upload_err)
                b64 = base64.b64encode(custom_photo_bytes).decode()
                image_url = f"data:{custom_photo_mime};base64,{b64}"
                yield {
                    "event": "image",
                    "data": {
                        "url": image_url,
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
                    "image_gcs_uri": image_gcs_uri,
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
    style_ref_block = (
        "VISUAL CONSISTENCY: The provided reference image shows this brand's visual identity — "
        "color palette, lighting style, and mood. Every image you generate must feel cohesive "
        "with this reference. Match the warmth, saturation, and composition style exactly.\n"
    ) if style_reference_gcs_uri else ""
    prompt = f"""You are a world-class social media content creator for {business_name}.

Brand tone: {tone}
Visual style: {visual_style}
{caption_style_directive}
{image_style_directive}
{style_ref_block}{f"CONTENT FORMAT:{chr(10)}{derivative_instruction}{chr(10)}" if derivative_instruction else ""}{f"{platform_format}{chr(10)}" if platform_format else ""}
Create a {platform} post for the "{pillar}" content pillar on the theme: "{content_theme}".

Start with this hook: "{caption_hook}"
Key message: {key_message}

Write the caption first (following the format above if specified), engaging and on-brand, ending with a call to action.
Then generate a stunning {platform}-optimized image.

{color_hint}
Image visual: {image_prompt}
{instruction_hint}
After the caption, add 5-8 relevant hashtags on a new line starting with HASHTAGS:
"""

    full_caption = ""
    image_bytes = None
    image_mime = "image/png"
    image_url = None
    image_gcs_uri = None
    parsed_hashtags = None

    try:
        # Build contents: prepend style reference image when available
        if style_reference_gcs_uri:
            gen_contents = [
                types.Part(file_data=types.FileData(
                    file_uri=style_reference_gcs_uri, mime_type="image/png"
                )),
                types.Part(text=prompt),
            ]
        else:
            gen_contents = prompt

        response = await asyncio.to_thread(
            client.models.generate_content,
            model=GEMINI_MODEL,
            contents=gen_contents,
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
                    image_url, image_gcs_uri = await upload_image_to_gcs(image_bytes, image_mime, post_id)
                    bt.budget_tracker.record_image()
                    yield {
                        "event": "image",
                        "data": {"url": image_url, "mime_type": image_mime, "gcs_uri": image_gcs_uri}
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
                "image_gcs_uri": image_gcs_uri,
            }
        }

    except Exception as e:
        logger.error("Content generation error for post %s: %s", post_id, e)
        yield {"event": "error", "data": {"message": str(e)}}
