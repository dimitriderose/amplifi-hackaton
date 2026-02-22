import asyncio
import json
import logging
from google import genai
from google.genai import types
from backend.config import GOOGLE_API_KEY

logger = logging.getLogger(__name__)

client = genai.Client(api_key=GOOGLE_API_KEY)

PLATFORMS = ["instagram", "linkedin", "twitter", "facebook"]
PILLARS = ["education", "inspiration", "promotion", "behind_the_scenes", "user_generated"]


async def run_strategy(brand_id: str, brand_profile: dict, num_days: int = 7) -> list[dict]:
    """Run the Strategy Agent to generate a multi-day content plan.

    Args:
        brand_id: The brand identifier.
        brand_profile: Full brand profile dict from Firestore.
        num_days: Number of day briefs to generate (default 7).

    Returns:
        List of day brief dicts, each describing one day's content.
    """
    prompt = f"""You are a social media strategy expert and creative director.

Your job is to generate a {num_days}-day content calendar for the following brand.

BRAND PROFILE:
{json.dumps(brand_profile, indent=2, default=str)}

Generate exactly {num_days} day briefs. Each brief covers one day of social media content.

Distribute content across platforms strategically. Use a healthy mix of content pillars.
Platforms to use: instagram, linkedin, twitter, facebook
Content pillars to use: education, inspiration, promotion, behind_the_scenes, user_generated

Each day brief MUST have these exact fields:
- day_index: integer (0-based, so first day is 0, last day is {num_days - 1})
- platform: one of "instagram", "linkedin", "twitter", "facebook"
- pillar: one of "education", "inspiration", "promotion", "behind_the_scenes", "user_generated"
- content_theme: string — specific topic or angle for this post (concise, 5-10 words)
- caption_hook: string — opening line designed to stop the scroll (under 15 words, punchy)
- key_message: string — the main takeaway or value this post delivers (1-2 sentences)
- image_prompt: string — detailed visual description for AI image generation (2-3 sentences, very specific about style, colors, composition, mood)
- hashtags: array of 5-8 relevant hashtag strings (without the # symbol)
- derivative_type: "original"

Make the content_theme and caption_hook specific to the brand's industry, tone, and audience.
The image_prompt should reference the brand's visual style and colors if provided.

Return ONLY a valid JSON array of {num_days} objects. No markdown, no extra text.
"""

    try:
        response = await asyncio.to_thread(
            client.models.generate_content,
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )

        raw = response.text.strip()
        # Strip markdown fences if present
        if raw.startswith("```"):
            parts = raw.split("```")
            raw = parts[1] if len(parts) > 1 else raw
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        days = json.loads(raw)
        if not isinstance(days, list):
            raise ValueError(f"Expected JSON array, got {type(days)}")

        # Normalize and validate each day
        validated = []
        for i, day in enumerate(days[:num_days]):
            validated.append(_normalize_day(day, i, brand_profile))

        # Pad if AI returned fewer days than requested
        while len(validated) < num_days:
            validated.append(_fallback_day(len(validated), brand_profile))

        return validated

    except Exception as e:
        logger.error(f"Strategy agent failed for brand {brand_id}: {e}")
        return _fallback_plan(num_days, brand_profile)


def _normalize_day(day: dict, index: int, brand_profile: dict) -> dict:
    """Ensure a day brief has all required fields with valid values."""
    platform = day.get("platform", "").lower()
    if platform not in PLATFORMS:
        platform = PLATFORMS[index % len(PLATFORMS)]

    pillar = day.get("pillar", "").lower().replace(" ", "_")
    if pillar not in PILLARS:
        pillar = PILLARS[index % len(PILLARS)]

    hashtags = day.get("hashtags", [])
    if not isinstance(hashtags, list):
        hashtags = []
    # Strip # prefix if present
    hashtags = [h.lstrip("#") for h in hashtags if isinstance(h, str)]

    return {
        "day_index": int(day.get("day_index", index)),
        "platform": platform,
        "pillar": pillar,
        "content_theme": str(day.get("content_theme", f"Day {index + 1} content")),
        "caption_hook": str(day.get("caption_hook", "Something worth stopping for.")),
        "key_message": str(day.get("key_message", "Share your brand story.")),
        "image_prompt": str(day.get("image_prompt", "Professional brand photo with clean composition.")),
        "hashtags": hashtags[:8],
        "derivative_type": str(day.get("derivative_type", "original")),
    }


def _fallback_day(index: int, brand_profile: dict) -> dict:
    """Generate a single fallback day brief when AI fails."""
    business_name = brand_profile.get("business_name", "your brand")
    industry = brand_profile.get("industry", "business")
    platform = PLATFORMS[index % len(PLATFORMS)]
    pillar = PILLARS[index % len(PILLARS)]

    themes_by_pillar = {
        "education": f"Tips and insights for {industry} enthusiasts",
        "inspiration": f"Why we do what we do at {business_name}",
        "promotion": f"Discover what makes {business_name} different",
        "behind_the_scenes": f"A day in the life at {business_name}",
        "user_generated": f"Our community shares their stories",
    }

    hooks_by_pillar = {
        "education": "Here's what most people don't know.",
        "inspiration": "This is the moment everything changed.",
        "promotion": "Meet the product you didn't know you needed.",
        "behind_the_scenes": "Ever wonder what happens behind closed doors?",
        "user_generated": "Real stories from real people.",
    }

    return {
        "day_index": index,
        "platform": platform,
        "pillar": pillar,
        "content_theme": themes_by_pillar[pillar],
        "caption_hook": hooks_by_pillar[pillar],
        "key_message": f"Showcase the value and authenticity of {business_name}.",
        "image_prompt": (
            f"Professional photo representing {business_name} in the {industry} space. "
            "Clean, modern composition with natural lighting. Brand colors visible. "
            "High quality, authentic feel with generous whitespace."
        ),
        "hashtags": [
            industry.lower().replace(" ", ""),
            business_name.lower().replace(" ", ""),
            pillar.replace("_", ""),
            platform,
            "smallbusiness",
            "contentcreator",
        ],
        "derivative_type": "original",
    }


def _fallback_plan(num_days: int, brand_profile: dict) -> list[dict]:
    """Generate a complete fallback plan when AI strategy fails."""
    logger.warning("Using fallback content plan generation.")
    return [_fallback_day(i, brand_profile) for i in range(num_days)]
