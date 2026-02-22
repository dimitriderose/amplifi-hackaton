import json
import logging
from google import genai
from google.genai import types
from backend.tools.web_scraper import fetch_website
from backend.tools.brand_tools import analyze_brand_colors, extract_brand_voice

logger = logging.getLogger(__name__)


async def run_brand_analysis(
    description: str,
    website_url: str | None = None,
    uploaded_assets: list[str] | None = None,
) -> dict:
    """Run the Brand Analyst agent to build a complete brand profile.

    Args:
        description: Free-text business description (min 20 chars, required)
        website_url: Optional website URL to scrape
        uploaded_assets: Optional list of GCS URIs for uploaded brand assets

    Returns: Complete brand profile dict
    """
    client = genai.Client()

    # Step 1: Gather website data if URL provided
    website_data = {}
    if website_url:
        logger.info(f"Fetching website: {website_url}")
        website_data = await fetch_website(website_url)
        color_analysis = analyze_brand_colors(website_data.get("colors_found", []))
        voice_analysis = extract_brand_voice(website_data.get("text_content", ""))
    else:
        color_analysis = {}
        voice_analysis = {}

    # Step 2: Build analysis prompt
    website_context = ""
    if website_data and not website_data.get("error"):
        website_context = f"""
WEBSITE DATA:
- Title: {website_data.get('title', 'N/A')}
- Description: {website_data.get('description', 'N/A')}
- Text content (first 3000 chars): {website_data.get('text_content', '')[:3000]}
- Colors found on site: {', '.join(website_data.get('colors_found', [])[:10])}
- Navigation items: {', '.join(website_data.get('nav_items', [])[:10])}
- Pre-analyzed colors: Primary={color_analysis.get('primary', 'N/A')}, Secondary={color_analysis.get('secondary', 'N/A')}
- Detected brand voice signals: {', '.join(voice_analysis.get('detected_tones', []))}
"""

    prompt = f"""You are a brand strategist analyzing a business to build a comprehensive brand profile for social media content creation.

BUSINESS DESCRIPTION: {description}
{website_context}

Infer the business type and tailor your analysis:
- local_business: local/physical businesses (restaurants, salons, gyms, shops)
- service: consulting, coaching, agencies, professional services
- personal_brand: solopreneurs, creators, influencers, coaches with personal name brands
- ecommerce: online stores, DTC brands, product-focused businesses

Analyze the provided information and extract:

1. BUSINESS_NAME: The brand/business name (infer from description if needed)
2. BUSINESS_TYPE: One of: local_business, service, personal_brand, ecommerce
3. INDUSTRY: The industry category (e.g., "Food & Beverage", "Fitness & Wellness", "B2B Software")
4. TONE: 3-5 comma-separated adjectives describing brand voice (e.g., "warm, approachable, artisanal")
5. COLORS: Array of 3 hex colors [primary, secondary, accent] that represent the brand
6. TARGET_AUDIENCE: One sentence describing demographics and psychographics
7. VISUAL_STYLE: One sentence describing photography/visual aesthetic style
8. CONTENT_THEMES: Array of 5-8 content topics this brand should post about
9. COMPETITORS: Array of 2-3 competitor names or domains
10. IMAGE_STYLE_DIRECTIVE: A 2-3 sentence visual identity fragment. Be EXTREMELY specific about colors, lighting, composition, textures. This will be prepended to every image generation prompt.
    BAD: "professional and clean"
    GOOD: "warm earth tones with terracotta and sage green accents, soft natural lighting with golden hour warmth, minimalist compositions with generous whitespace, organic textures like linen and raw wood, shot from slightly above at 30-degree angle"
11. CAPTION_STYLE_DIRECTIVE: A 2-4 sentence writing rhythm guide. Describe structural patterns, not just adjectives.
    BAD: "professional and friendly"
    GOOD: "Open with a one-sentence hook under 10 words. Second beat is a personal anecdote or concrete example. Third beat delivers the counterintuitive insight or actionable takeaway. Close with a direct question to drive comments. Use em dashes liberally. Never use exclamation marks."

Return ONLY a valid JSON object with these exact keys:
{{
  "business_name": "string",
  "business_type": "local_business|service|personal_brand|ecommerce",
  "industry": "string",
  "tone": "string (comma-separated adjectives)",
  "colors": ["#hex1", "#hex2", "#hex3"],
  "target_audience": "string",
  "visual_style": "string",
  "content_themes": ["theme1", "theme2", ...],
  "competitors": ["competitor1", "competitor2"],
  "image_style_directive": "string",
  "caption_style_directive": "string"
}}
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.4,
                response_mime_type="application/json",
            ),
        )

        raw = response.text.strip()
        # Strip markdown code blocks if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        profile = json.loads(raw)

    except Exception as e:
        logger.error(f"Brand analysis failed: {e}")
        # Fallback: return minimal profile from description
        profile = _fallback_profile(description, website_url)

    return profile


def _fallback_profile(description: str, website_url: str | None) -> dict:
    """Minimal fallback brand profile when AI analysis fails."""
    words = description.split()
    business_name = " ".join(words[:3]).title() if len(words) >= 3 else description[:30].title()
    return {
        "business_name": business_name,
        "business_type": "general",
        "industry": "General Business",
        "tone": "professional, approachable, authentic",
        "colors": ["#5B5FF6", "#8B5CF6", "#FF6B6B"],
        "target_audience": "Adults 25-45 interested in this type of business",
        "visual_style": "clean, modern, professional aesthetic",
        "content_themes": ["behind the scenes", "tips and advice", "product highlights", "customer stories", "team culture"],
        "competitors": [],
        "image_style_directive": "clean, modern aesthetic with consistent brand colors, professional lighting, crisp compositions with generous whitespace",
        "caption_style_directive": "Open with a compelling hook. Share a relevant insight or story. End with a clear call to action or question to drive engagement.",
    }
