# Technical Design Document
## Amplifi

**Category:** ✍️ Creative Storyteller
**Author:** Software Architecture Team
**Companion Document:** PRD — Amplifi v1.0
**Version:** 1.1 | February 23, 2026 (updated from v1.0 Feb 21)

---

# 1. Overview

This Technical Design Document specifies the implementation architecture for Amplifi, an AI-powered creative director that produces complete social media content packages using Gemini's interleaved text and image output. It translates the PRD's product requirements into concrete engineering decisions, API contracts, data models, code structure, and deployment specifications.

**Scope:** All P0 (Must Have) features from the PRD: brand analysis from URL, content calendar generation, interleaved post generation, brand consistency review, React dashboard, image storage, and streaming UI.

**Out of scope (unspecified):** Voice brand coaching (P3), post analytics dashboard (P3). All P2 features are now specified in §12.1, including video repurposing (§12.1.12). P3 features are additive and do not affect core architecture.

---

# 2. System Architecture

## 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                       USER BROWSER                              │
│                                                                 │
│   ┌───────────────────────────────────────────────────────────┐ │
│   │                    React Dashboard                        │ │
│   │                                                           │ │
│   │  ┌──────────┐  ┌────────────┐  ┌──────────────────────┐  │ │
│   │  │  Brand    │  │  Content   │  │   Post Generator     │  │ │
│   │  │  Wizard   │  │  Calendar  │  │   (SSE streaming)    │  │ │
│   │  │          │  │            │  │                      │  │ │
│   │  │ URL input │  │ 7-day grid │  │ Caption ──────────── │  │ │
│   │  │ Upload    │  │ Themes     │  │ Image ░░░░░░░░░░░░░ │  │ │
│   │  │ Describe  │  │ Platforms  │  │ Hashtags ──────────  │  │ │
│   │  └──────────┘  └────────────┘  └──────────────────────┘  │ │
│   └────────────────────────┬──────────────────────────────────┘ │
│                            │ REST + SSE                         │
└────────────────────────────┼────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    CLOUD RUN (us-central1)                       │
│                    Container: amplifi-backend                    │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                 FastAPI Application Server                 │  │
│  │                                                           │  │
│  │  POST   /api/brands           → Create brand profile      │  │
│  │  GET    /api/brands/{id}      → Get brand profile         │  │
│  │  PUT    /api/brands/{id}      → Update brand profile      │  │
│  │  POST   /api/brands/{id}/analyze  → Trigger brand analysis│  │
│  │  POST   /api/plans            → Generate content calendar │  │
│  │  GET    /api/plans/{id}       → Get plan details          │  │
│  │  GET    /api/generate/{planId}/{day} → SSE: generate post │  │
│  │  POST   /api/review/{postId}  → Review single post        │  │
│  │  GET    /api/posts/{brandId}  → List generated posts      │  │
│  │  GET    /health               → Health check              │  │
│  └──────────────┬────────────────────────────────────────────┘  │
│                 │                                                │
│  ┌──────────────▼────────────────────────────────────────────┐  │
│  │           ADK SequentialAgent Pipeline                     │  │
│  │                                                           │  │
│  │   Step 1          Step 2          Step 3         Step 4   │  │
│  │  ┌──────────┐   ┌──────────┐   ┌──────────┐  ┌────────┐ │  │
│  │  │  Brand   │──▶│ Strategy │──▶│ Content  │─▶│ Review │ │  │
│  │  │ Analyst  │   │  Agent   │   │ Creator  │  │ Agent  │ │  │
│  │  │          │   │          │   │ ⭐        │  │        │ │  │
│  │  │ gemini-  │   │ gemini-  │   │ gemini-  │  │gemini- │ │  │
│  │  │ 2.5-flash│   │ 2.5-flash│   │ 2.5-flash│  │2.5-    │ │  │
│  │  │ (text)   │   │ (text)   │   │ TEXT+IMG │  │flash   │ │  │
│  │  └──────────┘   └──────────┘   └──────────┘  └────────┘ │  │
│  └──────────────┬────────────────────────────────────────────┘  │
│                 │                                                │
│  ┌──────────────▼────────────────────────────────────────────┐  │
│  │         Gemini API (generateContent)                       │  │
│  │         Model: gemini-2.5-flash                            │  │
│  │         responseModalities: ["TEXT", "IMAGE"]               │  │
│  └───────────────────────────────────────────────────────────┘  │
└──────────────┬──────────────────────────────┬───────────────────┘
               │                              │
               ▼                              ▼
┌──────────────────────────┐  ┌──────────────────────────────────┐
│    Cloud Firestore       │  │       Cloud Storage               │
│    (us-east1)            │  │       (us-east1)                  │
│                          │  │                                   │
│  brands/{brandId}/       │  │  gs://amplifi-assets-2026/        │
│    business_name, tone,  │  │    brands/{brandId}/              │
│    colors, audience      │  │      logo.png                    │
│    content_plans/        │  │      product_photos/              │
│      {planId}/days/      │  │    generated/{postId}/            │
│        {day}/            │  │      image.png                   │
│          caption, image  │  │                                   │
└──────────────────────────┘  └──────────────────────────────────┘
```

## 2.2 Key Architectural Decisions

**Decision 1: REST + SSE (Not WebSocket)**
Unlike Fireside which requires bidirectional real-time communication, Amplifi uses standard REST APIs for all CRUD operations and Server-Sent Events (SSE) for the content generation stream. The frontend opens an SSE connection to `/api/generate/{planId}/{day}` and receives interleaved text and image data as the model produces it.

Rationale: Interleaved output uses the standard `generateContent` API (not Live API). SSE is the natural fit for a unidirectional server-to-client stream. It's simpler than WebSocket, doesn't require session affinity on Cloud Run, and works through CDNs and proxies.

**Decision 2: Per-Day Content Generation (Not Batch)**
The Content Creator Agent is invoked once per calendar day, producing one post per API call. A 7-day calendar requires 7 sequential calls.

Rationale: Each interleaved output call generates text + image in one response. Generating all 7 posts in one call would make the response too large and the UI would have to wait for the entire response before showing anything. Per-day calls allow progressive display: Day 1 streams in, then Day 2, etc.

**Decision 3: Image Storage in Cloud Storage with Signed URLs**
Generated images are extracted from the Gemini response, uploaded to Cloud Storage, and served to the frontend via time-limited signed URLs. The image URL (not the base64 data) is stored in Firestore.

Rationale: Base64 images in Firestore would quickly exceed document size limits (1 MiB). Cloud Storage is purpose-built for binary objects. Signed URLs provide security without requiring authentication on the frontend.

**Decision 4: Review Agent Runs Independently**
The Review Agent is a separate LLM call that receives the generated post content + the brand profile and produces a structured review. It does NOT modify the generated content; it only flags issues and provides suggestions.

Rationale: Keeping generation and review separate allows the user to accept "flagged" posts anyway. It also avoids circular loops where the reviewer rewrites content that then needs re-reviewing.

---

# 3. Agent Specifications

## 3.1 Pipeline Architecture (ADK SequentialAgent)

```python
from google.adk.agents import Agent, SequentialAgent

# The full pipeline as an ADK SequentialAgent
amplifi_pipeline = SequentialAgent(
    name="amplifi_pipeline",
    description="Brand analysis → strategy → content creation → review",
    sub_agents=[brand_analyst, strategy_agent, content_creator, review_agent],
)
```

Note: For MVP, the pipeline is invoked step-by-step through REST endpoints rather than as a single SequentialAgent run. This gives the user control between steps (edit brand profile, rearrange calendar). The SequentialAgent definition exists for completeness and could be used for a "one-click generate everything" flow.

## 3.2 Brand Analyst Agent

```python
brand_analyst = Agent(
    name="brand_analyst",
    model="gemini-2.5-flash",
    description="Analyzes a brand from its website and assets to build a brand profile",
    instruction="""You are a brand strategist analyzing a business to build a 
    comprehensive brand profile.
    
    BUSINESS DESCRIPTION: {business_description}
    
    Infer the business type and tailor your analysis accordingly:
    - Local/physical businesses: Emphasize product photography direction, local community 
      engagement, seasonal promotions, foot traffic drivers.
    - Service/consulting businesses: Emphasize expertise signaling, trust markers, thought 
      leadership topics, client outcome language.
    - Personal brands/creators: Emphasize personal voice authenticity, opinion-driven content 
      themes, storytelling angles, audience relationship building.
    - E-commerce/DTC: Emphasize product features, seasonal campaigns, UGC-style aesthetics,
      conversion-oriented content themes.
    
    Given a website URL (if provided), free-text business description, and/or uploaded brand 
    assets (images and PDFs like brand guides or menus), extract:
    1. BRAND COLORS: Primary, secondary, and accent colors (hex values)
    2. TONE OF VOICE: 3-5 adjectives describing the brand's communication style
    3. TARGET AUDIENCE: Demographics, psychographics, and interests
    4. INDUSTRY & POSITIONING: What category they're in and how they differentiate
    5. CONTENT THEMES: 5-8 recurring topics the brand should post about
       (weighted by business_type — personal brands get thought leadership topics,
        local businesses get community/product topics)
    6. VISUAL STYLE: Photography style, illustration preferences, overall aesthetic
    7. COMPETITORS: 2-3 direct competitors if identifiable
    8. IMAGE STYLE DIRECTIVE (P1): A 2-3 sentence visual identity fragment that will be
       prepended to EVERY image generation prompt for this brand. Be extremely specific.
       Bad: "professional and clean"
       Good: "warm earth tones with terracotta and sage green accents, soft natural 
       lighting with golden hour warmth, minimalist compositions with generous whitespace, 
       organic textures like linen and raw wood, shot from slightly above at 30-degree angle"
       This directive is the brand's visual DNA — it ensures every AI-generated image
       feels like it belongs to the same feed even when generated in separate API calls.
    9. CAPTION STYLE DIRECTIVE (P1): A 2-4 sentence writing rhythm guide that will be
       prepended to EVERY caption generation prompt for this brand. Describe the structural
       pattern of the brand's writing, not just adjectives about tone.
       Bad: "professional and friendly"
       Good: "Open with a one-sentence hook under 10 words. Second beat is a personal 
       anecdote or concrete example. Third beat delivers the counterintuitive insight or 
       actionable takeaway. Close with a direct question to drive comments. Use em dashes 
       liberally. Never use exclamation marks. Keep paragraphs to 1-2 sentences max."
       This directive is the brand's textual DNA — it ensures every caption sounds like 
       the same person wrote it, even across platforms and content types.
    
    OUTPUT FORMAT: Return a structured JSON object with these fields.
    Be specific and actionable. "Professional" is too vague — 
    "confident, authoritative, slightly playful" is useful.
    
    If the website is unavailable, work from the user's description and uploaded assets.
    """,
    tools=[fetch_website, analyze_brand_colors, extract_brand_voice, scan_competitors],
    output_key="brand_profile",
)
```

**Tool: `fetch_website`**
```python
import httpx
from bs4 import BeautifulSoup

async def fetch_website(url: str) -> dict:
    """Fetch and parse a website for brand analysis.
    
    Extracts: page title, meta description, visible text (first 5000 chars),
    CSS color values, image alt texts, navigation structure.
    
    Returns: {
        title: str, description: str, text_content: str,
        colors_found: list[str], images: list[str],
        nav_items: list[str]
    }
    """
    async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
        response = await client.get(url)
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Extract text content
    for tag in soup(['script', 'style', 'nav', 'footer']):
        tag.decompose()
    text = soup.get_text(separator=' ', strip=True)[:5000]
    
    # Extract colors from inline styles and stylesheets
    colors = extract_css_colors(response.text)
    
    # Extract images
    images = [img.get('alt', '') for img in soup.find_all('img') if img.get('alt')]
    
    return {
        "title": soup.title.string if soup.title else "",
        "description": soup.find('meta', {'name': 'description'}),
        "text_content": text,
        "colors_found": colors[:10],
        "images": images[:20],
        "nav_items": [a.text.strip() for a in soup.find_all('a') if a.text.strip()][:20],
    }
```

**Tool: `analyze_brand_colors`**
```python
def analyze_brand_colors(css_colors: list[str], logo_path: str | None = None) -> dict:
    """Analyze extracted colors to determine brand palette.
    
    Returns: { 
        primary: str (hex), secondary: str (hex), accent: str (hex),
        background: str (hex), text: str (hex)
    }
    """
    # Sort by frequency, filter out common neutral colors
    # Return top colors as primary/secondary/accent
    pass
```

## 3.3 Strategy Agent

```python
strategy_agent = Agent(
    name="strategy_agent",
    model="gemini-2.5-flash",
    description="Creates a 7-day content calendar from a brand profile using pillar-based repurposing",
    instruction="""You are a social media strategist creating a weekly content calendar.
    
    PILLAR-BASED STRATEGY (P1):
    Instead of 7 disconnected posts, identify 1-2 PILLAR ideas for the week — core themes
    or messages that can be repurposed across platforms. Then plan derivatives:
    
    Example for a coaching business with pillar "Pricing your services":
    - Monday: LinkedIn long-form post (deep dive, personal story)
    - Tuesday: X thread (same idea, condensed into 5 punchy tweets)  
    - Wednesday: Instagram carousel (visual tips, actionable steps)
    - Thursday: TikTok/Reel script (quick take, face-to-camera direction)
    - Friday: Instagram story poll ("How do you price your services?")
    - Saturday: LinkedIn comment/engagement post (follow-up to Monday)
    - Sunday: Rest or light content (behind-the-scenes, personal)
    
    Each day should include:
    1. PILLAR_ID: Which pillar this derives from (e.g., "pillar_1" or "standalone")
    2. PLATFORM: Which social platform (instagram, tiktok, linkedin, x)
    3. CONTENT THEME: What the post should be about
    4. DERIVATIVE_TYPE: How this relates to the pillar (original, condensed, visual, 
       conversational, engagement, standalone)
    5. CONTENT TYPE: photo, carousel, story, reel, thread
    6. POSTING TIME: Optimal time based on platform best practices
    7. CAPTION DIRECTION: Brief guidance for the caption tone/angle
    8. IMAGE DIRECTION: Brief guidance for the visual style
    9. PILLAR_CONTEXT: If a derivative, what was the original pillar's key message
       (so the Content Creator can maintain coherence across derivatives)
    
    CALENDAR PRINCIPLES:
    - Pillar derivatives should tell a coherent story across the week
    - Vary platforms throughout the week (not all Instagram)
    - Mix derivative types (not all text-heavy)
    - Space promotional content (max 2 direct sales posts per week)
    - Include engagement posts (questions, polls) alongside informational content
    - Consider day-of-week context (Monday motivation, Friday fun)
    - 1-2 standalone posts are fine for variety
    
    EVENT-AWARE PLANNING (P1):
    If BUSINESS_EVENTS_THIS_WEEK is provided, these are REAL events happening at the 
    business this week. They MUST be incorporated into the calendar:
    - A product launch, sale, or event should become a pillar with derivatives
    - Time-specific events should land on the correct day (e.g., "farmers market Saturday" 
      → Saturday's post is about the farmers market)
    - Events take priority over generic theme ideas — real is always better than invented
    - If no events are provided, generate thematic pillars as usual
    
    OUTPUT FORMAT: Return a JSON object with:
    - pillars: [{ id: string, theme: string, key_message: string, source: "event" | "generated" }]
    - days: [7 day objects with the fields above]
    
    BRAND PROFILE: {brand_profile}
    USER GOALS: {user_goals}
    BUSINESS_EVENTS_THIS_WEEK: {business_events or "None provided — generate thematic pillars."}
    """,
    tools=[generate_calendar, research_trending_hashtags],
    output_key="content_calendar",
)
```

## 3.4 Content Creator Agent ⭐ (Interleaved Output)

This is the star of the submission. It uses Gemini's interleaved output to generate caption text and matching product images in a single API call. When a user uploads their own photo (P1 BYOP mode), the agent switches to image-understanding mode — analyzing the photo and generating captions for it instead of generating an image.

```python
from google import genai
from google.genai import types

