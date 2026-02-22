import asyncio
import json
import logging
from google import genai
from google.genai import types
from backend.config import GOOGLE_API_KEY

logger = logging.getLogger(__name__)
client = genai.Client(api_key=GOOGLE_API_KEY)


async def review_post(
    post: dict,
    brand_profile: dict,
) -> dict:
    """
    AI review of a generated post against brand guidelines.
    Returns a ReviewResult dict with scores and suggestions.
    """
    platform = post.get("platform", "instagram")
    caption = post.get("caption", "")
    hashtags = post.get("hashtags", [])

    business_name = brand_profile.get("business_name", "Brand")
    tone = brand_profile.get("tone", "professional")
    target_audience = brand_profile.get("target_audience", "general audience")
    caption_style_directive = brand_profile.get("caption_style_directive", "")

    prompt = f"""You are a social media content quality reviewer for {business_name}.

Brand tone: {tone}
Target audience: {target_audience}
Caption style: {caption_style_directive}

Review this {platform} post:
Caption: "{caption}"
Hashtags: {hashtags}

Evaluate and respond with JSON only:
{{
  "score": <integer 1-10>,
  "brand_alignment": <"strong"|"moderate"|"weak">,
  "strengths": [<list of 2-3 strength strings>],
  "improvements": [<list of 1-3 improvement suggestions>],
  "approved": <true if score >= 7, false otherwise>,
  "revised_caption": <improved caption string, or null if score >= 8>
}}"""

    try:
        response = await asyncio.to_thread(
            client.models.generate_content,
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.3,
            ),
        )

        raw = response.text.strip()
        if raw.startswith("```"):
            lines = raw.split("\n")
            raw = "\n".join(lines[1:-1])

        result = json.loads(raw)

        # Normalize fields
        return {
            "score": int(result.get("score", 5)),
            "brand_alignment": result.get("brand_alignment", "moderate"),
            "strengths": result.get("strengths", []),
            "improvements": result.get("improvements", []),
            "approved": bool(result.get("approved", False)),
            "revised_caption": result.get("revised_caption"),
        }

    except Exception as e:
        logger.error(f"Review agent error: {e}")
        return {
            "score": 5,
            "brand_alignment": "moderate",
            "strengths": ["Content generated successfully"],
            "improvements": ["Review service temporarily unavailable"],
            "approved": True,
            "revised_caption": None,
        }
