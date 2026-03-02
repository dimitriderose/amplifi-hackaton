import asyncio
import json
import logging
from google import genai
from google.genai import types
from backend.config import GOOGLE_API_KEY, GEMINI_MODEL
from backend.platforms import keys as platform_keys, get as get_platform
from backend.services import firestore_client

logger = logging.getLogger(__name__)

client = genai.Client(api_key=GOOGLE_API_KEY)

PILLARS = ["education", "inspiration", "promotion", "behind_the_scenes", "user_generated"]
DERIVATIVE_TYPES = [
    "original", "carousel", "thread_hook", "blog_snippet", "story",
    "pin", "video_first",
]


# ── Platform intelligence ─────────────────────────────────────────────────────

async def _research_best_platforms(
    brand_profile: dict,
    available_platforms: list[str],
) -> list[dict]:
    """Research which social platforms are best for this business.

    Uses Google Search grounding to get current data on platform demographics
    and effectiveness for this specific industry + audience.

    Returns ranked list: [{"platform": "instagram", "reason": "...", "priority": 1}, ...]
    """
    business_type = brand_profile.get("business_type", "")
    industry = brand_profile.get("industry", "")
    target_audience = brand_profile.get("target_audience", "")
    content_themes = brand_profile.get("content_themes", [])
    tone = brand_profile.get("tone", "")

    # Check Firestore cache first (keyed by industry + business_type, TTL 7 days)
    try:
        cached = await firestore_client.get_platform_recommendations(industry, business_type)
        if cached:
            logger.info("Platform recommendations cache hit: %s / %s", industry, business_type)
            return cached
    except Exception:
        pass

    prompt = (
        f"Research the best social media platforms for a {business_type} "
        f"in the {industry} industry.\n"
        f"Target audience: {target_audience}\n"
        f"Brand tone: {tone}\n"
        f"Content themes: {', '.join(content_themes[:5]) if content_themes else 'general'}\n\n"
        f"Available platforms: {', '.join(available_platforms)}\n\n"
        "Based on current data (2025-2026), rank the TOP 5 platforms for this "
        "specific business type and audience. Consider:\n"
        "- Which platforms does this target audience actually use?\n"
        "- Which platforms favor this type of content/industry?\n"
        "- Where are similar businesses seeing the most engagement?\n"
        "- Platform demographics alignment with the target audience\n\n"
        "Return ONLY a valid JSON array of objects, ranked best to worst:\n"
        '[{"platform": "instagram", "reason": "Why this platform fits", "priority": 1}, ...]'
    )

    try:
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                response_mime_type="application/json",
                temperature=0.2,
            ),
        )
        raw = response.text.strip()
        if raw.startswith("```"):
            parts = raw.split("```")
            raw = parts[1] if len(parts) > 1 else raw
            if raw.startswith("json"):
                raw = raw[4:]
        recommendations = json.loads(raw.strip())

        # Validate — only keep platforms from our available list
        valid = [r for r in recommendations if r.get("platform") in available_platforms]

        # Cache for 7 days (best-effort)
        try:
            await firestore_client.save_platform_recommendations(industry, business_type, valid)
        except Exception:
            pass

        return valid[:5]
    except Exception as e:
        logger.warning("Platform recommendation research failed: %s", e)
        return []


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
            f"Research the current content strategy best practices on {platform} "
            f"for the {industry} industry. What's working right now?\n"
            "- What content FORMATS are getting the most engagement? (carousel, video, text, etc.)\n"
            "- Trending topics or hooks for this industry\n"
            "- Algorithm preferences (what's being boosted vs suppressed?)\n"
            "- Best posting time recommendations\n"
            "- Character/length sweet spots for captions\n\n"
            'Return ONLY a valid JSON object with these keys: '
            '{"trending_formats": [...], "trending_hooks": [...], '
            '"algorithm_notes": "...", "best_posting_times": [...], '
            '"best_content_format": "...", "caption_sweet_spot": "..."}'
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


# ── Format-aware planning notes ───────────────────────────────────────────────