client = genai.Client()

async def generate_post(brand_profile: dict, day_brief: dict, 
                         user_photo_url: str | None = None) -> AsyncGenerator:
    """Generate a single post. Two modes:
    
    MODE A (no user photo): Interleaved text + image output. 
        Caption and image are born together. The "wow" demo moment.
    MODE B (user photo provided, P1): Text-only output with image understanding.
        AI analyzes the user's photo and writes a caption specifically for it.
    
    Yields SSE events as parts stream from the model.
    """
    
    # --- Build prompt based on mode ---
    base_context = f"""You are the creative director for {brand_profile['business_name']}.

BRAND VOICE: {brand_profile['tone']}
BRAND COLORS: {', '.join(brand_profile['colors'])}
TARGET AUDIENCE: {brand_profile['target_audience']}
VISUAL STYLE: {brand_profile.get('visual_style', 'clean, modern, professional')}
INDUSTRY: {brand_profile['industry']}
BUSINESS TYPE: {brand_profile.get('business_type', 'general')}

CAPTION STYLE DIRECTIVE (follow this writing rhythm for ALL captions):
{brand_profile.get('caption_style_directive', 'Write in a natural, engaging tone appropriate for the platform.')}

TODAY'S BRIEF:
- Platform: {day_brief['platform']}
- Theme: {day_brief['theme']}
- Content Type: {day_brief['content_type']}
- Caption Direction: {day_brief['caption_direction']}
"""

    if user_photo_url:
        # --- MODE B: BYOP — write captions FOR user's photo ---
        photo_bytes = await download_from_gcs(user_photo_url)
        
        prompt_parts = [
            types.Part.from_text(base_context + """
PHOTO PROVIDED: The user has uploaded their own photo for this post.
Analyze the photo carefully and generate content that complements it:

1. A compelling caption for {platform} that references specific visual elements in the photo
   (colors, composition, subjects, mood, setting — be specific, not generic)
2. 5-8 relevant hashtags (mix of popular and niche, tailored to what's IN the photo)
3. Recommended posting time

Do NOT describe the photo generically. Reference specific details you see.
The caption should make followers feel like they're seeing a curated, intentional post.
""".format(platform=day_brief['platform'])),
            types.Part.from_image(types.Image.from_bytes(
                data=photo_bytes, mime_type="image/jpeg"
            ))
        ]
        
        response_stream = client.models.generate_content_stream(
            model="gemini-2.5-flash",
            contents=prompt_parts,
            config=types.GenerateContentConfig(
                response_modalities=["TEXT"],  # Text-only — we already have the image
                temperature=0.8,
            )
        )
        
        async for chunk in response_stream:
            for part in chunk.candidates[0].content.parts:
                if part.text:
                    yield {"type": "text", "content": part.text}
        
        # Emit the user's own photo as the image event
        yield {"type": "image", "url": user_photo_url, "mime_type": "image/jpeg", 
               "source": "user_upload"}
    
    else:
        # --- MODE A: Interleaved output — generate caption + image together ---
        prompt = base_context + f"""
- Image Direction: {day_brief['image_direction']}

VISUAL IDENTITY DIRECTIVE (apply to ALL generated images for this brand):
{brand_profile.get('image_style_directive', 'clean, modern, professional aesthetic')}

GENERATE THE FOLLOWING IN ORDER:
1. A compelling caption for {day_brief['platform']} (appropriate length for platform)
2. A matching product/lifestyle image that fits the brand aesthetic
   - IMPORTANT: Follow the Visual Identity Directive above for color palette, 
     lighting, composition, and texture. Every image must feel like it belongs 
     to the same Instagram feed.
   - NO text overlays on the image
   - Style: {day_brief['image_direction']}
   - Resolution: High quality, suitable for social media
3. 5-8 relevant hashtags (mix of popular and niche)
4. Recommended posting time

Generate the caption and image TOGETHER as interleaved output.
The image should visually match the mood and message of the caption.
"""
        
        response_stream = client.models.generate_content_stream(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["TEXT", "IMAGE"],
                temperature=0.8,
            )
        )
        
        async for chunk in response_stream:
            for part in chunk.candidates[0].content.parts:
                if part.text:
                    yield {"type": "text", "content": part.text}
                elif part.inline_data:
                    image_url = await upload_image_to_gcs(
                        part.inline_data.data,
                        part.inline_data.mime_type
                    )
                    yield {"type": "image", "url": image_url, "mime_type": part.inline_data.mime_type}
```

**Critical Implementation Note:** The `generate_content_stream` method may not stream individual parts of interleaved output — it may buffer the entire response. If streaming is unavailable for interleaved mode, fall back to the non-streaming `generate_content` and simulate progressive display:

```python
async def generate_post_fallback(brand_profile: dict, day_brief: dict):
    """Non-streaming fallback if interleaved output doesn't support streaming."""
    
    response = await client.aio.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_modalities=["TEXT", "IMAGE"],
        )
    )
    
    results = []
    for part in response.candidates[0].content.parts:
        if part.text:
            results.append({"type": "text", "content": part.text})
        elif part.inline_data:
            image_url = await upload_image_to_gcs(
                part.inline_data.data,
                part.inline_data.mime_type
            )
            results.append({"type": "image", "url": image_url})
    
    return results
```

## 3.5 Review Agent

```python
review_agent = Agent(
    name="review_agent",
    model="gemini-2.5-flash",
    description="Reviews generated content against brand profile for consistency",
    instruction="""You are a brand consistency reviewer. Evaluate generated social 
    media content against the brand profile.
    
    CHECK THE FOLLOWING:
    1. TONE CONSISTENCY: Does the caption match the brand voice?
       Score: 1-5 (5 = perfect match)
    2. AUDIENCE FIT: Is the content appropriate for the target audience?
       Score: 1-5
    3. PLATFORM RULES: Does it meet platform requirements?
       - Instagram caption: < 2,200 chars
       - Twitter/X: < 280 chars
       - LinkedIn: < 3,000 chars
       - TikTok caption: < 2,200 chars
       - Hashtag count: 5-30 for Instagram, 3-5 for other platforms
    4. BRAND COLOR CONSISTENCY: Does the image appear to use brand colors?
       Score: 1-5
    5. OVERALL QUALITY: Is this content ready to post?
       Score: 1-5
    
    OUTPUT FORMAT: Return a JSON object:
    {
        "overall_score": number (1-5),
        "approved": boolean (true if all scores >= 3),
        "checks": {
            "tone": { "score": number, "feedback": string },
            "audience": { "score": number, "feedback": string },
            "platform": { "score": number, "feedback": string },
            "visual": { "score": number, "feedback": string },
            "quality": { "score": number, "feedback": string }
        },
        "suggestions": [string]  // Actionable improvement suggestions
    }
    
    BRAND PROFILE: {brand_profile}
    GENERATED CAPTION: {caption}
    GENERATED HASHTAGS: {hashtags}
    TARGET PLATFORM: {platform}
    """,
    tools=[check_brand_consistency, validate_hashtags, check_platform_rules],
    output_key="review_result",
)
```

---

# 4. API Specification

## 4.1 REST Endpoints

### Brand Management

```
POST /api/brands
Body: { website_url?: string, description: string, uploaded_assets?: string[] }
  // description: free-text business description (min 20 chars, required)
  // website_url: optional — omitted in no-website mode
  // uploaded_assets: optional array of Cloud Storage refs for brand assets (images, PDFs)
Response: { brand_id: string, status: "created" }

POST /api/brands/{brandId}/analyze
Body: { website_url?: string, description: string }
  // If website_url present: crawl site + analyze description + process uploads
  // If website_url absent (no-website mode): infer brand from description + uploads only
Response: { brand_profile: BrandProfile, status: "analyzed" }
  // Triggers Brand Analyst Agent

GET /api/brands/{brandId}
Response: { brand_profile: BrandProfile }

PUT /api/brands/{brandId}
Body: Partial<BrandProfile>  // User corrections
Response: { brand_profile: BrandProfile, status: "updated" }

POST /api/brands/{brandId}/upload
Body: multipart/form-data (images: jpg/png, documents: pdf — max 3 files)
Response: { uploaded: [{ filename, url, type: "image" | "document" }] }
  // PDFs processed via Gemini multimodal for brand guide extraction
  // Images analyzed for brand colors, style, and product identification
```

### Content Planning

```
POST /api/plans
Body: { brand_id: string, goals?: string, platforms?: string[], business_events?: string }
Response: { plan_id: string, pillars: Pillar[], calendar: DayBrief[7] }
  // Triggers Strategy Agent
  // Pillar: { id: string, theme: string, key_message: string, source: "event" | "generated" }
  // business_events: free-text, e.g. "launching lavender croissant Tuesday, farmer's market Saturday"
  // DayBrief now includes: pillar_id, derivative_type, pillar_context

GET /api/plans/{planId}
Response: { plan: ContentPlan }

PUT /api/plans/{planId}/days/{dayIndex}
Body: Partial<DayBrief>  // User rearrangement
Response: { day: DayBrief }
```

### Photo Upload (P1 — BYOP)

```
POST /api/plans/{planId}/days/{dayIndex}/photo
Body: multipart/form-data (photo)
Response: { photo_url: string, day_index: int }
  // Uploads user photo to GCS, sets user_photo_url on the day brief
  // When this day is generated, Content Creator uses Mode B (image understanding)

DELETE /api/plans/{planId}/days/{dayIndex}/photo
Response: { status: "removed" }
  // Removes user photo, day reverts to Mode A (interleaved generation)
```

### Content Generation (SSE Stream)

```
GET /api/generate/{planId}/{dayIndex}
Accept: text/event-stream
Response: SSE stream of events:

  MODE A (AI-generated image — no user photo on this day):
  event: text
  data: {"content": "Rise and grind! Our new espresso blend..."}
  
  event: image
  data: {"url": "https://storage.googleapis.com/...", "mime_type": "image/png", "source": "generated"}
  
  event: text
  data: {"content": "#coffee #morningroutine #espresso..."}
  
  MODE B (user photo uploaded for this day — P1 BYOP):
  event: text
  data: {"content": "That golden hour light hitting the fresh batch..."}
  
  event: image
  data: {"url": "https://storage.googleapis.com/.../user_photo.jpg", "mime_type": "image/jpeg", "source": "user_upload"}
  
  event: text
  data: {"content": "#bakerylife #freshbread #goldenhour..."}
  
  BOTH MODES:
  event: complete
  data: {"post_id": "abc123"}
  data: {"post_id": "post_abc123"}
  
  event: review
  data: {"overall_score": 4.2, "approved": true, "checks": {...}}
```

### Post Management

```
GET /api/posts?brand_id={brandId}&plan_id={planId}
Response: { posts: Post[] }

PUT /api/posts/{postId}/approve
Response: { status: "approved" }

POST /api/posts/{postId}/regenerate
Body: { feedback?: string }
Response: SSE stream (same as generate)

GET /api/posts/{postId}/export
Response: { caption: string, image_url: string, hashtags: string[], download_url: string }

POST /api/export/{planId}
Response: { zip_url: string }  // All posts as ZIP
```

## 4.2 SSE Implementation

```python
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import json
import os

app = FastAPI()

# CORS middleware (for local dev: Vite on :5173, FastAPI on :8080)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend static files (Vite build output)
frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

