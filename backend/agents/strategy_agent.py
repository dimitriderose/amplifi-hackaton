import asyncio
import json
import logging
from google import genai
from google.genai import types
from backend.config import GOOGLE_API_KEY, GEMINI_MODEL
from backend.services import firestore_client

logger = logging.getLogger(__name__)

client = genai.Client(api_key=GOOGLE_API_KEY)

PLATFORMS = ["instagram", "linkedin", "twitter", "facebook"]
PILLARS = ["education", "inspiration", "promotion", "behind_the_scenes", "user_generated"]
DERIVATIVE_TYPES = ["original", "carousel", "thread_hook", "blog_snippet", "story"]


async def _research_platform_trends(platform: str, industry: str) -> dict | None:
    """Fetch current platform+industry trends via Google Search grounding.

    Results are cached in Firestore for 7 days.
    Returns None if research fails — callers treat it as optional enhancement.
    """
    # Check cache first
    try:
        cached = await firestore_client.get_platform_trends(platform, industry)
        if cached:
            logger.info("Platform trends cache hit: %s / %s", platform, industry)
            return cached
    except Exception as e:
        logger.warning("Trend cache read error: %s", e)

    # Fetch from Gemini with Google Search grounding
    try:
        prompt = (
            f"Research the current trending content patterns on {platform} "
            f"for the {industry} industry. What's working right now (this week/month)?\n"
            "- Trending formats (carousel, short video, text post, etc.)\n"
            "- Trending topics or hooks\n"
            "- Algorithm preferences (what's being boosted?)\n"
            "- Best posting time recommendations\n\n"
            'Return ONLY a valid JSON object with these keys: '
            '{"trending_formats": [...], "trending_hooks": [...], '
            '"algorithm_notes": "...", "best_posting_times": [...]}'
        )
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                temperature=0.2,
            ),
        )
        raw = response.text.strip()
        # Strip markdown fences if present
        if raw.startswith("```"):
            parts = raw.split("```")
            raw = parts[1] if len(parts) > 1 else raw
            if raw.startswith("json"):
                raw = raw[4:]
        trends = json.loads(raw.strip())

        # Save to cache (best-effort)
        try:
            await firestore_client.save_platform_trends(platform, industry, trends)
        except Exception as ce:
            logger.warning("Trend cache write error: %s", ce)

        return trends
    except Exception as e:
        logger.warning("Platform trend research failed (%s/%s): %s", platform, industry, e)
        return None


