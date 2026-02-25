# ✨ Amplifi

**Your AI creative director. One brand. Infinite content.**

An AI-powered creative director that analyzes your brand and produces complete, ready-to-post social media content packages — captions, images, hashtags, and posting schedules — all generated together in a single interleaved output stream.

## What is this?

Amplifi uses Gemini's interleaved text + image output to generate copy and visuals together in one coherent stream. Paste your website URL (or just describe your business), and get a full week of social media content tailored to your brand, across every platform.

- 🎨 **Brand-aware AI** — extracts your colors, tone, audience, and style automatically with deterministic analysis (temperature 0.15)
- 📅 **Full weekly calendar** — 7 days of content with pillar-based strategy and event integration
- 🖼️ **Interleaved generation** — captions and matching images born together via Gemini, with automatic fallback if interleaved mode fails to produce an image
- 📱 **Multi-platform** — Instagram, LinkedIn, X, TikTok, Facebook with platform-specific caption lengths and hashtag counts
- 📸 **Bring your own photos** — upload product shots, get tailored captions
- 🎠 **Instagram carousels** — 3-slide carousel posts with parallel image generation per slide
- 🎬 **AI video** — generate Reels/TikTok clips via Veo 3.1, viewable on saved posts (collapses for text-first platforms)
- 🗣️ **Voice coach** — multi-turn Gemini Live sessions with auto-reconnect and graceful close
- 🔐 **Anonymous auth** — Firebase Anonymous Auth links brands to a persistent UID across sessions
- 📋 **Full export** — "Copy All" clipboard, per-post ZIP download (image + video + caption), bulk plan ZIP with all media
- 🔍 **Auto-review** — AI checks every post against your brand for tone, platform rules, and engagement potential; auto-cleans hashtags
- 🎯 **Platform previews** — live character counts, "see more" fold indicators, and platform-specific formatting

## How it works

1. **Paste your URL** — Amplifi crawls your site and extracts your brand DNA. No website? Just describe your business.
2. **AI builds your brand** — Colors, tone, audience, competitors, style directives — all editable.
3. **Get your week** — Watch as a 7-day content calendar streams in live, post by post.

## Tech Stack

- **AI Engine:** Google Gemini 2.5 Flash (interleaved text + image output)
- **Voice:** Gemini Live API (BidiGenerateContent) for multi-turn voice coaching
- **Agent Framework:** Google ADK (Agent Development Kit)
- **Backend:** FastAPI on Cloud Run
- **Auth:** Firebase Anonymous Auth (persistent UID, zero-friction)
- **Database:** Cloud Firestore
- **Storage:** Cloud Storage (generated images, videos + uploads)
- **Video:** Veo 3.1 (AI-generated Reels/TikTok clips)
- **Frontend:** React 19 + TypeScript + Vite 7
- **Deployment:** Terraform + Cloud Build (CI/CD)

## Architecture

```
User Browser (React 19) ←REST + SSE→ Cloud Run (FastAPI)
                                       ├── ADK Sequential Pipeline
                                       │   ├── Brand Analyst Agent (temp 0.15)
                                       │   ├── Strategy Agent
                                       │   ├── Content Creator Agent (interleaved output)
                                       │   │   ├── Carousel: 3-slide parallel image gen
                                       │   │   └── Fallback: image-only retry on failure
                                       │   └── Review Agent (auto-clean hashtags)
                                       ├── Voice Coach (Gemini Live — BidiGenerateContent)
                                       ├── Video Creator (Veo 3.1)
                                       ├── Firebase Anonymous Auth (persistent UID)
                                       ├── Gemini API (generateContent)
                                       │   └── responseModalities: ["TEXT", "IMAGE"]
                                       ├── Cloud Firestore (brands, plans, posts)
                                       └── Cloud Storage (images, videos, assets)
```

See the full [architecture diagram](docs/architecture.mermaid) for agent interactions and data flows.

## Documentation

| Document | Description |
|---|---|
| [Product Requirements (PRD)](docs/PRD.md) | Full product spec — 7 P0, 9 P1, 12 P2, 2 P3 features. All P0 and P1 shipped; P2 export, preview, and review features shipped. |
| [Technical Design (TDD)](docs/TDD.md) | Implementation spec — 3,200+ lines covering all P0/P1 + shipped P2 features + persona-driven UX improvements |
| [Architecture Diagram](docs/architecture.mermaid) | Mermaid diagram — full agent pipeline, supporting agents, GCP services, and data flows |
| [UI Mockup](docs/amplifi-ui.jsx) | Interactive React prototype — 6 screens (Landing, Onboard, Brand, Calendar, Content, Dashboard) |

## Hackathon

Built for the **Gemini Live Agent Challenge** hackathon ($80K prize pool, Google DeepMind / Devpost).

- **Category:** ✍️ Creative Storyteller
- **Deadline:** March 16, 2026 at 5:00 PM PDT
- **Prize Target:** $10K (category) + $5K (subcategory)

## License

MIT