@app.get("/api/generate/{plan_id}/{day_index}")
async def generate_post_endpoint(plan_id: str, day_index: int, request: Request):
    """Stream interleaved post generation via SSE."""
    
    # Budget guard (Gap #7)
    if not budget_tracker.can_generate():
        return JSONResponse(
            status_code=429, 
            content={"error": "Image generation budget exhausted", 
                     "budget": budget_tracker.get_status()}
        )
    
    # Load brand profile and day brief
    plan = await firestore_client.get_plan(plan_id)
    brand = await firestore_client.get_brand(plan["brand_id"])
    day_brief = plan["days"][day_index]
    
    # Check if user uploaded their own photo for this day (P1 BYOP)
    user_photo_url = day_brief.get("user_photo_url", None)
    
    async def event_stream():
        post_data = {"texts": [], "images": [], "post_id": None}
        
        try:
            # Generate interleaved content (Mode A or B based on user photo)
            async for part in generate_post(brand, day_brief, user_photo_url=user_photo_url):
                if part["type"] == "text":
                    post_data["texts"].append(part["content"])
                    yield f"event: text\ndata: {json.dumps(part)}\n\n"
                elif part["type"] == "image":
                    post_data["images"].append(part["url"])
                    yield f"event: image\ndata: {json.dumps(part)}\n\n"
            
            # Zero-image fallback (Gap #5): only check if we expected AI image generation
            # In BYOP mode (user_photo_url present), no AI image is expected
            if not post_data["images"] and not user_photo_url:
                logger.warning("generation_no_image", extra={
                    "plan_id": plan_id, "day_index": day_index,
                    "text_parts": len(post_data["texts"]),
                })
                yield f'event: status\ndata: {json.dumps({"message": "Retrying image generation..."})}\n\n'
                
                # Retry with more explicit image instruction
                retry_results = await generate_post_fallback(brand, day_brief)
                retry_images = [r for r in retry_results if r["type"] == "image"]
                
                if retry_images:
                    for img in retry_images:
                        post_data["images"].append(img["url"])
                        yield f"event: image\ndata: {json.dumps(img)}\n\n"
                else:
                    # Both attempts failed — emit error event
                    yield f'event: error\ndata: {json.dumps({"code": "IMAGE_GEN_FAILED", "message": "Image generation failed after retry. Caption was saved — you can regenerate the image."})}\n\n'
            
            # Track budget
            budget_tracker.record_generation(len(post_data["images"]))
            
            # Save post to Firestore
            post_id = await firestore_client.save_post(
                brand_id=plan["brand_id"],
                plan_id=plan_id,
                day_index=day_index,
                caption="\n".join(post_data["texts"]),
                image_urls=post_data["images"],
                platform=day_brief["platform"],
            )
            post_data["post_id"] = post_id
            yield f"event: complete\ndata: {json.dumps({'post_id': post_id})}\n\n"
            
            # Run review agent
            review = await run_review_agent(brand, post_data)
            await firestore_client.save_review(post_id, review)
            yield f"event: review\ndata: {json.dumps(review)}\n\n"
        
        except Exception as e:
            logger.error("generation_error", extra={
                "plan_id": plan_id, "day_index": day_index, "error": str(e),
            })
            yield f'event: error\ndata: {json.dumps({"code": "GENERATION_ERROR", "message": str(e)})}\n\n'
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )
```

## 4.3 TypeScript API Client

```typescript
// Frontend SSE consumer
function usePostGeneration(planId: string, dayIndex: number) {
  const [caption, setCaption] = useState<string>("");
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [imageSource, setImageSource] = useState<"generated" | "user_upload" | null>(null);
  const [hashtags, setHashtags] = useState<string>("");
  const [review, setReview] = useState<ReviewResult | null>(null);
  const [error, setError] = useState<{ code: string; message: string } | null>(null);
  const [status, setStatus] = useState<"idle" | "generating" | "reviewing" | "done" | "error">("idle");
  
  const generate = useCallback(() => {
    setStatus("generating");
    setCaption("");
    setImageUrl(null);
    setHashtags("");
    setError(null);
    
    const eventSource = new EventSource(
      `/api/generate/${planId}/${dayIndex}`
    );
    
    let textParts: string[] = [];
    
    eventSource.addEventListener("text", (e) => {
      const data = JSON.parse(e.data);
      textParts.push(data.content);
      
      // First text part is usually the caption, subsequent are hashtags
      if (textParts.length === 1) {
        setCaption(data.content);
      } else {
        setHashtags(prev => prev + data.content);
      }
    });
    
    eventSource.addEventListener("image", (e) => {
      const data = JSON.parse(e.data);
      setImageUrl(data.url);
      setImageSource(data.source || "generated");  // "generated" or "user_upload"
    });
    
    eventSource.addEventListener("complete", (e) => {
      setStatus("reviewing");
    });
    
    eventSource.addEventListener("review", (e) => {
      const data = JSON.parse(e.data);
      setReview(data);
      setStatus("done");
      eventSource.close();
    });
    
    eventSource.addEventListener("error", (e) => {
      try {
        const data = JSON.parse((e as MessageEvent).data);
        setError(data);
        // IMAGE_GEN_FAILED is non-fatal — caption was still saved
        if (data.code === "IMAGE_GEN_FAILED") {
          setStatus("done");  // Allow user to retry image only
        } else {
          setStatus("error");
        }
      } catch {
        setStatus("error");
        setError({ code: "UNKNOWN", message: "Connection lost" });
      }
      eventSource.close();
    });
    
    eventSource.onerror = () => {
      eventSource.close();
      setStatus("error");
      setError({ code: "CONNECTION_ERROR", message: "Lost connection to server" });
    };
  }, [planId, dayIndex]);
  
  return { caption, imageUrl, hashtags, review, error, status, generate };
}
```

---

# 5. Data Model (Firestore)

## 5.1 Complete Schema

```
amplifi-db/
├── brands/
│   └── {brandId}/                         # Auto-generated
│       ├── business_name: string          # "Sunrise Bakery"
│       ├── business_type: string          # AI-inferred from description: "local_business" | "service" | "personal_brand" | "ecommerce"
│       ├── website_url: string | null     # "https://sunrisebakery.com" — null in no-website mode
│       ├── description: string            # Required free-text business description (min 20 chars)
│       ├── uploaded_assets: [{            # Optional brand assets (max 3)
│       │     filename: string,
│       │     url: string,                 # Cloud Storage signed URL
│       │     type: "image" | "document"
│       │   }]
│       ├── industry: string               # "Food & Beverage"
│       ├── tone: string                   # "warm, approachable, artisanal"
│       ├── colors: string[]               # ["#D4A574", "#8B4513", "#FFF8DC"]
│       ├── target_audience: string        # "Local food enthusiasts, 25-45, urban"
│       ├── visual_style: string           # "warm lighting, rustic textures, close-up product shots"
│       ├── image_style_directive: string  # P1: persistent visual identity fragment prepended to every image gen
│       │                                  # e.g. "warm earth tones, terracotta and sage accents, soft golden 
│       │                                  # hour lighting, minimalist compositions, organic textures"
│       ├── caption_style_directive: string # P1: persistent writing rhythm guide prepended to every caption gen
│       │                                  # e.g. "Open with one-sentence hook under 10 words. Personal anecdote
│       │                                  # second. Counterintuitive insight third. End with direct question."
│       ├── content_themes: string[]       # ["artisan process", "seasonal menu", "community events"]
│       ├── competitors: string[]          # ["competitor_a.com", "competitor_b.com"]
│       ├── logo_url: string | null        # "gs://amplifi-assets/brands/{brandId}/logo.png"
│       ├── product_photos: string[]       # ["gs://...", "gs://..."]
│       ├── created_at: timestamp
│       ├── updated_at: timestamp
│       ├── analysis_status: string        # "pending" | "analyzing" | "complete" | "failed"
│       │
│       ├── content_plans/                 # Subcollection
│       │   └── {planId}/
│       │       ├── week_of: string        # "2026-02-24" (ISO date of Monday)
│       │       ├── goals: string | null   # "Launch spring menu"
│       │       ├── business_events: string | null  # P1: "launching lavender croissant Tuesday, farmer's market Saturday"
│       │       ├── platforms: string[]    # ["instagram", "linkedin"]
│       │       ├── created_at: timestamp
│       │       ├── status: string         # "draft" | "generating" | "complete"
│       │       │
│       │       ├── pillars/               # Subcollection (P1 content repurposing)
│       │       │   └── {pillarId}/
│       │       │       ├── theme: string          # "Pricing your services"
│       │       │       ├── key_message: string    # "Value-based pricing builds better businesses"
│       │       │       ├── source: string         # "event" | "generated" — whether from business_events or AI-created
│       │       │       └── derivative_count: number  # How many days derive from this pillar
│       │       │
│       │       └── days/                  # Subcollection (7 documents)
│       │           └── {dayIndex}/        # "0" through "6" (Monday=0)
│       │               ├── day_name: string          # "Monday"
│       │               ├── platform: string          # "instagram"
│       │               ├── theme: string             # "Behind the scenes: morning bake"
│       │               ├── content_type: string      # "photo" | "carousel" | "story" | "reel" | "thread"
│       │               ├── caption_direction: string # "Show the early morning process, warm and inviting"
│       │               ├── image_direction: string   # "Golden hour lighting on fresh bread, flour dusted surface"
│       │               ├── posting_time: string      # "11:30 AM EST"
│       │               │
│       │               ├── pillar_id: string | null          # Reference to pillar (P1 repurposing)
│       │               ├── derivative_type: string | null    # "original" | "condensed" | "visual" | "conversational" | "engagement" | "standalone"
│       │               ├── pillar_context: string | null     # Key message from pillar for Content Creator coherence
│       │               │
│       │               ├── user_photo_url: string | null     # GCS URL of user-uploaded photo (P1 BYOP)
│       │               ├── image_source: string              # "generated" | "user_upload" (set after generation)
│       │               │
│       │               ├── generated: boolean        # Has content been generated?
│       │               ├── post_id: string | null    # Reference to generated post
│       │               └── status: string            # "planned" | "generated" | "approved" | "posted"
│       │
│       └── posts/                         # Subcollection
│           └── {postId}/
│               ├── plan_id: string        # Parent plan reference
│               ├── day_index: number      # 0-6
│               ├── platform: string       # "instagram"
│               ├── caption: string        # Full caption text
│               ├── image_urls: string[]   # ["gs://amplifi-assets/generated/{postId}/image.png"]
│               ├── hashtags: string[]     # ["#artisanbread", "#freshbaked", ...]
│               ├── posting_time: string   # "11:30 AM EST"
│               ├── status: string         # "draft" | "approved" | "posted"
│               │
│               ├── review/                # Embedded document
│               │   ├── overall_score: number     # 1-5
│               │   ├── approved: boolean
│               │   ├── tone_score: number
│               │   ├── audience_score: number
│               │   ├── platform_score: number
│               │   ├── visual_score: number
│               │   ├── quality_score: number
│               │   ├── suggestions: string[]
│               │   └── reviewed_at: timestamp
│               │
│               ├── video/                 # Embedded document (P1)
│               │   ├── url: string | null         # Signed URL to MP4 in Cloud Storage
│               │   ├── duration_seconds: number   # 8
│               │   ├── aspect_ratio: string       # "9:16" | "16:9"
│               │   ├── model: string              # "veo-3.1-fast-generate-preview"
│               │   ├── job_id: string | null      # Reference to video_jobs
│               │   └── generated_at: timestamp | null
│               │
│               ├── created_at: timestamp
│               └── updated_at: timestamp
│
│       └── video_jobs/                    # Subcollection (P1)
│           └── {jobId}/
│               ├── post_id: string
│               ├── status: string                 # "queued" | "generating" | "complete" | "failed"
│               ├── tier: string                   # "fast" | "standard"
│               ├── result: map | null             # { video_url, duration_seconds, ... }
│               ├── error: string | null
│               ├── created_at: timestamp
│               └── updated_at: timestamp
```

## 5.2 Cloud Storage Structure

```
gs://amplifi-assets-2026/
├── brands/
│   └── {brandId}/
│       ├── logo.png                       # Uploaded by user
│       ├── product_photos/
│       │   ├── photo_1.jpg
│       │   ├── photo_2.jpg
│       │   └── ...
│       └── website_screenshot.png         # Auto-captured during analysis
│
└── generated/
    └── {postId}/
        ├── image_0.png                    # First generated image
        ├── image_1.png                    # Additional images (carousel)
        ├── video_abc123.mp4               # Generated video clip (P1)
        └── ...
```

## 5.3 Cloud Storage Operations

```python
from google.cloud import storage
import uuid
from datetime import timedelta

storage_client = storage.Client()
BUCKET_NAME = f"{os.environ['GOOGLE_CLOUD_PROJECT']}-amplifi-assets"
bucket = storage_client.bucket(BUCKET_NAME)

async def upload_image_to_gcs(image_bytes: bytes, mime_type: str, 
                                post_id: str = None) -> str:
    """Upload a generated image to Cloud Storage and return a signed URL.
    
    Args:
        image_bytes: Raw image data from Gemini's inline_data
        mime_type: e.g., "image/png"
        post_id: Optional post ID for organized storage
    
    Returns: Signed URL valid for 7 days
    """
    if not post_id:
        post_id = str(uuid.uuid4())
    
    blob_path = f"generated/{post_id}/image_{uuid.uuid4().hex[:8]}.png"
    blob = bucket.blob(blob_path)
    
    blob.upload_from_string(image_bytes, content_type=mime_type)
    
    # Generate signed URL (7-day expiry)
    signed_url = blob.generate_signed_url(
        expiration=timedelta(days=7),
        method="GET"
    )
    
    return signed_url

async def upload_brand_asset(brand_id: str, file_bytes: bytes, 
                              filename: str, mime_type: str) -> str:
    """Upload a user's brand asset (logo, product photo)."""
    blob_path = f"brands/{brand_id}/{filename}"
    blob = bucket.blob(blob_path)
    blob.upload_from_string(file_bytes, content_type=mime_type)
    return f"gs://{BUCKET_NAME}/{blob_path}"
```

---

# 6. Interleaved Output: Deep Dive

## 6.1 How It Works

The Gemini API's interleaved output generates text and images in a single `generateContent` call. The response contains an ordered list of `Part` objects that alternate between `text` parts and `inline_data` parts (raw image bytes).

```python
# Actual API call
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="Create an Instagram post for a bakery's fresh sourdough bread. "
             "Include a warm, inviting caption and generate a matching product image.",
    config=types.GenerateContentConfig(
        response_modalities=["TEXT", "IMAGE"]
    )
)

# Response structure
# response.candidates[0].content.parts = [
#   Part(text="Rise and shine! Our signature sourdough is fresh out of the oven..."),
#   Part(inline_data=InlineData(mime_type="image/png", data=b'\x89PNG...')),
#   Part(text="#sourdough #freshbread #artisanbakery #morningroutine #bakerylife"),
# ]
```

## 6.2 Response Parsing

```python
from dataclasses import dataclass

@dataclass
class GeneratedPost:
    caption: str
    image_urls: list[str]
    hashtags: str
    raw_text_parts: list[str]

async def parse_interleaved_response(response, post_id: str) -> GeneratedPost:
    """Parse interleaved text + image response into structured post data."""
    
    text_parts = []
    image_urls = []
    
    for part in response.candidates[0].content.parts:
        if part.text:
            text_parts.append(part.text.strip())
        elif part.inline_data:
            url = await upload_image_to_gcs(
                part.inline_data.data,
                part.inline_data.mime_type,
                post_id=post_id
            )
            image_urls.append(url)
    
    # Heuristic: first text part = caption, last text part containing # = hashtags
    caption = text_parts[0] if text_parts else ""
    hashtags = ""
    for t in reversed(text_parts):
        if "#" in t:
            hashtags = t
            break
    
    return GeneratedPost(
        caption=caption,
        image_urls=image_urls,
        hashtags=hashtags,
        raw_text_parts=text_parts
    )
```

## 6.3 Budget Management

```python
# Image generation cost tracking
IMAGE_COST_TOKENS = 1290        # Tokens per generated image
TOKEN_COST_PER_MILLION = 30.0   # $30 per 1M output tokens
COST_PER_IMAGE = IMAGE_COST_TOKENS * TOKEN_COST_PER_MILLION / 1_000_000  # ~$0.039
COST_PER_VIDEO_FAST = 0.15 * 8  # $0.15/sec × 8 sec = $1.20 per clip (Veo 3.1 Fast)
COST_PER_VIDEO_STD = 0.40 * 8   # $0.40/sec × 8 sec = $3.20 per clip (Veo 3.1 Standard)
TOTAL_CREDIT = 100.0            # $100 Google Cloud credit

# Budget allocation (updated to include video)
IMAGE_BUDGET = 70.0             # $70 for images (~1,795 images)
VIDEO_BUDGET = 30.0             # $30 for videos (~25 Fast clips or ~9 Standard)
MAX_IMAGES = int(IMAGE_BUDGET / COST_PER_IMAGE)
MAX_VIDEOS_FAST = int(VIDEO_BUDGET / COST_PER_VIDEO_FAST)

class BudgetTracker:
    """Track image AND video generation costs against $100 credit."""
    
    def __init__(self):
        self.images_generated = 0
        self.videos_generated = 0
        self.image_cost = 0.0
        self.video_cost = 0.0
    
    @property
    def total_cost(self) -> float:
        return self.image_cost + self.video_cost
    
    def can_generate_image(self) -> bool:
        return self.total_cost < (TOTAL_CREDIT * 0.8)
    
    def can_generate_video(self) -> bool:
        return self.total_cost + COST_PER_VIDEO_FAST < (TOTAL_CREDIT * 0.8)
    
    def record_image(self, num_images: int = 1):
        self.images_generated += num_images
        self.image_cost = self.images_generated * COST_PER_IMAGE
    
    def record_video(self, tier: str = "fast"):
        self.videos_generated += 1
        cost = COST_PER_VIDEO_FAST if tier == "fast" else COST_PER_VIDEO_STD
        self.video_cost += cost
    
    def get_status(self) -> dict:
        return {
            "images_generated": self.images_generated,
            "videos_generated": self.videos_generated,
            "image_cost": f"${self.image_cost:.2f}",
            "video_cost": f"${self.video_cost:.2f}",
            "total_cost": f"${self.total_cost:.2f}",
            "budget_remaining": f"${TOTAL_CREDIT - self.total_cost:.2f}",
        }
```

## 6.4 Video Generation via Veo 3.1 (P1)

Video generation is a **separate, additive flow** that builds on top of the P0 interleaved image output. It is NOT part of the SSE generation stream. It has its own endpoint, its own UI button, and its own async lifecycle.

**Platform-aware display:** On text-first platforms (LinkedIn, X, Twitter, Facebook), the video section defaults to a collapsed pill ("🎬 Video Clip (not typical for this platform) ›") to reduce visual noise. `TEXT_PLATFORMS = new Set(['linkedin', 'x', 'twitter', 'facebook'])` controls this behavior. `videoExpanded` state (default `false`) toggles between collapsed pill and full section. State resets to collapsed on every `postId` change. Video-first platforms (Instagram, TikTok, Reels) always show the full expanded section.

### 6.4.1 Architecture Decision

The interleaved output hero image becomes Veo's **first frame**, ensuring visual continuity between the static post and the video clip. This is the key design insight: the image and video share the same visual DNA because one literally starts from the other.

```
Interleaved Output (P0)              Veo Video (P1)
┌─────────────────────┐              ┌─────────────────────┐
│ Caption text         │              │                     │
│ ┌─────────────────┐ │   first      │  ┌─────────────┐   │
│ │  Hero Image     │─┼───frame────▶ │  │  8-sec MP4  │   │
│ │  (generated)    │ │              │  │  720p/1080p  │   │
│ └─────────────────┘ │              │  │  with audio  │   │
│ Hashtags             │              │  └─────────────┘   │
└─────────────────────┘              └─────────────────────┘
     SSE (streaming)                    REST (async poll)
     ~10-20 sec                         ~2-3 min