_FORMAT_GUIDE = """PLATFORM FORMAT GUIDANCE (match content format to what works on each platform):

INSTAGRAM — Carousel or Reels:
  - Carousels get 10% engagement (highest of any format). Use for educational/tip content.
  - Static images declining 17% YoY — avoid when possible.
  - Use derivative_type "carousel" for most Instagram posts.
  - DM shares and saves are the #1 algorithm signals.

LINKEDIN — Document Carousel or Thought Leadership:
  - Document/carousel posts get 596% more engagement than text-only.
  - Structure as frameworks, checklists, step-by-step guides.
  - Use derivative_type "carousel" for LinkedIn educational content.
  - Use derivative_type "blog_snippet" for opinion/thought leadership.

X/TWITTER — Video + Short Text or Thread:
  - 4 out of 5 sessions now include video — video is the dominant format.
  - Use derivative_type "video_first" for X when possible.
  - Use derivative_type "thread_hook" for multi-point educational content.
  - Single tweets: keep under 200 chars, designed to spark quick replies.

TIKTOK — Photo Carousel or Short Video:
  - Photo carousels are getting algorithm-boosted reach.
  - Use derivative_type "carousel" for TikTok educational/list content.
  - Problem-solution and behind-the-scenes content outperforms polished.

FACEBOOK — Mixed (Carousel, Photo, or Reel):
  - Format-agnostic algorithm. Shares/saves worth 50x likes.
  - Use derivative_type "carousel" for storytelling, "story" for stories.
  - Community-oriented, question-based content drives comments.

THREADS — Conversation Starter + Image:
  - Image posts get 60% more engagement than text-only.
  - Algorithm SUPPRESSES promotional content — be authentic.
  - Use derivative_type "original" — always text+image.
  - End with a question or hot take.

PINTEREST — SEO Pin + Visual:
  - Idea Pins (multi-image) get 4x engagement of standard pins.
  - Pinterest is a SEARCH ENGINE — keyword-rich titles and descriptions.
  - Use derivative_type "pin" — caption format is PIN TITLE + PIN DESCRIPTION.

YOUTUBE SHORTS — Video Description:
  - Video-first platform. Our job is to generate the description/caption.
  - Use derivative_type "video_first".
  - First 125 chars appear in search — include primary keyword.

MASTODON — Text + Essential Hashtags:
  - NO algorithm — hashtags ARE the only discovery mechanism.
  - Community-first, anti-spam. Earn boosts by being genuinely useful.
  - Use derivative_type "original" — text + optional image.
  - CamelCase hashtags are critical for accessibility and discovery.

BLUESKY — Thread or Short Take + Image:
  - Threads get 3x engagement vs single posts.
  - Custom feeds drive 5x impressions.
  - Replies are the #1 metric, not likes.
  - Use derivative_type "thread_hook" for multi-point content.
  - 300 char limit, so single posts must be ultra-concise.
"""


# ── Main strategy agent ──────────────────────────────────────────────────────

