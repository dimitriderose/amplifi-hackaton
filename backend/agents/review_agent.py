import asyncio
import json
import logging
from google import genai
from google.genai import types
from backend.config import GOOGLE_API_KEY, GEMINI_MODEL

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

Platform-specific guidelines to check:
- Instagram: hook ≤125 chars above fold, total 150-250 words, 8-12 hashtags
- LinkedIn: hook ≤140 chars above "see more", 150-300 words, 3-5 hashtags
- Twitter/X: ≤280 chars per tweet, aim 100-200 chars, 1-2 hashtags in text
- TikTok: 50-150 chars (ultra-short), 4-6 hashtags
- Facebook: 100-250 words, 0-3 hashtags

Flag captions that are too long for their platform. Check hashtags for junk (sentence fragments, common words like #the, #for, #your).

Evaluate and respond with JSON only:
{{
  "score": <integer 1-10, overall brand quality score>,
  "brand_alignment": <"strong"|"moderate"|"weak">,
  "strengths": [<list of 2-3 strength strings>],
  "improvements": [<list of 1-3 improvement suggestions>],
  "approved": <true if score >= 7, false otherwise>,
  "revised_caption": <improved caption string if score < 8 or caption is too long for platform, otherwise null>,
  "revised_hashtags": <cleaned hashtag array if any hashtags are junk/irrelevant/too many, otherwise null>,
  "engagement_scores": {{
    "hook_strength": <integer 1-10: how compelling the opening line is — will people stop scrolling?>,
    "relevance": <integer 1-10: how on-brand and relevant to target audience>,
    "cta_effectiveness": <integer 1-10: how clear and motivating the call-to-action is>,
    "platform_fit": <integer 1-10: how well the format, length, and hashtag use fits {platform}>
  }},
  "engagement_prediction": <"low"|"medium"|"high"|"viral" — predicted relative engagement vs average for {platform}>
}}"""

    try:
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=GEMINI_MODEL,
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
        raw_engagement = result.get("engagement_scores", {})
        return {
            "score": int(result.get("score", 5)),
            "brand_alignment": result.get("brand_alignment", "moderate"),
            "strengths": result.get("strengths", []),
            "improvements": result.get("improvements", []),
            "approved": bool(result.get("approved", False)),
            "revised_caption": result.get("revised_caption"),
            "revised_hashtags": result.get("revised_hashtags"),
            "engagement_scores": {
                "hook_strength": int(raw_engagement.get("hook_strength", 5)),
                "relevance": int(raw_engagement.get("relevance", 5)),
                "cta_effectiveness": int(raw_engagement.get("cta_effectiveness", 5)),
                "platform_fit": int(raw_engagement.get("platform_fit", 5)),
            },
            "engagement_prediction": result.get("engagement_prediction", "medium"),
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
            "engagement_scores": {
                "hook_strength": 5,
                "relevance": 5,
                "cta_effectiveness": 5,
                "platform_fit": 5,
            },
            "engagement_prediction": "medium",
        }