```

### 6.4.2 Veo API Integration

```python
from google import genai
from google.genai import types
import asyncio

client = genai.Client()

async def generate_video(
    hero_image_bytes: bytes,
    caption: str,
    brand_profile: dict,
    platform: str,
    tier: str = "fast"
) -> dict:
    """Generate an 8-second video clip from a hero image using Veo 3.1.
    
    Args:
        hero_image_bytes: Raw bytes of the interleaved-output hero image
        caption: Post caption (used to build video prompt)
        brand_profile: Brand profile for style guidance
        platform: Target platform (determines aspect ratio)
        tier: "fast" ($1.20/clip) or "standard" ($3.20/clip)
    
    Returns: { video_url: str, duration_seconds: int, status: str }
    """
    
    # Select model based on tier
    model = "veo-3.1-fast-generate-preview" if tier == "fast" else "veo-3.1-generate-preview"
    
    # Determine aspect ratio from platform
    aspect_ratio = "9:16" if platform in ["instagram", "tiktok"] else "16:9"
    
    # Build cinematic video prompt from caption + brand context
    video_prompt = f"""Create a smooth, professional social media video for {brand_profile['business_name']}.

BRAND STYLE: {brand_profile.get('visual_style', 'clean, modern, professional')}
BRAND TONE: {brand_profile.get('tone', 'professional')}
POST CAPTION CONTEXT: {caption[:200]}

VIDEO DIRECTION:
- Start from the provided hero image as the first frame
- Add subtle, elegant motion: slow zoom, parallax, product reveal, or lifestyle movement
- Maintain the color palette and mood of the starting image throughout
- NO text overlays, NO watermarks, NO logos
- The motion should feel cinematic and intentional, not stock-footage generic
- Audio: ambient, brand-appropriate background music or subtle sound design
"""
    
    # Convert hero image bytes to Veo-compatible image
    hero_image = types.Image.from_bytes(data=hero_image_bytes, mime_type="image/png")
    
    # Start async video generation
    operation = client.models.generate_videos(
        model=model,
        prompt=video_prompt,
        image=hero_image,
        config=types.GenerateVideosConfig(
            aspect_ratio=aspect_ratio,
            number_of_videos=1,
        ),
    )
    
    # Poll for completion (2-3 min typical)
    while not operation.done:
        await asyncio.sleep(10)
        operation = client.operations.get(operation)
    
    # Extract video
    generated_video = operation.response.generated_videos[0]
    video_bytes = generated_video.video.video_bytes
    
    # Upload to Cloud Storage
    video_url = await upload_video_to_gcs(video_bytes, post_id=None)
    
    return {
        "video_url": video_url,
        "duration_seconds": 8,
        "model": model,
        "aspect_ratio": aspect_ratio,
        "status": "complete",
    }


async def upload_video_to_gcs(video_bytes: bytes, post_id: str) -> str:
    """Upload generated MP4 to Cloud Storage and return signed URL."""
    blob_path = f"generated/{post_id}/video_{uuid.uuid4().hex[:8]}.mp4"
    blob = bucket.blob(blob_path)
    blob.upload_from_string(video_bytes, content_type="video/mp4")
    
    signed_url = blob.generate_signed_url(
        expiration=timedelta(days=7),
        method="GET"
    )
    return signed_url
```

### 6.4.3 REST Endpoint

```python
@app.post("/api/posts/{post_id}/generate-video")
async def generate_video_endpoint(post_id: str, tier: str = "fast"):
    """Start async video generation for a post that already has a hero image.
    
    Returns immediately with a job_id. Client polls for completion.
    """
    
    # Budget check
    if not budget_tracker.can_generate_video():
        return JSONResponse(
            status_code=429,
            content={"error": "Video generation budget exhausted",
                     "budget": budget_tracker.get_status()}
        )
    
    # Load post data
    post = await firestore_client.get_post(post_id)
    brand = await firestore_client.get_brand(post["brand_id"])
    
    if not post.get("image_urls"):
        return JSONResponse(
            status_code=400,
            content={"error": "Post must have a hero image before video generation"}
        )
    
    # Download hero image from GCS
    hero_image_bytes = await download_from_gcs(post["image_urls"][0])
    
    # Create job record in Firestore
    job_id = await firestore_client.create_video_job(post_id, tier)
    
    # Start generation in background
    asyncio.create_task(
        _run_video_generation(job_id, post_id, hero_image_bytes, post, brand, tier)
    )
    
    return {"job_id": job_id, "status": "processing", "estimated_seconds": 150}


async def _run_video_generation(job_id, post_id, hero_image_bytes, post, brand, tier):
    """Background task for video generation."""
    try:
        await firestore_client.update_video_job(job_id, "generating")
        
        result = await generate_video(
            hero_image_bytes=hero_image_bytes,
            caption=post["caption"],
            brand_profile=brand,
            platform=post["platform"],
            tier=tier,
        )
        
        # Save video URL to post
        await firestore_client.update_post_video(post_id, result["video_url"])
        await firestore_client.update_video_job(job_id, "complete", result)
        
        # Track budget
        budget_tracker.record_video(tier)
        
    except Exception as e:
        logger.error("video_generation_error", extra={
            "job_id": job_id, "post_id": post_id, "error": str(e)
        })
        await firestore_client.update_video_job(job_id, "failed", {"error": str(e)})


@app.get("/api/video-jobs/{job_id}")
async def get_video_job_status(job_id: str):
    """Poll video generation status."""
    job = await firestore_client.get_video_job(job_id)
    return job
```

### 6.4.4 Frontend Integration

```typescript
// useVideoGeneration.ts
function useVideoGeneration(postId: string) {
  const [status, setStatus] = useState<"idle" | "generating" | "complete" | "error">("idle");
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  
  const generateVideo = useCallback(async (tier: "fast" | "standard" = "fast") => {
    setStatus("generating");
    setProgress(0);
    
    // Start generation
    const res = await fetch(`/api/posts/${postId}/generate-video?tier=${tier}`, {
      method: "POST"
    });
    const { job_id, estimated_seconds } = await res.json();
    
    // Poll for completion
    const startTime = Date.now();
    const pollInterval = setInterval(async () => {
      const statusRes = await fetch(`/api/video-jobs/${job_id}`);
      const job = await statusRes.json();
      
      // Update progress estimate
      const elapsed = (Date.now() - startTime) / 1000;
      setProgress(Math.min(95, (elapsed / estimated_seconds) * 100));
      
      if (job.status === "complete") {
        clearInterval(pollInterval);
        setVideoUrl(job.result.video_url);
        setProgress(100);
        setStatus("complete");
      } else if (job.status === "failed") {
        clearInterval(pollInterval);
        setStatus("error");
      }
    }, 5000);  // Poll every 5 seconds
  }, [postId]);
  
  return { status, videoUrl, progress, generateVideo };
}
```

```typescript
// VideoGenerateButton.tsx — appears on DayCards for reel/story/tiktok content types
function VideoGenerateButton({ postId, contentType }: Props) {
  const { status, videoUrl, progress, generateVideo } = useVideoGeneration(postId);
  
  // Only show for video-eligible content types
  if (!["reel", "story", "tiktok"].includes(contentType)) return null;
  
  return (
    <div className="video-generation">
      {status === "idle" && (
        <button 
          onClick={() => generateVideo("fast")}
          className="px-4 py-2 bg-purple-600 text-white rounded-lg flex items-center gap-2"
        >
          <VideoIcon size={16} /> Generate Video Clip
        </button>
      )}
      
      {status === "generating" && (
        <div className="flex items-center gap-3">
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div 
              className="bg-purple-600 h-2 rounded-full transition-all" 
              style={{ width: `${progress}%` }}
            />
          </div>
          <span className="text-sm text-gray-500">{Math.round(progress)}%</span>
        </div>
      )}
      
      {status === "complete" && videoUrl && (
        <video 
          src={videoUrl} 
          controls 
          className="rounded-lg shadow-lg w-full"
          poster={/* hero image URL */}
        />
      )}
      
      {status === "error" && (
        <button onClick={() => generateVideo("fast")} className="text-red-500">
          Video failed — Retry
        </button>
      )}
    </div>
  );
}
```

---

# 7. Frontend Architecture

## 7.1 React Component Tree

```
App (React Router)
├── LandingPage (/)
│   ├── HeroSection (gradient headline, value prop, dual CTAs)
│   ├── ProductPreview (mini calendar preview with pillar tags)
│   ├── HowItWorks (3-step cards: URL → Brand → Calendar)
│   ├── FeaturesGrid (2×3: brand-aware, multi-platform, BYOP, video, pillars, events)
│   ├── Testimonial (social proof placeholder)
│   └── FooterCTA (repeat start button)
│
├── OnboardPage (/onboard)
│   └── BrandWizard
│       ├── URLInput (website URL — hidden in no-website mode)
│       ├── DescriptionInput (free-text textarea, min 20 chars, always visible)
│       ├── NoWebsiteToggle ("No website? Describe your business instead →")
│       ├── AssetUploadZone (optional drag-drop for images/PDFs, max 3 files)
│       │   └── UploadedFileList (filename, type icon, remove button)
│       └── AnalysisProgress (step-by-step with adaptive steps based on mode)
│
├── DashboardPage (/dashboard/{brandId})
│   ├── BrandProfileCard (editable brand profile summary)
│   │   ├── InferredBusinessType (AI-inferred from description, editable)
│   │   ├── ColorSwatches (clickable hex colors)
│   │   ├── ToneChips (editable tone adjectives)
│   │   ├── ImageStyleDirective (P1 — shows visual identity seed, editable)
│   │   │   └── "warm earth tones, soft natural lighting, minimalist..."
│   │   ├── CaptionStyleDirective (P1 — shows writing rhythm guide, editable)
│   │   │   └── "Open with hook under 10 words. Personal story second..."
│   │   ├── AudienceDescription
│   │   └── EditButton → BrandEditModal
│   │
│   ├── ContentCalendar
│   │   ├── CalendarHeader (week selector, "Generate All" button)
│   │   ├── EventsInput (P1 — "What's happening this week?" free-text area)
│   │   │   └── Placeholder: "launching lavender croissant Tuesday, farmer's market Saturday..."
│   │   ├── PillarSummary (P1 — shows 1-2 pillar themes with derivative count + event/generated badge)
│   │   └── DayCard[7]
│   │       ├── DayLabel ("Monday")
│   │       ├── PlatformBadge (Instagram icon)
│   │       ├── PillarTag (P1 — "Pillar: Pricing Strategy" or "Standalone")
│   │       ├── DerivativeType (P1 — "Original" | "X Thread" | "Carousel" | etc.)
│   │       ├── ThemePreview (truncated theme text)
│   │       ├── PhotoDropZone (P1 BYOP — "Drop your photo here" / uploaded thumbnail)
│   │       ├── StatusBadge (planned / generated / approved)
│   │       └── GenerateButton → opens PostGenerator
│   │
│   └── PostLibrary (grid of all generated posts)
│       ├── HeaderRow
│       │   ├── RefreshButton
│       │   ├── CopyAllButton ("📋 Copy All" / "✓ Copied N" — bulk clipboard export)
│       │   └── ExportAllButton (ZIP download)
│       └── PostCard[]
│           ├── ImageThumbnail
│           ├── VideoPlayer (if video generated, P1)
│           ├── CaptionPreview
│           ├── PlatformBadge
│           ├── ReviewScore (1-5 stars)
│           └── ActionButtons (approve, regenerate, download, copy caption)
│
├── GeneratePage (/generate/{planId}/{dayIndex})
│   ├── DayBriefPanel (theme, platform, directions — editable)
│   │   └── PillarContext (P1 — shows pillar key message if this is a derivative)
│   │
│   ├── GenerationStream ⭐ (the "wow" moment)
│   │   ├── CaptionArea (text streams in progressively)
│   │   ├── ImageArea
│   │   │   ├── Mode A (no user photo): SkeletonLoader → AI-generated image materializes
│   │   │   └── Mode B (BYOP): User photo displayed immediately, caption streams around it
│   │   ├── HashtagArea (tags appear last)
│   │   └── GenerationStatus ("Crafting your caption..." → "done")
│   │
│   ├── VideoSection (P1 — collapsed pill on text-first platforms, expanded on video platforms)
│   │   ├── CollapsedPill (LinkedIn/X/Facebook: "🎬 Video Clip (not typical for this platform) ›")
│   │   ├── GenerateButton ("Generate Video Clip" — visible when expanded)
│   │   ├── ProgressBar (0-100% during async generation)
│   │   └── VideoPlayer (plays MP4 on completion)
│   │
│   ├── ReviewPanel (appears after generation completes)
│   │   ├── ScoreRadar (5 criteria as radar chart)
│   │   ├── CheckList (green ✓ / yellow ⚠ per criterion)
│   │   └── SuggestionsList
│   │
│   └── ActionBar
│       ├── ApproveButton
│       ├── RegenerateButton
│       ├── DownloadImageButton
│       └── CopyCaptionButton
│
└── ExportPage (/export/{planId})
    ├── PageSubtitle ("Copy captions to clipboard, download individual posts, or export as ZIP")
    └── PostLibrary (reused — with CopyAllButton, filter tabs, PostCard grid)
```

## 7.2 Key UI Interactions

### Generation Stream (SSE Consumer)

```typescript
// PostGenerator.tsx
function PostGenerator({ planId, dayIndex }: Props) {
  const { caption, imageUrl, imageSource, hashtags, review, error, status, generate } = 
    usePostGeneration(planId, dayIndex);
  
  return (
    <div className="generation-stream">
      {/* Caption area — text streams in character by character */}
      <div className="caption-area">
        {status === "generating" && !caption && (
          <div className="typing-indicator">
            {imageSource === "user_upload" 
              ? "Analyzing your photo and crafting a caption..." 
              : "Crafting your caption..."}
          </div>
        )}
        {caption && (
          <TypewriterText text={caption} speed={20} />
        )}
      </div>
      
      {/* Image area — different UX for BYOP vs AI-generated */}
      <div className="image-area">
        {/* Mode A: AI-generated — show skeleton until image arrives */}
        {status === "generating" && !imageUrl && imageSource !== "user_upload" && (
          <SkeletonImage className="animate-pulse bg-gray-200 rounded-lg w-full aspect-square" />
        )}
        {/* Mode B: BYOP — user photo shows immediately (already uploaded) */}
        {imageUrl && (
          <div className="relative">
            <img 
              src={imageUrl} 
              alt="Generated content" 
              className="rounded-lg shadow-lg w-full animate-fade-in"
            />
            {imageSource === "user_upload" && (
              <span className="absolute top-2 right-2 bg-blue-500 text-white text-xs px-2 py-1 rounded">
                Your Photo
              </span>
            )}
          </div>
        )}
        {/* Image generation failed — show retry option */}
        {error?.code === "IMAGE_GEN_FAILED" && !imageUrl && (
          <div className="image-error bg-amber-50 border border-amber-200 rounded-lg p-4 text-center">
            <p className="text-amber-800">Image generation failed. Caption was saved.</p>
            <button onClick={generate} className="mt-2 px-4 py-2 bg-amber-500 text-white rounded">
              Retry Image
            </button>
          </div>
        )}
      </div>
      
      {/* General error state */}
      {status === "error" && (
        <div className="error-state bg-red-50 border border-red-200 rounded-lg p-4 text-center">
          <p className="text-red-800">{error?.message || "Generation failed"}</p>
          <button onClick={generate} className="mt-2 px-4 py-2 bg-red-500 text-white rounded">
            Try Again
          </button>
        </div>
      )}
      
      {/* Hashtags */}
      {hashtags && (
        <div className="hashtags text-blue-500 mt-4">
          {hashtags.split(/\s+/).map(tag => (
            <span key={tag} className="mr-2">{tag}</span>
          ))}
        </div>
      )}
      
      {/* Review panel */}
      {review && <ReviewPanel review={review} />}
      
      {/* Action buttons */}
      {status === "done" && (
        <ActionBar postId={...} caption={caption} imageUrl={imageUrl} />
      )}
    </div>
  );
}
```

---

# 8. Deployment & Infrastructure

## 8.1 Docker Configuration

**Frontend Serving Strategy:** Same as Fireside — single container. Vite builds to `frontend/dist/`, FastAPI serves it via `StaticFiles`. One Dockerfile, one Cloud Run service, same-origin eliminates CORS in production.

```dockerfile
# Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies (includes Node.js for frontend build)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Build frontend
COPY frontend/ ./frontend/
RUN cd frontend && npm ci && npm run build

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ ./backend/

