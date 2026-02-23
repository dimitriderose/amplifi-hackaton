# ✨ Amplifi

**Your AI creative director. One brand. Infinite content.**

An AI-powered creative director that analyzes your brand and produces complete, ready-to-post social media content packages — captions, images, hashtags, and posting schedules — all generated together in a single interleaved output stream.

## What is this?

Amplifi uses Gemini's interleaved text + image output to generate copy and visuals together in one coherent stream. Paste your website URL (or just describe your business), and get a full week of social media content tailored to your brand, across every platform.

- 🎨 **Brand-aware AI** — extracts your colors, tone, audience, and style automatically
- 📅 **Full weekly calendar** — 7 days of content with pillar-based strategy and event integration
- 🖼️ **Interleaved generation** — captions and matching images born together via Gemini
- 📱 **Multi-platform** — Instagram, LinkedIn, X, TikTok, Facebook with platform-specific formatting
- 📸 **Bring your own photos** — upload product shots, get tailored captions
- 🎬 **AI video** — generate Reels/TikTok clips via Veo (collapses for text-first platforms)
- 🗣️ **Voice analysis** — per-platform demo voice data (LinkedIn B2B, Instagram lifestyle, X punchy) with OAuth-ready social connect
- 📋 **Clipboard-first export** — "Copy All" bulk captions to clipboard, per-post copy, or full ZIP download
- 🔍 **Auto-review** — AI checks every post against your brand for tone, platform rules, and engagement potential
- 🎯 **Platform previews** — live character counts, "see more" fold indicators, and platform-specific formatting

## How it works

1. **Paste your URL** — Amplifi crawls your site and extracts your brand DNA. No website? Just describe your business.
2. **AI builds your brand** — Colors, tone, audience, competitors, style directives — all editable.
3. **Get your week** — Watch as a 7-day content calendar streams in live, post by post.

## Tech Stack

- **AI Engine:** Google Gemini 2.5 Flash (interleaved text + image output)
- **Agent Framework:** Google ADK (Agent Development Kit)
- **Backend:** FastAPI on Cloud Run
- **Database:** Cloud Firestore
- **Storage:** Cloud Storage (generated images + uploads)
- **Video:** Veo 3.1 (P1)
- **Frontend:** React (desktop-first, mobile responsive)
- **Deployment:** Terraform + Cloud Build (CI/CD)

## Architecture

```
User Browser (React) ←REST + SSE→ Cloud Run (FastAPI)
                                    ├── ADK Sequential Pipeline
                                    │   ├── Brand Analyst Agent
                                    │   ├── Strategy Agent
                                    │   ├── Content Creator Agent (interleaved output)
                                    │   └── Review Agent
                                    ├── Gemini API (generateContent)
                                    │   └── responseModalities: ["TEXT", "IMAGE"]
                                    ├── Cloud Firestore (brand profiles, plans)
                                    └── Cloud Storage (images, assets)
```

## Documentation

| Document | Description |
|---|---|
| [Product Requirements (PRD)](docs/PRD.md) | Full product spec — 7 P0, 9 P1, 12 P2, 2 P3 features. All P0, P1, and P2 shipped (28/28). |
| [Technical Design (TDD)](docs/TDD.md) | Implementation spec — 3,200+ lines covering all P0/P1/P2 + persona-driven UX improvements |
| [UI Mockup](docs/amplifi-ui.jsx) | Interactive React prototype — 6 screens (Landing, Onboard, Brand, Calendar, Content, Dashboard) |

## Hackathon

Built for the **Gemini Live Agent Challenge** hackathon ($80K prize pool, Google DeepMind / Devpost).

- **Category:** ✍️ Creative Storyteller
- **Deadline:** March 16, 2026 at 5:00 PM PDT
- **Prize Target:** $10K (category) + $5K (subcategory)

## License

MIT
