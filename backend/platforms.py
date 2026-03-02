"""Platform Registry — single source of truth for all platform-specific configuration.

Every backend agent imports from this module instead of maintaining local platform dicts.
Adding a new platform = add ONE PlatformSpec entry here + one entry in the frontend registry.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PlatformSpec:
    """All configuration for a single social media platform."""

    key: str
    display_name: str

    # Content generation
    content_prompt: str
    review_guidelines: str
    hashtag_limit: int
    caption_max: int

    # Post-generation enforcement
    hard_char_limit: int | None = None
    fold_at: int | None = None

    # Image generation
    image_aspect: str = "1:1"

    # Video
    is_portrait_video: bool = False

    # Derivative types this platform supports
    derivative_types: list[str] = field(default_factory=lambda: ["original"])


# ── Content prompts (named constants for readability) ─────────────────────────

_INSTAGRAM_PROMPT = (
    "PLATFORM FORMAT: Instagram post.\n"
    "- Hook in first line (≤125 chars — appears above 'more' fold, make it count)\n"
    "- 2-3 short paragraphs with line breaks for readability\n"
    "- Total caption: 150-250 words. Be concise — don't over-explain\n"
    "- Include 2-3 searchable keywords naturally in caption (Instagram SEO is keyword-based now)\n"
    "- CTA that drives saves and DM shares (top algorithm signals in 2026)\n"
    "- Emoji use: moderate, on-brand\n"
    "- Carousels are the #1 engagement format — use slide-by-slide structure when possible\n"
    "- For Reels: keep caption ultra-short (50-100 chars), video does the talking\n"
    "HASHTAGS: 3-5 highly targeted hashtags (quality over quantity — Instagram penalizes hashtag stuffing)"
)

_LINKEDIN_PROMPT = (
    "PLATFORM FORMAT: LinkedIn post.\n"
    "- Strong opening hook — first 140 chars appear above \"see more\", make them count\n"
    "- Professional but PERSONAL — LinkedIn rewards vulnerability and first-person stories\n"
    "- 3-5 short paragraphs with generous line breaks (dwell time = reach)\n"
    "- Total length: 150-300 words\n"
    "- End with a specific question or CTA to drive comments\n"
    "- Emoji: 1-2 per post max, never decorative\n"
    "- Document/carousel format for frameworks, checklists, step-by-step guides\n"
    "- NEVER include external links in the post body — LinkedIn massively deprioritizes\n"
    "  posts with URLs (put links in comments instead if needed)\n"
    "HASHTAGS: 3-5 maximum (LinkedIn penalizes over-hashtagging)"
)

_X_PROMPT = (
    "PLATFORM FORMAT: X (Twitter) post.\n"
    "- Concise, punchy, conversational — one clear idea per post\n"
    "- Designed to spark quick replies (replies = #1 algorithm signal)\n"
    "- Aim for 100-200 characters for maximum engagement\n"
    "- 80% value content (educational/entertaining), 20% promotional\n"
    "- Video-companion captions should create curiosity about the visual\n"
    "- For threads: number each post (1/, 2/, etc.) — each must stand alone\n"
    "- Quote-post and reply-to-trending formats drive the most growth\n"
    "HASHTAGS: 0-1 maximum — woven into text naturally (X discovery is algorithmic now, not hashtag-based)\n"
    "Hard limit: 280 characters per post (Premium accounts can go longer but keep it tight)"
)

_TIKTOK_PROMPT = (
    "PLATFORM FORMAT: TikTok caption.\n"
    "- Ultra-casual, trend-aware voice\n"
    "- Hook immediately — first 3 words matter most\n"
    "- For VIDEO posts: 50-150 characters (visual does the talking)\n"
    "- For CAROUSEL/PHOTO posts: 200-500 characters with searchable keywords\n"
    "  (TikTok is a search engine now — people search TikTok like Google)\n"
    "- Include relevant keywords naturally — think 'what would someone search to find this?'\n"
    "- Problem-solution format performs best\n"
    "- Behind-the-scenes / authentic > polished. 'Edutainment' (educational + entertaining) wins\n"
    "- CTA: 'Follow for more' or 'Save this for later'\n"
    "HASHTAGS: 4-6 mix of niche hashtags and trending tags"
)

_FACEBOOK_PROMPT = (
    "PLATFORM FORMAT: Facebook post.\n"
    "- Conversational, community-oriented tone\n"
    "- Ask questions to drive comments — the algorithm rewards meaningful interactions\n"
    "- Storytelling works well — 100-250 words\n"
    "- Shares and saves are the most valuable engagement signals\n"
    "- Carousel posts increase dwell time — use for educational/storytelling content\n"
    "- NEVER include external links in the post body — Facebook heavily deprioritizes link posts\n"
    "  (share links in comments if needed)\n"
    "- Emoji use: moderate\n"
    "- Content must be shareable beyond followers (Facebook's 'Suggested for you' feed is primary discovery)\n"
    "HASHTAGS: 0-3 (optional — Facebook engagement doesn't depend on hashtags)"
)

_THREADS_PROMPT = (
    "PLATFORM FORMAT: Threads post.\n"
    "- Conversation-first — write to spark replies, not broadcast\n"
    "- Authentic, genuine voice — the algorithm suppresses promotional content\n"
    "- Strong opening line that stops the scroll (this is your headline)\n"
    "- 200-300 characters is the sweet spot (500 char limit)\n"
    "- Image posts get 60% more engagement than text-only\n"
    "- End with a question or hot take to drive discussion\n"
    "- Use 1-3 topic tags where relevant (Threads now supports topic-based discovery)\n"
    "HASHTAGS: 0-3 topic tags where relevant for discovery"
)

_PINTEREST_PROMPT = (
    "PLATFORM FORMAT: Pinterest pin.\n"
    "- Write as TWO clearly labeled parts:\n"
    "  PIN TITLE: ≤100 chars, keyword-rich, compelling (this is the search headline)\n"
    "  PIN DESCRIPTION: 200-250 chars, SEO-optimized with natural keywords\n"
    "- Pinterest is a SEARCH ENGINE — every word matters for discovery\n"
    "  Include: primary keyword in title, secondary keywords in description, action verbs\n"
    "- How-to content is the #1 engagement driver\n"
    "- Include actionable value: 'How to...', '5 ways to...', 'The best...'\n"
    "- No emoji — clean, professional, search-friendly\n"
    "- Multi-image pins get 4x engagement of standard pins\n"
    "- Think: 'What would someone search to find this?'\n"
    "HASHTAGS: 0 — use keywords instead (Pinterest doesn't rely on hashtags)"
)

_YOUTUBE_SHORTS_PROMPT = (
    "PLATFORM FORMAT: YouTube Shorts description.\n"
    "- Hook in first line — first 125 chars appear in preview and search\n"
    "- Punchy teaser that makes viewers want to watch the video\n"
    "- Keep total under 200 chars — the video does the talking\n"
    "- Include 2-3 searchable keywords naturally (Shorts have evergreen discovery via YouTube Search)\n"
    "- YouTube auto-detects Shorts by video length — do NOT add #Shorts as a hashtag (unnecessary)\n"
    "- CTA: 'Subscribe for more' or 'Watch the full video' (link to long-form content when available)\n"
    "HASHTAGS: 3-5 relevant keyword-based tags for search discovery"
)

_MASTODON_PROMPT = (
    "PLATFORM FORMAT: Mastodon post.\n"
    "- Community-first — genuine, useful, respectful of instance norms\n"
    "- No algorithm — hashtags ARE the discovery mechanism (essential)\n"
    "- 200-400 characters, well-considered (500 char limit)\n"
    "- Provide practical value — earn boosts by being genuinely useful\n"
    "- Use CamelCase hashtags for accessibility (screen readers parse CamelCase)\n"
    "- Anti-spam culture: no aggressive promotion, no engagement bait, no 'like and share'\n"
    "- Content warnings (CW): use them for potentially sensitive topics — this is a cultural expectation\n"
    "- Image descriptions (alt text) are expected, not optional — describe images for accessibility\n"
    "HASHTAGS: 3-5 CamelCase hashtags woven into text (these are critical for discovery)"
)

_BLUESKY_PROMPT = (
    "PLATFORM FORMAT: Bluesky post.\n"
    "- Concise, conversational, genuine — authentic voice wins\n"
    "- One clear thought per post — no fluff\n"
    "- 150-250 characters optimal (300 char hard limit)\n"
    "- Designed to spark replies — replies are the #1 engagement signal\n"
    "- Ask specific questions ('What's your take on X?') not generic hooks\n"
    "- Thread format for deeper content (reply to your own post)\n"
    "- Content that fits into custom feeds (niche topic feeds) gets 5x impressions\n"
    "  — write about specific topics, not generic platitudes\n"
    "HASHTAGS: 1-3 relevant hashtags for discovery (Bluesky now supports hashtags)"
)


# ── Registry ──────────────────────────────────────────────────────────────────

REGISTRY: dict[str, PlatformSpec] = {
    "instagram": PlatformSpec(
        key="instagram",
        display_name="Instagram",
        content_prompt=_INSTAGRAM_PROMPT,
        review_guidelines=(
            "hook ≤125 chars above fold, 150-250 words, 3-5 targeted hashtags, "
            "SEO keywords in caption, saves/shares-optimized CTA, no external links"
        ),
        hashtag_limit=5,
        caption_max=2200,
        fold_at=125,
        image_aspect="1:1",
        is_portrait_video=True,
        derivative_types=["original", "carousel", "story", "video_first"],
    ),
    "linkedin": PlatformSpec(
        key="linkedin",
        display_name="LinkedIn",
        content_prompt=_LINKEDIN_PROMPT,
        review_guidelines=(
            "hook ≤140 chars above 'see more', 150-300 words, 3-5 hashtags, "
            "personal narrative tone, NO external links in body, dwell-time optimized"
        ),
        hashtag_limit=5,
        caption_max=3000,
        fold_at=140,
        image_aspect="1.91:1",
        derivative_types=["original", "carousel", "blog_snippet", "video_first"],
    ),
    "x": PlatformSpec(
        key="x",
        display_name="X",
        content_prompt=_X_PROMPT,
        review_guidelines=(
            "≤280 chars hard limit, aim 100-200 chars, 0-1 hashtags woven in text, "
            "reply-sparking, no hashtag blocks"
        ),
        hashtag_limit=1,
        caption_max=280,
        hard_char_limit=280,
        image_aspect="16:9",
        derivative_types=["original", "thread_hook", "video_first"],
    ),
    "tiktok": PlatformSpec(
        key="tiktok",
        display_name="TikTok",
        content_prompt=_TIKTOK_PROMPT,
        review_guidelines=(
            "video: 50-150 chars, carousel: 200-500 chars with SEO keywords, "
            "4-6 hashtags, hook in first 3 words, edutainment tone"
        ),
        hashtag_limit=6,
        caption_max=2200,
        image_aspect="9:16",
        is_portrait_video=True,
        derivative_types=["original", "carousel", "video_first"],
    ),
    "facebook": PlatformSpec(
        key="facebook",
        display_name="Facebook",
        content_prompt=_FACEBOOK_PROMPT,
        review_guidelines=(
            "100-250 words, 0-3 hashtags, question-based CTA, "
            "NO external links in body, shareable beyond followers"
        ),
        hashtag_limit=3,
        caption_max=63206,
        image_aspect="1.91:1",
        derivative_types=["original", "carousel", "story", "video_first"],
    ),
    "threads": PlatformSpec(
        key="threads",
        display_name="Threads",
        content_prompt=_THREADS_PROMPT,
        review_guidelines=(
            "≤500 chars, 200-300 optimal, 0-3 topic tags, "
            "conversation-starter format, anti-promotional"
        ),
        hashtag_limit=3,
        caption_max=500,
        hard_char_limit=500,
        image_aspect="1:1",
        is_portrait_video=True,
        derivative_types=["original", "video_first"],
    ),
    "pinterest": PlatformSpec(
        key="pinterest",
        display_name="Pinterest",
        content_prompt=_PINTEREST_PROMPT,
        review_guidelines=(
            "PIN TITLE ≤100 chars + PIN DESCRIPTION 200-250 chars, "
            "0 hashtags, SEO keywords in both title and description"
        ),
        hashtag_limit=0,
        caption_max=500,
        image_aspect="2:3",
        is_portrait_video=True,
        derivative_types=["original", "pin", "video_first"],
    ),
    "youtube_shorts": PlatformSpec(
        key="youtube_shorts",
        display_name="YouTube Shorts",
        content_prompt=_YOUTUBE_SHORTS_PROMPT,
        review_guidelines=(
            "≤200 chars, 3-5 keyword hashtags (NO #Shorts), "
            "hook in first 125 chars, searchable keywords"
        ),
        hashtag_limit=5,
        caption_max=5000,
        image_aspect="9:16",
        is_portrait_video=True,
        derivative_types=["original", "video_first"],
    ),
    "mastodon": PlatformSpec(
        key="mastodon",
        display_name="Mastodon",
        content_prompt=_MASTODON_PROMPT,
        review_guidelines=(
            "≤500 chars, 3-5 CamelCase hashtags, community-appropriate tone, "
            "no engagement bait, CW for sensitive topics"
        ),
        hashtag_limit=5,
        caption_max=500,
        hard_char_limit=500,
        image_aspect="16:9",
        derivative_types=["original", "video_first"],
    ),
    "bluesky": PlatformSpec(
        key="bluesky",
        display_name="Bluesky",
        content_prompt=_BLUESKY_PROMPT,
        review_guidelines=(
            "≤300 chars hard limit, 1-3 hashtags, reply-sparking format, "
            "custom-feed optimized, specific topics not platitudes"
        ),
        hashtag_limit=3,
        caption_max=300,
        hard_char_limit=300,
        image_aspect="16:9",
        derivative_types=["original", "thread_hook", "video_first"],
    ),
}


# ── Alias handling ────────────────────────────────────────────────────────────

_ALIASES: dict[str, str] = {"twitter": "x"}


# ── Public helpers ────────────────────────────────────────────────────────────

def get(key: str) -> PlatformSpec:
    """Return the PlatformSpec for the given key, handling aliases.

    Falls back to Instagram if the key is unknown.
    """
    normalized = _ALIASES.get(key.lower(), key.lower())
    return REGISTRY.get(normalized, REGISTRY["instagram"])


def keys() -> list[str]:
    """Return all canonical platform keys."""
    return list(REGISTRY.keys())


def get_review_guidelines_block() -> str:
    """Build the full platform-specific review guidelines block for the review agent."""
    lines = ["Platform-specific guidelines to check:"]
    for spec in REGISTRY.values():
        lines.append(f"- {spec.display_name}: {spec.review_guidelines}")
    return "\n".join(lines)