ENV PORT=8080
EXPOSE 8080

CMD ["uvicorn", "backend.server:app", "--host", "0.0.0.0", "--port", "8080"]
```

```txt
# requirements.txt
fastapi==0.115.0
uvicorn[standard]==0.30.0
google-adk==0.5.0
google-genai==1.0.0
google-cloud-firestore==2.19.0
google-cloud-storage==2.18.0
httpx==0.27.0
beautifulsoup4==4.12.3
pydantic==2.9.0
python-dotenv==1.0.0
python-multipart==0.0.9
```

## 8.2 Terraform

```hcl
# terraform/amplifi.tf

resource "google_cloud_run_v2_service" "amplifi" {
  name     = "amplifi"
  location = var.region

  template {
    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/hackathon/amplifi:latest"
      
      ports {
        container_port = 8080
      }
      
      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = var.project_id
      }
      env {
        name  = "GCS_BUCKET"
        value = google_storage_bucket.amplifi_assets.name
      }
      
      resources {
        limits = {
          cpu    = "2"
          memory = "1Gi"
        }
      }
    }
    
    scaling {
      min_instance_count = 0
      max_instance_count = 5
    }
    
    timeout = "300s"  # 5 min for long generation requests
  }
}

resource "google_cloud_run_v2_service_iam_member" "amplifi_public" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.amplifi.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_storage_bucket" "amplifi_assets" {
  name     = "${var.project_id}-amplifi-assets"
  location = "US"
  
  uniform_bucket_level_access = true
  
  cors {
    origin          = ["*"]
    method          = ["GET"]
    response_header = ["Content-Type"]
    max_age_seconds = 3600
  }
}
```

## 8.3 Cloud Build Pipeline

```yaml
# cloudbuild-amplifi.yaml
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: 
      - 'build'
      - '-t'
      - '${_REGION}-docker.pkg.dev/$PROJECT_ID/hackathon/amplifi:$SHORT_SHA'
      - '-t'
      - '${_REGION}-docker.pkg.dev/$PROJECT_ID/hackathon/amplifi:latest'
      - './amplifi/backend'

  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', '--all-tags', '${_REGION}-docker.pkg.dev/$PROJECT_ID/hackathon/amplifi']

  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    args:
      - 'gcloud'
      - 'run'
      - 'deploy'
      - 'amplifi'
      - '--image'
      - '${_REGION}-docker.pkg.dev/$PROJECT_ID/hackathon/amplifi:$SHORT_SHA'
      - '--region'
      - '${_REGION}'
      - '--allow-unauthenticated'

substitutions:
  _REGION: 'us-central1'
```

---

# 9. Repository Structure

```
amplifi/
├── backend/
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── brand_analyst.py       # Brand Analyst Agent + system prompt
│   │   ├── strategist.py          # Strategy Agent + calendar generation
│   │   ├── content_creator.py     # Content Creator Agent (interleaved output)
│   │   ├── video_creator.py       # Video Creator (Veo 3.1 integration, P1)
│   │   └── reviewer.py            # Review Agent + consistency checks
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── web_scraper.py         # fetch_website, extract colors
│   │   ├── brand_tools.py         # analyze_brand_colors, extract_brand_voice
│   │   └── review_tools.py        # check_brand_consistency, validate_hashtags
│   ├── services/
│   │   ├── __init__.py
│   │   ├── firestore_client.py    # All Firestore CRUD operations
│   │   ├── storage_client.py      # Cloud Storage upload + signed URLs
│   │   └── budget_tracker.py      # Image generation budget tracking
│   ├── models/
│   │   ├── __init__.py
│   │   ├── brand.py               # Pydantic models for BrandProfile
│   │   ├── plan.py                # ContentPlan, DayBrief models
│   │   ├── post.py                # Post, ReviewResult models
│   │   └── api.py                 # Request/Response models
│   ├── server.py                  # FastAPI app, all endpoints
│   ├── config.py                  # Environment variables, constants
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── public/
│   │   └── index.html
│   ├── src/
│   │   ├── App.jsx
│   │   ├── pages/
│   │   │   ├── OnboardPage.jsx
│   │   │   ├── DashboardPage.jsx
│   │   │   ├── GeneratePage.jsx
│   │   │   └── ExportPage.jsx
│   │   ├── components/
│   │   │   ├── BrandWizard.jsx
│   │   │   ├── BrandProfileCard.jsx
│   │   │   ├── ContentCalendar.jsx
│   │   │   ├── DayCard.jsx
│   │   │   ├── PostGenerator.jsx    # SSE consumer, generation stream
│   │   │   ├── ReviewPanel.jsx
│   │   │   ├── PostLibrary.jsx
│   │   │   ├── PostCard.jsx
│   │   │   └── ActionBar.jsx
│   │   ├── hooks/
│   │   │   ├── usePostGeneration.ts # SSE hook
│   │   │   ├── useVideoGeneration.ts # Veo polling hook (P1)
│   │   │   ├── useBrandProfile.ts
│   │   │   └── useContentPlan.ts
│   │   ├── api/
│   │   │   └── client.ts           # REST API client (fetch wrapper)
│   │   └── utils/
│   │       └── format.ts           # Date formatting, hashtag parsing
│   ├── package.json
│   └── vite.config.js
├── terraform/
│   ├── amplifi.tf
│   ├── variables.tf
│   └── outputs.tf
├── cloudbuild-amplifi.yaml
├── README.md
└── LICENSE (MIT)
```

---

# 10. Testing Strategy

## 10.1 Testing Tiers

| Tier | What | How | When |
|------|------|-----|------|
| **Unit** | Brand profile parsing, hashtag validation, platform rules | pytest, mocked Gemini responses | Week 1 |
| **Integration** | Brand Analyst → Firestore write → read | Live Gemini API + Firestore emulator | Week 1 |
| **Interleaved Output** | Generate post with text + image, verify both present | Live Gemini API, inspect response parts | Week 1 Friday |
| **SSE Streaming** | Frontend receives progressive events in correct order | FastAPI TestClient + manual browser testing | Week 2 |
| **End-to-End** | Full flow: paste URL → analysis → calendar → generate 7 posts → review | Manual testing with real business URLs | Week 2 Friday |
| **Budget** | Verify cost tracking accuracy across multiple generations | Automated test with counter assertions | Week 2 |

## 10.2 Critical Test Cases

```python
# test_content_creator.py

async def test_interleaved_output_has_text_and_image():
    """Every generated post must contain at least 1 text part and 1 image part."""
    brand = sample_brand_profile()
    brief = sample_day_brief()
    result = await generate_post_fallback(brand, brief)
    
    text_parts = [r for r in result if r["type"] == "text"]
    image_parts = [r for r in result if r["type"] == "image"]
    
    assert len(text_parts) >= 1, "Must have at least one text part (caption)"
    assert len(image_parts) >= 1, "Must have at least one image"

async def test_image_uploaded_to_gcs():
    """Generated images must be stored in Cloud Storage with valid signed URL."""
    # Generate a post, extract image URL
    # Verify URL is accessible via HTTP GET
    # Verify URL expires after 7 days
    pass

async def test_review_agent_catches_wrong_platform_length():
    """Review agent should flag a tweet caption that exceeds 280 characters."""
    brand = sample_brand_profile()
    post = {"caption": "x" * 300, "platform": "x", "hashtags": ["#test"]}
    review = await run_review_agent(brand, post)
    assert review["checks"]["platform"]["score"] < 3
    assert not review["approved"]

async def test_brand_analysis_from_url():
    """Brand Analyst should extract meaningful colors and tone from a real URL."""
    result = await brand_analyst.analyze("https://example-bakery.com")
    assert len(result["colors"]) >= 2
    assert len(result["tone"].split(",")) >= 2
    assert result["industry"] != ""
```

---

# 11. Performance & Monitoring

## 11.1 Performance Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| Brand analysis | < 15s | URL fetch + Gemini analysis |
| Calendar generation | < 10s | Strategy Agent response |
| Post generation (text) | < 5s to first text chunk | SSE first event |
| Post generation (image) | < 20s to image | SSE image event (Gemini image gen latency) |
| Post generation (total) | < 30s per post | SSE complete event |
| Full week generation | < 4 min (7 × 30s) | All 7 posts generated |
| Review | < 5s per post | Review Agent response |
| Image upload to GCS | < 2s | Upload + signed URL generation |
| Video generation (Veo Fast) | < 3 min per clip | Async poll completion |
| Video upload to GCS | < 5s | MP4 upload + signed URL |
| Cold start | < 8s | Cloud Run first request |

## 11.2 Latency Optimization

```python
# Parallel review: run review while user looks at generated content
# (already handled: review runs after generation and streams as separate SSE event)

# Image pre-upload: start uploading image to GCS as soon as inline_data arrives,
# don't wait for the full response to complete
async def stream_and_upload(response_parts):
    upload_tasks = []
    for part in response_parts:
        if part.inline_data:
            # Fire-and-forget upload, collect URL later
            task = asyncio.create_task(
                upload_image_to_gcs(part.inline_data.data, part.inline_data.mime_type)
            )
            upload_tasks.append(task)
    
    # Await all uploads
    urls = await asyncio.gather(*upload_tasks)
    return urls
```

## 11.3 Observability

```python
# Key metrics
logger.info("generation_event", extra={
    "brand_id": brand_id,
    "plan_id": plan_id,
    "day_index": day_index,
    "platform": platform,
    "text_parts": num_text_parts,
    "image_parts": num_image_parts,
    "generation_latency_ms": latency,
    "image_upload_latency_ms": upload_latency,
    "review_score": review_score,
    "estimated_cost": cost,
    "budget_remaining": budget_remaining,
})
```

---

# 12. PRD Cross-Reference & Compliance Matrix

| PRD Requirement | TDD Section | Implementation Status |
|---|---|---|
| Brand analysis from URL (P0) | §3.2 Brand Analyst Agent, §4.1 POST /api/brands/{id}/analyze | ✓ Specified |
| Content calendar generation (P0) | §3.3 Strategy Agent, §4.1 POST /api/plans | ✓ Specified |
| Interleaved post generation (P0) | §3.4 Content Creator Agent, §6 Interleaved Output Deep Dive | ✓ Specified |
| Brand consistency review (P0) | §3.5 Review Agent, §4.1 POST /api/review/{postId} | ✓ Specified |
| React dashboard (P0) | §7 Frontend Architecture | ✓ Specified |
| Image storage — Cloud Storage (P0) | §5.2 Cloud Storage Structure, §5.3 Operations | ✓ Specified |
| Streaming UI — SSE (P0) | §4.2 SSE Implementation, §4.3 TypeScript Client | ✓ Specified |
| Generation error handling | §4.2 SSE error/retry flow, §4.3 error event type, §7.2 error UI | ✓ Specified |
| Budget protection | §4.2 Budget guard (429), §6.3 BudgetTracker | ✓ Specified |
| Individual download (P0) | §7.1 ActionBar (via signed URL — already exists) | ✓ Covered by GCS signed URLs |
| Bring Your Own Photos (P1) | §3.4 Mode B, §4.1 Photo Upload endpoint, §4.2 user_photo_url, §5.1 day schema, §7.1 PhotoDropZone | ✓ Specified |
| Content repurposing / pillars (P1) | §3.3 Strategy Agent pillar prompt, §5.1 pillars subcollection + day pillar fields, §7.1 PillarSummary/PillarTag | ✓ Specified |
| Business persona (P1) | §3.2 Brand Analyst business_type prompt, §4.1 POST /api/brands, §5.1 business_type field, §7.1 BusinessTypeBadge | ✓ Specified |
| Event-aware calendar (P1) | §3.3 Strategy Agent BUSINESS_EVENTS_THIS_WEEK prompt, §4.1 POST /api/plans business_events param, §5.1 business_events field, §7.1 EventsInput | ✓ Specified |
| Visual identity seed (P1) | §3.2 Brand Analyst image_style_directive output, §3.4 Content Creator Mode A prepend, §5.1 image_style_directive field, §7.1 ImageStyleDirective | ✓ Specified |
| Caption style directive (P1) | §3.2 Brand Analyst caption_style_directive output, §3.4 Content Creator base_context prepend, §5.1 caption_style_directive field, §7.1 CaptionStyleDirective | ✓ Specified |
| Video generation via Veo 3.1 (P1) | §6.4 Video Generation, §6.4.2 Veo API, §6.4.3 REST endpoint, §6.4.4 Frontend | ✓ Specified |
| ZIP export (P2) | §12.1.1 One-Tap Caption Export (includes ZIP) | ✓ Specified |
| Engagement prediction (P2) | §12.1.8 Engagement Prediction Scoring | ✓ Specified |
| Social media voice analysis (P2) | §12.1.9 Social Media Voice Analysis | ✓ Specified |
| Platform meta intelligence (P2) | §12.1.10 Platform Meta Intelligence | ✓ Specified |
| Video repurposing / smart editing (P2) | §12.1.12 Video Repurposing / Smart Editing | ✓ Specified |
| Instagram grid consistency (P2) | §12.1.11 Instagram Grid Visual Consistency | ✓ Specified |
| One-tap caption export (P2) | §12.1.1 One-Tap Caption Export | ✓ Specified |
| Platform preview formatting (P2) | §12.1.2 Platform Preview Formatting | ✓ Specified |
| Content editing/regeneration (P2) | §12.1.3 Content Editing & Regeneration | ✓ Specified |
| Competitor visibility toggle (P2) | §12.1.4 Competitor Visibility Toggle | ✓ Specified |
| AI image quality validation (P2) | §12.1.5 AI Image Quality Validation | ✓ Specified |
| Description-first onboarding (P2) | §12.1.6 Description-First Onboarding Option | ✓ Specified |
| Multi-platform formatting (P2) | §12.1.7 Multi-Platform Formatting | ✓ Specified |
| Frontend serving (single container) | §8.1 Docker Configuration | ✓ Specified |
| CORS configuration | §4.2 FastAPI app setup | ✓ Specified |
| Gemini model compliance | §3.4 model="gemini-2.5-flash" | ✓ gemini-2.5-flash with ["TEXT", "IMAGE"] |
| ADK compliance | §3.1 SequentialAgent pipeline | ✓ ADK SequentialAgent |
| Cloud Run + Firestore + Storage | §8 Deployment, §5 Data Model | ✓ All three services |
| Interleaved output (category req) | §6 Deep Dive, responseModalities | ✓ ["TEXT", "IMAGE"] |
| Automated deployment (bonus) | §8.2 Terraform, §8.3 Cloud Build | ✓ Specified |
| Public GitHub repo | §9 Repository Structure | ✓ MIT License |

## 12.1 P2 Architecture Notes (Post-Hackathon)

These features are documented in the PRD and sequenced by PM sprint priority (see PRD Post-Hackathon P2 Roadmap). Each includes implementation detail sufficient to build.

---

### 12.1.1 One-Tap Caption Export (Sprint 4)

**Type:** Frontend + one backend endpoint

**Three export tiers (clipboard-first hierarchy):**

1. **Bulk clipboard ("Copy All")** — PostLibrary header button copies all filtered captions as a structured string with `[N] Platform · Day N` headers and `---` separators. Count is snapshotted at click time via `useRef` (not re-derived at render) to prevent label drift during polling refresh. Timer cleaned up on unmount.

2. **Per-post clipboard** — Each PostCard has a copy button that writes `caption\n\nhashtags` to clipboard with 1.5s confirmation flash.

3. **ZIP export** — `POST /api/export/{plan_id}` generates a ZIP containing per-day caption `.txt` files and images. Served via `StreamingResponse`.

**ExportPage subtitle** leads with clipboard: "Copy captions to clipboard, download individual posts, or export an entire plan as a ZIP archive."

**PostLibrary header button order:** `[Refresh] [Copy All] [Export All]` — lightweight to heavy, left to right. Copy All hidden when no filtered posts exist.

---

### 12.1.2 Platform Preview Formatting (Sprint 4)

**Effort:** 1–2 days | **Type:** Frontend components

```typescript
// Platform-specific preview components

