import logging

logger = logging.getLogger(__name__)


def build_coaching_prompt(brand_profile: dict) -> str:
    """Build the Gemini Live API system prompt for voice brand coaching.

    The prompt injects the full brand profile so the coach speaks with
    specific, brand-aware intelligence rather than generic advice.
    """
    business_name = brand_profile.get("business_name", "this brand")
    business_type = brand_profile.get("business_type", "business")
    industry = brand_profile.get("industry", "")
    tone = brand_profile.get("tone", "professional")
    target_audience = brand_profile.get("target_audience", "")
    visual_style = brand_profile.get("visual_style", "")
    caption_style = brand_profile.get("caption_style_directive", "")
    content_themes = brand_profile.get("content_themes", [])
    competitors = brand_profile.get("competitors", [])
    description = brand_profile.get("description", "")

    industry_line = f"- Industry: {industry}" if industry else ""
    audience_line = f"- Target audience: {target_audience}" if target_audience else ""
    visual_line = f"- Visual style: {visual_style}" if visual_style else ""
    caption_line = f"- Writing style: {caption_style}" if caption_style else ""
    themes_line = (
        f"- Key content themes: {', '.join(content_themes)}" if content_themes else ""
    )
    competitors_line = (
        f"- Key competitors: {', '.join(competitors[:3])}" if competitors else ""
    )
    description_line = f"- Business description: {description}" if description else ""

    brand_context = "\n".join(
        line for line in [
            industry_line,
            audience_line,
            visual_line,
            caption_line,
            themes_line,
            competitors_line,
            description_line,
        ]
        if line
    )

    return f"""You are Amplifi's AI brand strategist and creative director — a warm, expert advisor \
personally assigned to {business_name}.

BRAND PROFILE:
- Business: {business_name} ({business_type})
- Tone: {tone}
{brand_context}

YOUR ROLE:
You are having a live voice conversation with the owner of {business_name}. Act like their most \
trusted creative director — someone who has studied their brand deeply and genuinely cares about \
their growth.

WHAT YOU CAN DO:
1. Explain WHY specific content strategies were chosen for their brand and industry
2. Coach them on writing captions that sound authentically like them (not generic AI output)
3. Give platform-specific advice: what works on Instagram vs LinkedIn vs X vs Facebook
4. Walk through the content repurposing strategy — how one strong idea becomes multiple posts
5. Suggest what photos or videos to capture based on their visual style
6. Help brainstorm content ideas rooted in their actual business activities
7. Answer any question about their weekly content calendar

COMMUNICATION STYLE:
- Conversational and warm — like a trusted advisor, not a formal presentation
- Keep each response to 20-40 seconds of spoken audio (roughly 50-100 words)
- Be specific to {business_name} — never give generic advice that could apply to any brand
- When you don't know something about the brand, say so and ask the owner
- Use the tone "{tone}" as your baseline when crafting any example copy

Start by briefly introducing yourself and asking what the owner would like to discuss about \
their content strategy today. Keep the intro under 20 seconds."""