async def run_strategy(brand_id: str, brand_profile: dict, num_days: int = 7, business_events: str | None = None) -> list[dict]:
    """Run the Strategy Agent to generate a multi-day content plan.

    Args:
        brand_id: The brand identifier.
        brand_profile: Full brand profile dict from Firestore.
        num_days: Number of day briefs to generate (default 7).
        business_events: Optional string describing real business events this week.

    Returns:
        List of day brief dicts, each describing one day's content.
    """
    # Fetch platform trend intelligence (best-effort, non-blocking)
    industry = brand_profile.get("industry", "")
    primary_platform = PLATFORMS[0]  # Instagram as primary trend lookup
    trends = await _research_platform_trends(primary_platform, industry)
    trends_context = ""
    if trends:
        trends_context = f"""
CURRENT PLATFORM TRENDS ({primary_platform.upper()} · {industry}):
- Trending formats: {', '.join(trends.get('trending_formats', [])[:4])}
- Trending hooks: {', '.join(trends.get('trending_hooks', [])[:4])}
- Algorithm notes: {trends.get('algorithm_notes', 'N/A')}
- Best posting times: {', '.join(trends.get('best_posting_times', [])[:3])}

Incorporate these trends where they fit the brand. Don't force them — only use what is authentic to this brand.
"""

    prompt = f"""You are a social media strategy expert and creative director.

Your job is to generate a {num_days}-day content calendar for the following brand.

BRAND PROFILE:
{json.dumps(brand_profile, indent=2, default=str)}
{trends_context}
BUSINESS_EVENTS_THIS_WEEK: {business_events or "None provided — generate thematic pillars based on brand profile."}

Generate exactly {num_days} day briefs. Each brief covers one day of social media content.

Distribute content across platforms strategically. Use a healthy mix of content pillars.
Platforms to use: instagram, linkedin, twitter, facebook
Content pillars to use: education, inspiration, promotion, behind_the_scenes, user_generated

INSTAGRAM CAROUSEL POSTS (IMPORTANT):
For Instagram posts, decide whether the post works better as a SINGLE IMAGE or a CAROUSEL (3 slides).
Use derivative_type "carousel" for Instagram posts with educational, how-to, tip-based, listicle, before/after, or multi-point content.
Use derivative_type "original" for Instagram posts with single mood shots, announcements, quotes, or simple product features.
Aim for roughly half of Instagram posts to be carousels across the week.

CONTENT REPURPOSING (IMPORTANT — follow this carefully):
Choose exactly 2 "hero" content ideas that will be repurposed across different platforms this week.
For each hero idea:
  - ONE day is the ORIGINAL hero post: derivative_type "original" or "carousel" (if Instagram), ideally on Instagram or LinkedIn.
  - ONE OR TWO other days REPURPOSE that idea for a different platform and format:
      derivative_type must be one of: "carousel", "thread_hook", "blog_snippet", "story"
      - carousel: multi-slide visual breakdown (Instagram or LinkedIn)
      - thread_hook: Twitter/X thread opening + key points
      - blog_snippet: LinkedIn thought-leadership excerpt (longer, professional tone)
      - story: Quick, punchy Instagram/Facebook story-format post
  - All days in the same repurposing group MUST share the same pillar_id string (e.g., "series_0").
  - Adapt content_theme, caption_hook, and image_prompt to suit the derivative platform/format.
Remaining days (not part of any repurposing series) each get their own unique pillar_id (e.g., "series_2", "series_3", …) and derivative_type "original" (or "carousel" if Instagram and content fits).

Each day brief MUST have these exact fields:
- day_index: integer (0-based, so first day is 0, last day is {num_days - 1})
- platform: one of "instagram", "linkedin", "twitter", "facebook"
- pillar: one of "education", "inspiration", "promotion", "behind_the_scenes", "user_generated"
- pillar_id: string — repurposing group ID (e.g., "series_0"). Hero + derivatives share one ID; standalone days get their own unique ID.
- content_theme: string — specific topic or angle for this post (concise, 5-10 words)
- caption_hook: string — opening line designed to stop the scroll (under 15 words, punchy)
- key_message: string — the main takeaway or value this post delivers (1-2 sentences)
- image_prompt: string — detailed visual description for AI image generation (2-3 sentences, very specific about style, colors, composition, mood)
- hashtags: array of 5-8 relevant hashtag strings (without the # symbol)
- derivative_type: "original" for hero posts; "carousel", "thread_hook", "blog_snippet", or "story" for repurposed derivatives
- event_anchor: string or null — short event name if this day's content is directly tied to a business event, otherwise null

Make the content_theme and caption_hook specific to the brand's industry, tone, and audience.
The image_prompt should reference the brand's visual style and colors if provided.

EVENT-AWARE PLANNING:
- If BUSINESS_EVENTS_THIS_WEEK is provided, identify 1-2 of the most impactful events and make them content pillars
- Events become the "promotion" or "behind_the_scenes" day brief for the day they occur
- Derivative posts can reference the event (e.g. "The launch is tomorrow — here's why we created this")
- Add an "event_anchor" field to day briefs where the content is directly tied to a business event (value = short event name string, null otherwise)
- Other days can build anticipation for or reflect on the event

Return ONLY a valid JSON array of {num_days} objects. No markdown, no extra text.
"""

    try:
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=GEMINI_MODEL,
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

        # Cap group sizes: if LLM reuses the same pillar_id on too many days,
        # break extras out as standalones so the UI grouping stays meaningful
        validated = _enforce_group_size(validated)

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

    derivative_type = str(day.get("derivative_type", "original")).lower()
    if derivative_type not in DERIVATIVE_TYPES:
        derivative_type = "original"

    return {
        "day_index": int(day.get("day_index", index)),
        "platform": platform,
        "pillar": pillar,
        "pillar_id": str(day.get("pillar_id", f"series_{index}")),
        "content_theme": str(day.get("content_theme", f"Day {index + 1} content")),
        "caption_hook": str(day.get("caption_hook", "Something worth stopping for.")),
        "key_message": str(day.get("key_message", "Share your brand story.")),
        "image_prompt": str(day.get("image_prompt", "Professional brand photo with clean composition.")),
        "hashtags": hashtags[:8],
        "derivative_type": derivative_type,
        "event_anchor": day.get("event_anchor", None),
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
        "pillar_id": f"series_{index}",
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
        "event_anchor": None,
    }


def _enforce_group_size(days: list[dict], max_group_size: int = 3) -> list[dict]:
    """Break out excess days from oversized pillar_id groups.

    Prevents the LLM from assigning the same pillar_id to all days, which would
    color every card with the same series accent and make grouping meaningless.
    Any day beyond the first max_group_size in a group gets a unique standalone ID.
    """
    group_seen: dict[str, int] = {}
    standalone_idx = 9000  # start high to avoid collisions with "series_N" IDs
    result = []
    for day in days:
        pid = day["pillar_id"]
        count = group_seen.get(pid, 0)
        if count >= max_group_size:
            day = {**day, "pillar_id": f"series_{standalone_idx}", "derivative_type": "original"}
            standalone_idx += 1
        else:
            group_seen[pid] = count + 1
        result.append(day)
    return result


def _fallback_plan(num_days: int, brand_profile: dict) -> list[dict]:
    """Generate a complete fallback plan when AI strategy fails."""
    logger.warning("Using fallback content plan generation.")
    return [_fallback_day(i, brand_profile) for i in range(num_days)]