const PLATFORM_LIMITS = {
  instagram: { captionMax: 2200, hashtagMax: 30 },
  linkedin: { captionMax: 3000, foldAt: 140 },  // "see more" fold
  x: { captionMax: 280 },
  tiktok: { captionMax: 2200 },
  facebook: { captionMax: 63206 }
};

const LinkedInPreview: React.FC<{ caption: string; image?: string }> = ({ caption, image }) => {
  const foldAt = PLATFORM_LIMITS.linkedin.foldAt;
  const isFolded = caption.length > foldAt;
  const [expanded, setExpanded] = useState(false);
  
  return (
    <div className="linkedin-preview">
      <div className="preview-header">
        <span className="brand-avatar" />
        <span className="brand-name">{brandName}</span>
      </div>
      {image && <img src={image} className="preview-image" style={{ aspectRatio: '1.91/1' }} />}
      <p className="preview-caption">
        {expanded || !isFolded ? caption : caption.slice(0, foldAt)}
        {isFolded && !expanded && (
          <button onClick={() => setExpanded(true)} className="see-more">...see more</button>
        )}
      </p>
      <div className="char-count">{caption.length} / {PLATFORM_LIMITS.linkedin.captionMax}</div>
      {isFolded && (
        <div className="fold-indicator">
          ⚠️ First {foldAt} characters appear above fold — hook must be here
        </div>
      )}
    </div>
  );
};

const XPreview: React.FC<{ caption: string }> = ({ caption }) => {
  const overLimit = caption.length > PLATFORM_LIMITS.x.captionMax;
  return (
    <div className="x-preview">
      <p className={overLimit ? "caption-over-limit" : ""}>
        {overLimit ? caption.slice(0, 277) + "..." : caption}
      </p>
      <div className={`char-count ${overLimit ? "over" : ""}`}>
        {caption.length} / {PLATFORM_LIMITS.x.captionMax}
        {overLimit && " ⚠️ Will be truncated"}
      </div>
    </div>
  );
};