async def run_strategy(
    brand_id: str,
    brand_profile: dict,
    num_days: int = 7,
    business_events: str | None = None,
    platforms: list[str] | None = None,
) -> list[dict]:
    """Run the Strategy Agent to generate a multi-day content plan.

    Args:
        brand_id: The brand identifier.
        brand_profile: Full brand profile dict from Firestore.
        num_days: Number of day briefs to generate (default 7).
        business_events: Optional string describing real business events this week.
        platforms: Optional list of platform keys. If None, AI recommends platforms.

    Returns:
        List of day brief dicts, each describing one day's content.
    """
    industry = brand_profile.get("industry", "")
    all_platforms = platform_keys()

    # ── Phase 0a: Determine platforms ─────────────────────────────────────────
    platform_reasoning = ""
    if platforms:
        # User specified platforms — validate and use them directly
        platforms = [p for p in platforms if p in all_platforms or p == "twitter"]
        if not platforms:
            platforms = ["instagram", "linkedin"]
        logger.info("User-selected platforms for %s: %s", brand_id, platforms)
    else:
        # AI selects best platforms for this business
        recommendations = await _research_best_platforms(brand_profile, all_platforms)
        if recommendations:
            platforms = [r["platform"] for r in recommendations]
            platform_reasoning = "\n".join(
                f"- {r['platform'].upper()}: {r['reason']}" for r in recommendations
            )
            logger.info("AI-recommended platforms for %s: %s", brand_id, platforms)
        else:
            platforms = ["instagram", "linkedin", "x", "facebook"]
            platform_reasoning = ""

    # ── Phase 0b: Fetch trends for selected platforms (in parallel) ───────────
    trend_platforms = platforms[:5]  # Limit to 5 to avoid rate limits
    trend_results = await asyncio.gather(
        *[_research_platform_trends(p, industry) for p in trend_platforms],
        return_exceptions=True,
    )
    trends_context = ""
    platform_trends_map: dict[str, dict] = {}
    for p, result in zip(trend_platforms, trend_results):
        if isinstance(result, dict):
            platform_trends_map[p] = result
            trends_context += (
                f"\nCURRENT TRENDS ({p.upper()} · {industry}):\n"
                f"- Trending formats: {', '.join(result.get('trending_formats', [])[:4])}\n"
                f"- Trending hooks: {', '.join(result.get('trending_hooks', [])[:4])}\n"
                f"- Algorithm notes: {result.get('algorithm_notes', 'N/A')}\n"
                f"- Best posting times: {', '.join(result.get('best_posting_times', [])[:3])}\n"
            )
    if trends_context:
        trends_context += (
            "\nIncorporate these trends where they fit the brand. "
            "Don't force them — only use what is authentic.\n"
        )

    # ── Build strategy prompt ─────────────────────────────────────────────────
    platform_list = ", ".join(platforms)
    platform_rec_block = ""
    if platform_reasoning:
        platform_rec_block = (
            f"\nRECOMMENDED PLATFORMS (based on industry + audience research):\n"
            f"{platform_reasoning}\n"
        )

    prompt = f"""You are a social media strategy expert and creative director.

Your job is to generate a {num_days}-day content calendar for the following brand.

BRAND PROFILE:
{json.dumps(brand_profile, indent=2, default=str)}
{platform_rec_block}{trends_context}
BUSINESS_EVENTS_THIS_WEEK: {business_events or "None provided — generate thematic pillars based on brand profile."}

Generate exactly {num_days} day briefs. Each brief covers one day of social media content.

CRITICAL — GO DEEP, NOT WIDE:
You have {num_days} days of content and these platforms available: {platform_list}
Do NOT spread across all platforms. Pick the TOP 2-4 platforms and give them multiple
posts each. It's better to post 3x/week on Instagram than 1x on 5 different platforms.
Most platform algorithms reward consistency (3-5 posts/week minimum).
Prioritize the top-ranked platforms — they should get the majority of days.

Content pillars to use: education, inspiration, promotion, behind_the_scenes, user_generated

{_FORMAT_GUIDE}

CAROUSEL POSTS (IMPORTANT):
For Instagram and LinkedIn posts, decide whether the post works better as a SINGLE IMAGE or a CAROUSEL (3 slides).
Use derivative_type "carousel" for posts with educational, how-to, tip-based, listicle, before/after, or multi-point content.
Use derivative_type "original" for posts with single mood shots, announcements, quotes, or simple product features.

CONTENT REPURPOSING (IMPORTANT — follow this carefully):
Choose exactly 2 "hero" content ideas that will be repurposed across different platforms this week.
For each hero idea:
  - ONE day is the ORIGINAL hero post: derivative_type "original" or "carousel", ideally on the top-priority platform.
  - ONE OR TWO other days REPURPOSE that idea for a different platform and format:
      derivative_type must be one of: "carousel", "thread_hook", "blog_snippet", "story", "pin", "video_first"
  - All days in the same repurposing group MUST share the same pillar_id string (e.g., "series_0").
  - Adapt content_theme, caption_hook, and image_prompt to suit the derivative platform/format.
Remaining days each get their own unique pillar_id and derivative_type "original" (or format-appropriate type).

Each day brief MUST have these exact fields:
- day_index: integer (0-based, so first day is 0, last day is {num_days - 1})
- platform: one of {json.dumps(platforms)}
- pillar: one of "education", "inspiration", "promotion", "behind_the_scenes", "user_generated"
- pillar_id: string — repurposing group ID (e.g., "series_0")
- content_theme: string — specific topic or angle (5-10 words)
- caption_hook: string — opening line to stop the scroll (under 15 words)
- key_message: string — main takeaway (1-2 sentences)
- image_prompt: string — detailed visual description for AI image generation (2-3 sentences)
- hashtags: array of 5-8 relevant hashtag strings (without the # symbol)
- derivative_type: one of "original", "carousel", "thread_hook", "blog_snippet", "story", "pin", "video_first"
- event_anchor: string or null

Make the content_theme and caption_hook specific to the brand's industry, tone, and audience.
The image_prompt should reference the brand's visual style and colors if provided.

EVENT-AWARE PLANNING:
- If BUSINESS_EVENTS_THIS_WEEK is provided, identify 1-2 impactful events and make them content pillars
- Events become the "promotion" or "behind_the_scenes" day brief
- Add "event_anchor" field where content is tied to a business event (null otherwise)

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
            validated.append(
                _normalize_day(day, i, brand_profile, platforms, platform_trends_map)
            )

        # Pad if AI returned fewer days than requested
        while len(validated) < num_days:
            validated.append(_fallback_day(len(validated), brand_profile, platforms))

        # Cap group sizes
        validated = _enforce_group_size(validated)

        return validated

    except Exception as e:
        logger.error(f"Strategy agent failed for brand {brand_id}: {e}")
        return _fallback_plan(num_days, brand_profile, platforms)


def _normalize_day(
    day: dict,
    index: int,
    brand_profile: dict,
    platforms: list[str],
    platform_trends_map: dict[str, dict] | None = None,
) -> dict:
    """Ensure a day brief has all required fields with valid values."""
    all_platforms = platform_keys()
    platform = get_platform(day.get("platform", "")).key
    if platform not in platforms:
        platform = platforms[index % len(platforms)]

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

    result = {
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

    # Attach platform trend intelligence for content creator
    if platform_trends_map and platform in platform_trends_map:
        result["platform_trends"] = platform_trends_map[platform]

    return result


def _fallback_day(
    index: int,
    brand_profile: dict,
    platforms: list[str] | None = None,
) -> dict:
    """Generate a single fallback day brief when AI fails."""
    if not platforms:
        platforms = ["instagram", "linkedin", "x", "facebook"]
    business_name = brand_profile.get("business_name", "your brand")
    industry = brand_profile.get("industry", "business")
    platform = platforms[index % len(platforms)]
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


def _fallback_plan(
    num_days: int,
    brand_profile: dict,
    platforms: list[str] | None = None,
) -> list[dict]:
    """Generate a complete fallback plan when AI strategy fails."""
    logger.warning("Using fallback content plan generation.")
    return [_fallback_day(i, brand_profile, platforms) for i in range(num_days)]