const InstagramPreview: React.FC<{ caption: string; image?: string }> = ({ caption, image }) => (
  <div className="instagram-preview">
    {image && <img src={image} className="preview-image" style={{ aspectRatio: '1/1' }} />}
    <p className="preview-caption">{caption}</p>
    <div className="hashtag-count">
      {(caption.match(/#/g) || []).length} / {PLATFORM_LIMITS.instagram.hashtagMax} hashtags
    </div>
  </div>
);

// Platform preview switcher on ContentDetail page
const PlatformPreview: React.FC<{ platform: string; caption: string; image?: string }> = (props) => {
  switch (props.platform) {
    case "linkedin": return <LinkedInPreview {...props} />;
    case "x": return <XPreview {...props} />;
    case "instagram": return <InstagramPreview {...props} />;
    default: return <GenericPreview {...props} />;
  }
};
```

**Component tree update:**
```
├── ContentDetail
│   ├── PlatformPreview (NEW — shows how post appears on target platform)
│   │   ├── LinkedInPreview (character count, "see more" fold, 1.91:1 image crop)
│   │   ├── XPreview (280 char limit, truncation warning)
│   │   ├── InstagramPreview (square crop, hashtag count)
│   │   └── TikTokPreview (caption + video frame)
│   ├── CaptionText
│   └── CopyButton
```

No backend changes. No Firestore changes. Pure frontend.

---

### 12.1.3 Content Editing & Regeneration (Sprint 4)

**Effort:** 1–2 days | **Type:** New endpoint + frontend

**Backend — Single post regeneration:**
```python
@app.post("/api/content/{plan_id}/day/{day_index}/regenerate")
async def regenerate_single_post(plan_id: str, day_index: int, 
                                  edit_instructions: str = None):
    """Regenerate a single day's content without regenerating the full week."""
    db = firestore.client()
    plan_ref = db.collection("plans").document(plan_id)
    plan = plan_ref.get().to_dict()
    brand_id = plan["brand_id"]
    
    brand_ref = db.collection("brands").document(brand_id)
    brand = brand_ref.get().to_dict()
    
    day = plan["days"][day_index]
    
    # Build context from brand + strategy for this specific day
    context = {
        "brand_profile": brand,
        "day_strategy": day,  # pillar, platform, content_type
        "edit_instructions": edit_instructions,  # Optional: "make it more casual" / "focus on the sale"
    }
    
    # Call Content Creator for just this one post
    result = await content_creator_agent.generate_single_post(context)
    
    # Update Firestore — only this day's content
    plan["days"][day_index]["caption"] = result["caption"]
    plan["days"][day_index]["hashtags"] = result["hashtags"]
    if result.get("image_url"):
        plan["days"][day_index]["image_url"] = result["image_url"]
    plan["days"][day_index]["regenerated"] = True
    plan["days"][day_index]["regenerated_at"] = firestore.SERVER_TIMESTAMP
    
    plan_ref.update({"days": plan["days"]})
    
    return {"day": plan["days"][day_index]}
```

**Frontend — Inline editing:**
```typescript
const EditableCaption: React.FC<{ caption: string; onSave: (text: string) => void }> = ({ caption, onSave }) => {
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState(caption);
  
  if (!editing) {
    return (
      <div onClick={() => setEditing(true)} className="editable-caption">
        <p>{caption}</p>
        <span className="edit-hint">✏️ Click to edit</span>
      </div>
    );
  }
  
  return (
    <div className="caption-editor">
      <textarea value={text} onChange={e => setText(e.target.value)} />
      <button onClick={() => { onSave(text); setEditing(false); }}>Save</button>
      <button onClick={() => { setText(caption); setEditing(false); }}>Cancel</button>
    </div>
  );
};

// Regenerate button with optional instructions
const RegenerateButton: React.FC<{ planId: string; dayIndex: number }> = ({ planId, dayIndex }) => {
  const [instructions, setInstructions] = useState("");
  const [showInput, setShowInput] = useState(false);
  
  const handleRegenerate = async () => {
    const result = await api.regeneratePost(planId, dayIndex, instructions || undefined);
    // Update local state with new content
  };
  
  return (
    <div>
      <button onClick={() => setShowInput(!showInput)}>🔄 Regenerate</button>
      {showInput && (
        <div className="regen-input">
          <input placeholder="Optional: 'make it funnier' or 'focus on the promotion'" 
                 value={instructions} onChange={e => setInstructions(e.target.value)} />
          <button onClick={handleRegenerate}>Go</button>
        </div>
      )}
    </div>
  );
};
```

---

### 12.1.4 Competitor Visibility Toggle (Sprint 4)

**Effort:** 2–3 hours | **Type:** Frontend only

```typescript
// Add to BrandProfileCard
const CompetitorSection: React.FC<{ competitors: Competitor[] }> = ({ competitors }) => {
  const [visible, setVisible] = useState(true);  // Default visible
  
  return (
    <div className="competitor-section">
      <div className="section-header">
        <h3>Competitor Landscape</h3>
        <ToggleSwitch checked={visible} onChange={setVisible} label={visible ? "Showing" : "Hidden"} />
      </div>
      {visible && (
        <div className="competitor-grid">
          {competitors.map(c => <CompetitorCard key={c.name} {...c} />)}
        </div>
      )}
    </div>
  );
};
```

**Firestore schema addition:**
```
brands/{brandId}/
  ├── ui_preferences: {
  │     show_competitors: true   # NEW — user toggle
  │   }
```

Competitor data is always extracted during brand analysis (it informs content strategy). The toggle only affects the user-facing display.

---

### 12.1.5 AI Image Quality Validation (Sprint 5)

**Effort:** 4–6 hours | **Type:** Prompt change + frontend indicator

**Brand Analyst prompt addition:**
```
INDUSTRY RISK ASSESSMENT:
After inferring the business type, assess AI image generation risk:
- HIGH RISK (recommend BYOP): food photography, fashion, real estate, jewelry, 
  automotive, cosmetics — industries where bad AI images are worse than no images
- MEDIUM RISK: fitness, travel, education — AI images acceptable but user photos preferred
- LOW RISK: SaaS, consulting, coaching, finance — abstract/graphic images work well

Output a new field:
  "image_generation_risk": "high" | "medium" | "low"
  "byop_recommendation": "We recommend using your own photos for food content — 
    AI-generated food photography can look unappetizing. Upload your best shots 
    and we'll write perfect captions."
```

**Frontend — Quality confidence indicator:**
```typescript
const ImageQualityIndicator: React.FC<{ risk: string; contentType: string }> = ({ risk, contentType }) => {
  if (risk === "high" && contentType === "photo") {
    return (
      <div className="quality-warning">
        ⚠️ AI image quality may be limited for {industry}. 
        <strong>Upload your own photos</strong> for best results.
        <ToggleSwitch label="Caption-only mode" />
      </div>
    );
  }
  return null;
};
```

**Firestore schema addition:**
```
brands/{brandId}/
  ├── image_generation_risk: "high" | "medium" | "low"  # NEW
  ├── byop_recommendation: "..."                          # NEW
```

---

### 12.1.6 Description-First Onboarding Option (Sprint 5)

**Effort:** 3–4 hours | **Type:** Frontend flow change + A/B test

```typescript
// Two onboarding modes — A/B tested

// Mode A (current): URL primary, description secondary
// Mode B (new): Description primary, URL as optional enhancement

const OnboardPage: React.FC<{ variant: "url_first" | "description_first" }> = ({ variant }) => {
  if (variant === "description_first") {
    return (
      <div className="onboard">
        <h2>Tell us about your business</h2>
        <DescriptionInput required minLength={20} />
        <AssetUploadZone optional />
        <CollapsibleSection label="Have a website? Paste it for even better results">
          <URLInput optional />
        </CollapsibleSection>
        <AnalyzeButton />
      </div>
    );
  }
  
  // Mode A: existing flow
  return (
    <div className="onboard">
      <URLInput />
      <NoWebsiteToggle />
      <DescriptionInput />
      <AssetUploadZone />
      <AnalyzeButton />
    </div>
  );
};
```

**Analytics event:** Track conversion rate per variant:
```python
# POST /api/analytics/onboard
{
  "variant": "description_first",
  "completed": true,
  "had_url": false,
  "had_assets": true,
  "time_to_complete_ms": 45000
}
```

No backend API changes — the `POST /api/brands` endpoint already accepts `description` (required) and `website_url` (optional).

---

### 12.1.7 Multi-Platform Formatting (Sprint 5)

**Effort:** 1–2 days | **Type:** Prompt engineering per platform

**Content Creator prompt update — platform-specific generation:**
```python
PLATFORM_PROMPTS = {
    "instagram": """
    FORMAT: Instagram caption. 
    - Hook in first line (appears above fold)
    - 2-3 short paragraphs with line breaks
    - Call to action (comment, save, share)
    - 20-30 relevant hashtags at the end
    - Emoji use: moderate, on-brand
    Max: 2200 characters
    """,
    "linkedin": """
    FORMAT: LinkedIn post.
    - Strong opening hook (first 140 chars appear above "see more")
    - Professional but personable tone
    - 3-5 short paragraphs
    - End with a question or CTA to drive comments
    - 3-5 hashtags maximum (LinkedIn penalizes more)
    - No emoji overuse — 1-2 per post max
    Max: 3000 characters
    """,
    "x": """
    FORMAT: X (Twitter) post.
    - Concise, punchy, conversational
    - One clear idea per post
    - Thread format if content needs more than 280 chars (indicate with 🧵)
    - 1-3 hashtags integrated naturally (not appended)
    Max: 280 characters per tweet
    """,
    "tiktok": """
    FORMAT: TikTok caption.
    - Ultra-casual, trend-aware
    - Hook immediately — first 3 words matter most
    - Hashtags mixed with trending tags
    - CTA: "Follow for more" or "Save this for later"
    Max: 2200 characters
    """,
    "facebook": """
    FORMAT: Facebook post.
    - Conversational, community-oriented
    - Ask questions to drive comments
    - Longer form acceptable
    - 1-3 hashtags or none
    - Emoji use: moderate
    """,
}
```

**Integration:** The Strategy Agent already assigns a platform per day. When the Content Creator generates each post, it receives the corresponding `PLATFORM_PROMPTS[platform]` fragment prepended to the generation prompt. This is a prompt change, not architecture.

---

### 12.1.8 Engagement Prediction Scoring (Sprint 6)

**Effort:** 3–5 days | **Type:** New tool on Review Agent

```python
# Add to Review Agent tools

@tool
def predict_engagement(caption: str, platform: str, brand_profile: dict, 
                       image_description: str = None) -> dict:
    """Predict engagement potential for a post. Returns score and reasoning.
    
    Scoring rubric (heuristic v1 — replace with ML model when data available):
    - Hook strength (0-25): Does the first line grab attention?
    - Relevance (0-25): Does content match audience interests?
    - CTA effectiveness (0-20): Clear call-to-action that drives interaction?
    - Visual appeal (0-15): Image/video quality and relevance?
    - Platform fit (0-15): Optimized for this specific platform's algorithm?
    """
    prompt = f"""Score this social media post for predicted engagement.
    
    Platform: {platform}
    Brand audience: {brand_profile.get('target_audience')}
    Brand tone: {brand_profile.get('tone')}
    Caption: {caption}
    Image: {image_description or 'No image description available'}
    
    Score each dimension 0-100 and provide one-sentence reasoning:
    1. Hook strength (weight: 25%)
    2. Audience relevance (weight: 25%)
    3. CTA effectiveness (weight: 20%)
    4. Visual appeal (weight: 15%)
    5. Platform optimization (weight: 15%)
    
    Return JSON: {{
      "overall_score": 0-100,
      "dimensions": {{
        "hook": {{"score": N, "reasoning": "..."}},
        "relevance": {{"score": N, "reasoning": "..."}},
        "cta": {{"score": N, "reasoning": "..."}},
        "visual": {{"score": N, "reasoning": "..."}},
        "platform_fit": {{"score": N, "reasoning": "..."}}
      }},
      "improvement_suggestions": ["...", "..."]
    }}
    """
    
    response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
    return json.loads(response.text)
```

**Firestore schema addition:**
```
plans/{planId}/days[N]/
  ├── engagement_prediction: {
  │     overall_score: 78,
  │     dimensions: { hook: {score: 85, reasoning: "..."}, ... },
  │     improvement_suggestions: ["Add a question to drive comments", ...]
  │   }
```

**Frontend:** Show engagement score as a colored badge on each calendar day card (green 80+, yellow 60-79, red <60). Tap to expand full breakdown.

---

### 12.1.9 Social Media Voice Analysis (Sprint 6)

**Effort:** 3–5 days | **Type:** OAuth integrations + new input pipeline

**Frontend — Per-platform demo voice data:** The SocialConnect component includes built-in demo voice data (`DEMO_VOICE_ANALYSES: Record<string, VoiceAnalysis>`) so users can preview the voice analysis workflow without connecting a real account. Each platform card has a "try demo" link (visible when `!connected && !expanded`) that loads platform-appropriate sample data:
- **LinkedIn:** Authoritative B2B coaching voice — no emoji, long-form (250-400 words), tone: candid, specific, no-nonsense
- **Instagram:** Warm artisanal lifestyle — moderate emoji, medium-form, tone: warm, authentic, enthusiastic
- **X:** Punchy hot-take style — minimal emoji, short-form (under 280 chars), tone: sharp, opinionated, provocative

Demo data is wired via `onLoadDemo` prop: `onLoadDemo={DEMO_VOICE_ANALYSES[key] ? () => handleConnected(key, DEMO_VOICE_ANALYSES[key]) : undefined}`. The `hasAnyActive` banner check covers all four voice-analysis data sources: connected platforms array, session-local analyses, `existingVoiceAnalyses` prop (server-stored), and `existingVoiceAnalysis` + platform pair.

**Backend — OAuth flow (for real account connection):**

```python
# New endpoint for connecting social accounts
@app.post("/api/brands/{brand_id}/connect-social")
async def connect_social_account(brand_id: str, platform: str, oauth_token: str):
    """Connect a social media account for voice analysis."""
    # Platform-specific API calls
    if platform == "linkedin":
        posts = await fetch_linkedin_posts(oauth_token, limit=50)
    elif platform == "instagram":
        posts = await fetch_instagram_posts(oauth_token, limit=50)
    elif platform == "x":
        posts = await fetch_x_posts(oauth_token, limit=50)
    
    # Analyze voice patterns
    voice_analysis = await analyze_social_voice(posts)
    
    # Update brand profile with social voice data
    db = firestore.client()
    db.collection("brands").document(brand_id).update({
        "social_voice_analysis": voice_analysis,
        "connected_platforms": firestore.ArrayUnion([platform])
    })
    
    return voice_analysis

async def analyze_social_voice(posts: list[dict]) -> dict:
    """Use Gemini to analyze writing patterns from existing posts."""
    post_texts = "\n---\n".join([p["text"] for p in posts[:30]])
    
    prompt = f"""Analyze these social media posts and extract the writer's voice:
    
    {post_texts}
    
    Return JSON:
    {{
      "voice_characteristics": ["conversational", "uses humor", "asks questions"],
      "common_phrases": ["here's the thing", "let me explain"],
      "emoji_usage": "moderate" | "heavy" | "minimal" | "none",
      "average_post_length": N,
      "successful_patterns": ["posts with questions get 2x engagement", ...],
      "tone_adjectives": ["warm", "authoritative", "playful"]
    }}
    """
    
    response = await client.aio.models.generate_content(model="gemini-2.5-flash", contents=prompt)
    return json.loads(response.text)
```

**Brand Analyst integration:** When `social_voice_analysis` exists on a brand, the Brand Analyst includes it in context:
```
The user's existing social media voice has been analyzed:
Voice characteristics: {voice_characteristics}
Common phrases: {common_phrases}
Successful patterns: {successful_patterns}

IMPORTANT: Generated content should match this existing voice, not replace it.
```

---

### 12.1.10 Platform Meta Intelligence (Sprint 6)

**Effort:** 2–3 days | **Type:** Data pipeline + Strategy Agent tool

```python
# New tool for Strategy Agent

@tool
def research_platform_trends(platform: str, industry: str) -> dict:
    """Research current trending content patterns for a platform + industry.
    
    Uses Gemini with web search grounding to find current best practices.
    """
    prompt = f"""Research the current trending content patterns on {platform} 
    for the {industry} industry.
    
    What's working right now (this week/month)?
    - Trending formats (carousel, short video, text post, etc.)
    - Trending topics or hooks
    - Algorithm preferences (what's being boosted?)
    - Posting time recommendations
    
    Return JSON: {{
      "trending_formats": ["carousel", "behind-the-scenes reels"],
      "trending_hooks": ["hot takes", "myth-busting", "day-in-the-life"],
      "algorithm_notes": "LinkedIn is boosting document posts and polls this month",
      "best_posting_times": ["Tue 8am", "Thu 12pm"],
      "freshness": "2026-02-22"
    }}
    """
    
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=genai.types.GenerateContentConfig(
            tools=[genai.types.Tool(google_search=genai.types.GoogleSearch())]
        )
    )
    return json.loads(response.text)
```

**Caching:** Trend data is cached in Firestore per platform+industry for 7 days. Strategy Agent checks cache before making a new research call.

```
platform_trends/{platform}_{industry}/
  ├── data: { ... trend JSON ... }
  ├── fetched_at: timestamp
  ├── expires_at: timestamp + 7 days
```

---

### 12.1.11 Instagram Grid Visual Consistency (Sprint 6)

**Effort:** 2–3 days | **Type:** Style reference image + Content Creator update

```python
# During brand analysis, generate a "style reference image"

async def generate_style_reference(brand_profile: dict) -> str:
    """Generate a reference image that captures the brand's visual identity.
    Used as context for every subsequent image generation call."""
    
    prompt = f"""Generate a style reference image for a brand with these characteristics:
    Colors: {brand_profile['colors']}
    Tone: {brand_profile['tone']}  
    Industry: {brand_profile['business_type']}
    Style directive: {brand_profile.get('image_style_directive', 'modern, clean')}
    
    This is NOT a real post — it's a visual reference showing:
    - The brand's color palette applied to a simple composition
    - The lighting style (warm/cool/natural)
    - The texture and mood (minimal/rich/rustic)
    - The typography style if applicable
    
    Generate a single cohesive image that a designer could use as a mood board reference.
    """
    
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=genai.types.GenerateContentConfig(response_modalities=["IMAGE"])
    )
    
    # Upload style reference to GCS
    for part in response.candidates[0].content.parts:
        if part.inline_data:
            blob = bucket.blob(f"brands/{brand_id}/style_reference.png")
            blob.upload_from_string(part.inline_data.data, content_type="image/png")
            return blob.public_url
    
    return None

# Content Creator update — pass style reference with every image generation
# In the Content Creator prompt for Mode A (AI-generated images):
"""
VISUAL CONSISTENCY:
Reference this style image for color palette, lighting, and mood: {style_reference_url}
Every image you generate should feel like it belongs in the same Instagram grid 
as this reference. Match the warmth, saturation, and composition style.
"""
```

**Firestore schema addition:**
```
brands/{brandId}/
  ├── style_reference_url: "gs://..."   # NEW
```

---

### 12.1.12 Video Repurposing / Smart Editing (Sprint 7+)

**Effort:** 1–2 weeks | **Type:** New agent + async processing pipeline + FFmpeg integration

User uploads raw video (up to 5 min, .mp4/.mov). Amplifi produces 2–3 platform-ready short-form clips with auto-generated captions.

**New endpoint — Upload raw video:**
```python
@app.post("/api/brands/{brand_id}/video")
async def upload_raw_video(brand_id: str, file: UploadFile = File(...)):
    """Upload raw video for repurposing. Triggers async processing."""
    # Validate: max 500MB, .mp4 or .mov only
    if file.size > 500 * 1024 * 1024:
        raise HTTPException(413, "Video must be under 500MB")
    if not file.filename.lower().endswith(('.mp4', '.mov')):
        raise HTTPException(400, "Only .mp4 and .mov files accepted")
    
    # Upload to GCS
    video_id = str(uuid.uuid4())
    gcs_path = f"brands/{brand_id}/raw_video/{video_id}/{file.filename}"
    upload_to_gcs(gcs_path, await file.read())
    
    # Create processing job record
    db = firestore.client()
    db.collection("video_jobs").document(video_id).set({
        "brand_id": brand_id,
        "status": "queued",
        "source_url": f"gs://{GCS_BUCKET}/{gcs_path}",
        "created_at": firestore.SERVER_TIMESTAMP,
        "clips": [],  # Populated by processor
    })
    
    # Trigger async processing via Cloud Tasks or Pub/Sub
    enqueue_video_processing(video_id, brand_id, gcs_path)
    
    return {"video_id": video_id, "status": "processing"}
```

**New endpoint — Check job status / get clips:**
```python
@app.get("/api/video/{video_id}")
async def get_video_status(video_id: str):
    """Poll processing status. Returns clips when ready."""
    db = firestore.client()
    job = db.collection("video_jobs").document(video_id).get().to_dict()
    return {
        "status": job["status"],  # queued | processing | complete | failed
        "clips": job.get("clips", []),
        "error": job.get("error"),
    }
```

**Async processing pipeline (Cloud Run Job or Cloud Tasks handler):**
```python
class VideoEditorAgent:
    """New agent — activated only for user-uploaded video repurposing."""
    
    async def process_video(self, video_id: str, brand_id: str, source_url: str):
        db = firestore.client()
        db.collection("video_jobs").document(video_id).update({"status": "processing"})
        
        # Step 1: Download from GCS and extract audio
        video_path = download_from_gcs(source_url)
        audio_path = extract_audio(video_path)  # FFmpeg: ffmpeg -i input.mp4 -vn audio.wav
        
        # Step 2: Transcribe via Gemini
        transcript = await self.transcribe(audio_path)
        # Returns: [{"start": 0.0, "end": 3.2, "text": "So today I want to talk about..."}, ...]
        
        # Step 3: Analyze content for highlights
        brand_profile = db.collection("brands").document(brand_id).get().to_dict()
        
        analysis_prompt = f"""Analyze this video transcript for a {brand_profile.get('description', 'business')} 
        that posts on social media. Brand tone: {brand_profile.get('tone', 'professional')}.
        
        Transcript (with timestamps):
        {json.dumps(transcript)}
        
        Identify the TOP 3 clip-worthy moments. For each, provide:
        - start_time: float (seconds)
        - end_time: float (seconds) 
        - platform: best target platform ("reels" | "tiktok" | "linkedin" | "youtube_shorts")
        - hook: the opening line/moment that grabs attention
        - reason: why this moment is compelling (key insight, emotional beat, quotable line)
        - suggested_caption: a caption in the brand's voice style
        
        Platform constraints:
        - Reels/TikTok: 15-60 seconds, hook in first 3 seconds
        - LinkedIn: 30-90 seconds, insight-driven
        - YouTube Shorts: 15-60 seconds, high energy
        
        Return as JSON array sorted by engagement potential.
        """
        
        response = await generate_content(analysis_prompt)
        clip_specs = json.loads(response.text)
        
        # Step 4: Extract clips via FFmpeg
        clips = []
        for i, spec in enumerate(clip_specs[:3]):
            clip_filename = f"clip_{i+1}_{spec['platform']}.mp4"
            clip_path = f"/tmp/{video_id}/{clip_filename}"
            
            # FFmpeg clip extraction
            extract_clip(
                input_path=video_path,
                output_path=clip_path,
                start=spec["start_time"],
                end=spec["end_time"],
            )
            
            # Step 5: Add caption overlay
            captioned_path = add_captions(
                clip_path=clip_path,
                transcript=get_segment(transcript, spec["start_time"], spec["end_time"]),
                style=brand_profile.get("caption_style", "default"),
            )
            
            # Step 6: Platform-specific formatting
            formatted_path = format_for_platform(
                clip_path=captioned_path,
                platform=spec["platform"],
                # Reels/TikTok: 9:16 vertical
                # LinkedIn: 1:1 or 16:9
                # YouTube Shorts: 9:16 vertical
            )
            
            # Upload to GCS
            gcs_clip_path = f"brands/{brand_id}/clips/{video_id}/{clip_filename}"
            upload_to_gcs(gcs_clip_path, open(formatted_path, "rb").read())
            
            clips.append({
                "clip_url": f"gs://{GCS_BUCKET}/{gcs_clip_path}",
                "platform": spec["platform"],
                "duration_seconds": spec["end_time"] - spec["start_time"],
                "hook": spec["hook"],
                "suggested_caption": spec["suggested_caption"],
                "start_time": spec["start_time"],
                "end_time": spec["end_time"],
            })
        
        # Update job status
        db.collection("video_jobs").document(video_id).update({
            "status": "complete",
            "clips": clips,
            "completed_at": firestore.SERVER_TIMESTAMP,
        })
```

**FFmpeg utility functions:**
```python
import subprocess

def extract_audio(video_path: str) -> str:
    audio_path = video_path.replace(".mp4", ".wav").replace(".mov", ".wav")
    subprocess.run([
        "ffmpeg", "-i", video_path, "-vn", "-acodec", "pcm_s16le", 
        "-ar", "16000", "-ac", "1", audio_path
    ], check=True)
    return audio_path

def extract_clip(input_path: str, output_path: str, start: float, end: float):
    subprocess.run([
        "ffmpeg", "-i", input_path, "-ss", str(start), "-to", str(end),
        "-c:v", "libx264", "-c:a", "aac", "-y", output_path
    ], check=True)

def add_captions(clip_path: str, transcript: list, style: str = "default") -> str:
    """Burn-in captions using FFmpeg subtitles filter."""
    srt_path = clip_path.replace(".mp4", ".srt")
    generate_srt(transcript, srt_path)
    output_path = clip_path.replace(".mp4", "_captioned.mp4")
    
    # Style presets
    font_size = {"default": 24, "bold": 28, "minimal": 20}[style]
    subprocess.run([
        "ffmpeg", "-i", clip_path, "-vf",
        f"subtitles={srt_path}:force_style='FontSize={font_size},PrimaryColour=&HFFFFFF,Outline=2'",
        "-c:a", "copy", "-y", output_path
    ], check=True)
    return output_path

def format_for_platform(clip_path: str, platform: str) -> str:
    """Crop/pad to platform aspect ratio."""
    output_path = clip_path.replace(".mp4", f"_{platform}.mp4")
    aspect = {
        "reels": "9:16", "tiktok": "9:16", "youtube_shorts": "9:16",
        "linkedin": "1:1",
    }.get(platform, "16:9")
    
    w, h = {"9:16": (1080, 1920), "1:1": (1080, 1080), "16:9": (1920, 1080)}[aspect]
    subprocess.run([
        "ffmpeg", "-i", clip_path, "-vf",
        f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:black",
        "-c:a", "copy", "-y", output_path
    ], check=True)
    return output_path
```

**Firestore schema:**
```
video_jobs/{videoId}/
  ├── brand_id: "brand_xyz"
  ├── status: "queued" | "processing" | "complete" | "failed"
  ├── source_url: "gs://bucket/brands/brand_xyz/raw_video/..."
  ├── created_at: timestamp
  ├── completed_at: timestamp | null
  ├── error: string | null
  ├── clips: [
  │     {
  │       clip_url: "gs://bucket/brands/brand_xyz/clips/...",
  │       platform: "reels",
  │       duration_seconds: 28.5,
  │       hook: "The biggest mistake I see new founders make...",
  │       suggested_caption: "Stop doing this one thing...",
  │       start_time: 42.0,
  │       end_time: 70.5
  │     }
  │   ]
```

**Frontend component tree addition:**
```
├── ContentDetail
│   ├── ... (existing)
│   ├── UploadVideoButton (NEW — appears alongside BYOP photo upload)
│   ├── VideoProcessingIndicator (NEW — shows "Analyzing your video..." with progress)
│   └── ClipPreviewCarousel (NEW — shows 2-3 clip options with:
│       ├── VideoPlayer (trimmed clip with caption overlay preview)
│       ├── PlatformBadge (which platform this clip is optimized for)
│       ├── HookPreview (the opening line that hooks viewers)
│       ├── CaptionEditor (edit suggested caption before export)
│       └── DownloadClipButton
│       )
```

**Docker dependency:** FFmpeg must be installed in the Cloud Run container image:
```dockerfile
# Add to Dockerfile
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*
```

**Processing notes:**
- Processing is ASYNC — not in the request path. Upload returns immediately with a job ID.
- Client polls `GET /api/video/{video_id}` every 5 seconds until status = "complete".
- Processing time estimate: 30–90 seconds for a 3-minute video (dominated by Gemini transcription + analysis).
- Cloud Run jobs have a 60-minute timeout — sufficient for 5-minute videos.
- If processing fails, status is set to "failed" with error message. Client shows retry button.

---

# 13. Environment Variable Manifest

| Variable | Required | Description | Example |
|---|---|---|---|
| `GOOGLE_CLOUD_PROJECT` | ✓ | GCP project ID | `amplifi-hackathon-2026` |
| `GEMINI_API_KEY` | ✓ | Gemini API key (or use ADC) | `AIzaSy...` |
| `GCS_BUCKET` | ✓ | Cloud Storage bucket for brand assets + generated images | `amplifi-hackathon-2026-amplifi-assets` |
| `FIRESTORE_DATABASE` | | Firestore database ID (default: `(default)`) | `(default)` |
| `PORT` | | Server port (Cloud Run provides this) | `8080` |
| `BUDGET_LIMIT_USD` | | Override budget cap (default: `100`) | `80` |

```bash
# .env.example
GOOGLE_CLOUD_PROJECT=amplifi-hackathon-2026
GEMINI_API_KEY=your-api-key-here
GCS_BUCKET=amplifi-hackathon-2026-amplifi-assets
FIRESTORE_DATABASE=(default)
PORT=8080
BUDGET_LIMIT_USD=100
```

---

# 14. Architectural Differences from Fireside

For engineers working on both projects, here is a comparison of the key architectural differences:

| Dimension | Fireside — Betrayal | Amplifi |
|---|---|---|
| **Primary API** | Gemini Live API (WebSocket, bidirectional) | Gemini generateContent (REST, unidirectional) |
| **Transport** | WebSocket (persistent, multiplayer) | REST + SSE (stateless, single user) |
| **Response Modality** | AUDIO (native voice) | TEXT + IMAGE (interleaved) + VIDEO (Veo 3.1, P1) |
| **Model** | gemini-2.5-flash-native-audio-preview-12-2025 | gemini-2.5-flash + veo-3.1-fast-generate-preview |
| **Agent Architecture** | Narrator (LLM) + Game Master (deterministic) + Traitor (LLM) | Sequential pipeline: Analyst → Strategy → Creator → Review |
| **Session Management** | Persistent (10+ min, session resumption required) | Stateless per request (no session management needed) |
| **Cloud Run Config** | Session affinity ON, 3600s timeout, WebSocket | No session affinity needed, 300s timeout, HTTP |
| **Firestore Role** | Real-time game state (players, votes, phases) | Persistent content storage (brands, plans, posts) |
| **Cloud Storage Role** | Scene images (stretch goal) | Core feature — all generated images |
| **Frontend** | Mobile-first PWA, audio playback, real-time updates | Dashboard, SSE streaming, image gallery |
| **Concurrent Users** | 3–6 players per game, 1 game at a time (demo) | 1 user at a time (demo) |
| **Budget Concern** | Minimal (voice is cheap) | Moderate (~$0.039/image, tracked) |

---

# 15. Post-Hackathon Architecture Migration

This section catalogs every architectural decision made for the 3-week hackathon that will NOT survive contact with real users at scale. These are not bugs — they are intentional shortcuts that need planned migrations.

**Severity Levels:**
- 🔴 **Breaking** — Stops working entirely at scale. Must fix before any public launch.
- 🟡 **Degraded** — Works but poorly. Users will notice. Fix within first month.
- 🟢 **Technical Debt** — Works fine but limits future features. Fix when convenient.

## 15.1 🔴 Single-Container Monolith → Microservices

**Hackathon:** One Docker container runs FastAPI + React + all 4 ADK agents in-process (§8.1). Single Cloud Run service.

**Why it breaks:** A content generation request (Brand Analyst → Strategy → Content Creator → Review) holds a Cloud Run instance for 30-60 seconds while 4 sequential LLM calls complete. The Content Creator with interleaved output blocks for 10-20 seconds per post; generating 7 posts = 70-140 seconds of wall-clock time per user. At 50 concurrent users generating weekly calendars, you need ~50 warm Cloud Run instances each burning CPU while waiting on Gemini API responses.

**Migration:**

```
HACKATHON                           PRODUCTION
┌─────────────────────────┐         ┌──────────┐  ┌──────────┐  ┌───────────┐
│ Cloud Run (1 container) │         │Firebase  │  │API       │  │Agent      │
│ React + FastAPI + ADK   │   →     │Hosting   │  │Gateway   │  │Workers    │
│ + SSE + Budget (memory) │         │(static)  │  │(stateless│  │(Cloud Run │
└─────────────────────────┘         └──────────┘  │ + auth)  │  │ Jobs)     │
                                                  └────┬─────┘  └────┬──────┘
                                                       │             │
                                                  Cloud Tasks ───────┘
                                                  (job queue)
```

- Split into 3 services: Frontend (Firebase Hosting / CDN), API Gateway (stateless Cloud Run), Agent Workers (Cloud Run Jobs — no request timeout, billed per vCPU-second)
- Generation requests enqueue via Cloud Tasks; workers pull and process
- Video generation (§6.4) already uses this async job pattern — extend it to all generation

**Effort:** 2-3 weeks.

## 15.2 🔴 Gemini API Rate Limits — The Hard Ceiling

**Hackathon:** Direct Gemini API calls from a single GCP project. Every agent call = 1 API request.

**Why it breaks:** Gemini 2.5 Flash on Paid Tier 1: ~150 RPM. A single user's full calendar generation = 16 API calls (1 brand analysis + 1 strategy + 7 content generations + 7 reviews). Maximum concurrent full-calendar generations before 429 errors: **~9 users**. This is not a scale problem — it's a "10th customer gets an error" problem.

Interleaved output (TEXT + IMAGE) requests are computationally expensive and may hit TPM (tokens per minute) limits before RPM. Image generation has its own IPM cap. Veo has even stricter quotas.

**Migration:**
- Request queue with priority + position tracking ("You are #3 in line" instead of 429 error)
- Vertex AI provisioned throughput (enterprise quotas, SLA) instead of AI Studio API keys
- Aggressive caching: identical brand analysis for the same URL hits cache, not Gemini
- Pre-generate common content templates during off-peak (Gemini Batch API)
- Multi-project sharding: split users across 2-3 GCP projects to multiply quotas (short-term)

**Effort:** 1-2 weeks for queuing + caching. Vertex AI migration is a config change.

## 15.3 🔴 In-Memory BudgetTracker → Persistent Budget Service

**Hackathon:** `BudgetTracker` (§6.3) is a Python class instance in memory on a single Cloud Run container.

**Why it breaks:** Cloud Run is stateless. Instance scales down → budget resets to zero. Two instances running simultaneously have independent counters — each thinks it has the full $100 budget. 2x overspend without knowing.

**Migration:**
- Firestore atomic increment on a `budget` document per project
- Firestore transactions for check-and-increment (`can_generate` + `record_generation` must be atomic)
- Cloud Monitoring alerts at 50%, 75%, 90% budget thresholds
- Per-user budget isolation (multi-tenant) in Firestore

**Effort:** Half a day. Should be done during hackathon if time allows.

## 15.4 🔴 No Authentication / Single-Tenant → Multi-Tenant with Auth

**Hackathon:** No authentication. One brand, one user. The Firestore schema (§5.1) has no `user_id` scoping on any document.

**Why it breaks:** Adding multi-tenancy retroactively requires restructuring every Firestore path from `brands/{brandId}/...` to `users/{userId}/brands/{brandId}/...` — affecting every query in the codebase.

**Migration:**
- Firebase Authentication (Google Sign-In, email/password)
- Restructure Firestore: `users/{userId}/brands/{brandId}/content_plans/{planId}/days/{dayIndex}/...`
- Firestore security rules scoped to authenticated user
- API middleware: extract `user_id` from Firebase JWT, scope all queries
- Data migration script for existing documents

**Effort:** 1 week. Auth is fast; restructuring Firestore + updating every query is the bulk.

## 15.5 🟡 SSE Streaming → Job Polling

**Hackathon:** Server-Sent Events (§4.2) for generation stream.

**Why it degrades:**
- SSE connections are unidirectional — client can't cancel mid-generation
- Each SSE connection holds a Cloud Run instance active for 30-60 seconds per post
- Connections don't survive Cloud Run instance restarts — client loses all progress
- No reconnection semantics; client must restart generation from scratch

**Migration (recommended: job-based polling):**
- Generation request returns `job_id` immediately
- Client polls `GET /api/jobs/{jobId}` every 2 seconds
- Backend writes generation progress to Firestore in real-time
- This is exactly the video generation pattern (§6.4.3) — extend to all content generation
- Alternative: Firestore `onSnapshot` listeners for real-time push without direct server connection

**Effort:** 3-4 days (pattern already exists in §6.4).

## 15.6 🟡 Sequential Agent Pipeline → Parallel Generation

**Hackathon:** ADK SequentialAgent (§3.1) runs all 4 agents in-process, serially. 7 posts × 15 seconds each = ~2 minutes wall-clock.

**Why it degrades:** Can't parallelize within ADK's SequentialAgent by definition. The entire pipeline blocks. ADK's session management is designed for single-conversation flows, not concurrent multi-user batch workloads. Context window bloats as more agents and data accumulate in the sequence.

**Migration:**
- Replace SequentialAgent with explicit orchestration: FastAPI background task calls each agent individually, stores intermediate results in Firestore
- Parallelize Content Creator: `asyncio.gather()` for all 7 posts simultaneously → generation time drops from ~2 min to ~20 seconds
- ADK context processors to trim unnecessary data between agent stages
- Consider Vertex AI Agent Engine for managed session handling at scale

**Effort:** 1-2 weeks. Parallelization alone delivers 7x speedup for calendar generation.

## 15.7 🟡 Signed URLs (7-day expiry) → CDN + Permanent URLs

**Hackathon:** Generated images served via GCS signed URLs (§5.3) that expire in 7 days.

**Why it degrades:** User returns after 2 weeks — all content images are broken links. Signed URLs aren't CDN-cacheable (unique signatures). Every image request hits GCS directly — no edge caching for distant users.

**Migration:**
- Cloud CDN in front of GCS bucket with public-read objects for generated content
- Permanent deterministic URLs: `https://cdn.amplifi.app/content/{postId}/hero.png`
- Access control at application level (API checks user owns brand before returning URL)

**Effort:** 1-2 days. Mostly configuration.

## 15.8 🟡 No Billing → Stripe Subscriptions

**Hackathon:** Free, unlimited usage funded by $100 Google Cloud credit. Shared global budget.

**Why it degrades:** $100 runs out. One heavy user burns the entire budget. No revenue model.

**Migration:**
- Stripe integration: subscription billing + usage-based metering
- Tiered plans: Free (5 posts/week, no video), Pro ($19/mo, unlimited + 10 videos), Business ($49/mo, team features)
- Per-user budget isolation in Firestore
- Stripe webhook → update user's generation allowance

**Effort:** 1-2 weeks.

## 15.9 🟢 No Social Publishing

**Hackathon:** Generate → download. No scheduling, no publishing, no calendar sync.

**Why this is debt:** Amplifi generates a 7-day calendar but can't schedule posts. Users manually copy captions and upload images to each platform — defeating the "AI creative director" promise.

**Migration:**
- Social media API integrations: Instagram Graph API, X API v2, LinkedIn Marketing API, TikTok API
- Each requires OAuth 2.0 per user per platform + media upload + content policy compliance
- Cloud Scheduler cron job publishes due posts every 15 minutes
- Instagram requires Facebook Page + Business Account; X requires paid API tier for posting

**Effort:** 3-4 weeks for 2-3 platforms (~1 week per platform due to OAuth + media upload quirks).

## 15.10 🟢 No Analytics / Feedback Loop

**Hackathon:** Generate and forget. AI never learns what works for a specific brand.

**Why this is debt:** Strategy Agent makes identical recommendations regardless of past performance. No engagement data = no improvement over time.

**Migration:**
- Pull engagement metrics from social media APIs (requires §15.9)
- Store per-post metrics in Firestore: impressions, likes, comments, shares
- Feedback loop: top-performing posts become few-shot examples in Strategy Agent prompts
- Dashboard: engagement charts, best-performing content types, optimal posting times

**Effort:** 2-3 weeks (after social integrations are complete).

## 15.11 🟢 No Content Library / Asset Management

**Hackathon:** Generated images stored in flat GCS paths. No tagging, search, or reuse.

**Why this is debt:** After 4 weeks, a brand has ~28 images. Users can't search "coffee image from 2 weeks ago" or reuse a high-performing image with a new caption.

**Migration:**
- Firestore media collection with auto-tags (Gemini image analysis), dimensions, performance
- Search endpoint: `GET /api/media?tags=coffee,morning&sort=engagement`
- "Use existing image" option in calendar alongside "Generate new" and "Upload photo"

**Effort:** 1 week.

## 15.12 Migration Priority

| Priority | Item | Effort | Why First |
|---|---|---|---|
| **Week 1** | §15.3 Persistent Budget | 0.5 days | Prevents overspend. Trivial fix. |
| **Week 1** | §15.4 Auth + Multi-Tenant | 1 week | Can't have multiple users without it. |
| **Week 2** | §15.2 Rate Limit Queuing | 1-2 weeks | 10th user gets 429 without it. |
| **Week 2** | §15.7 CDN + Permanent URLs | 1-2 days | Images break after 7 days. |
| **Week 3-4** | §15.1 Microservices Split | 2-3 weeks | Unblocks scaling past ~20 concurrent users. |
| **Week 3-4** | §15.6 Parallel Generation | 1-2 weeks | 7x speedup for core UX. |
| **Week 5-6** | §15.5 Job Polling | 3-4 days | Resilient generation. |
| **Week 5-6** | §15.8 Billing | 1-2 weeks | Revenue. |
| **Month 3+** | §15.9 Social Publishing | 3-4 weeks | Makes this a real product. |
| **Month 3+** | §15.10 Analytics | 2-3 weeks | Makes this a sticky product. |
| **Month 3+** | §15.11 Asset Library | 1 week | Power user quality-of-life. |

**Total estimated effort:** 8-12 weeks to production-ready.

**Key insight:** The core logic survives intact — agent prompts, interleaved output parsing, brand analysis pipeline, Veo integration, BYOP photo flow, pillar-based repurposing. The migration wraps this core in production infrastructure (auth, queuing, billing, CDN, microservices). No rewrites, only re-wiring.

---

*Document created: February 21, 2026*
*Updated: February 23, 2026*
*Companion PRD: prd-amplifi.md v1.1*
*Hackathon deadline: March 16, 2026*