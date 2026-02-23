# Amplifi — Playtest Personas

## Overview

Two small business personas reviewed the Amplifi codebase and UI across 2 rounds. The panel evaluated UX fixes incrementally as they were merged to `main`.

| Round | Composite | Delta | HEAD Commit |
|-------|-----------|-------|-------------|
| Round 1 (21+ Fixes: DK/H/M/L tiers) | 8.25/10 | — | `2b6642e` |
| Round 2 (3 Flag Fixes) | 9.25/10 | +1.0 | `b738285` |

**Final Verdict:** Ship the demo. Only remaining gate is live output quality evaluation.

---

## Persona Profiles

### 🧑‍🍳 Maria — The Small Business Owner

| Attribute | Detail |
|-----------|--------|
| Age | 37 |
| Business | Verde Kitchen — farm-to-table restaurant, Brooklyn |
| Team Size | 12 employees |
| Social Media Habit | Does social media Sunday nights in a batch session |
| Primary Platform | Instagram (food photography, stories) |
| Secondary Platform | Facebook (events, community) |
| Tech Comfort | Uses iPhone for photos, has never used AI tools |
| Content Style | Warm, artisanal, community-focused. Own photography. |
| Key Constraint | Time. Sunday night is the only window. Every extra tap is a reason to give up and post nothing. |

### 💼 Jason — The Solopreneur Coach

| Attribute | Detail |
|-----------|--------|
| Age | 42 |
| Business | Executive leadership coaching (Austin) |
| Background | Former VP Engineering at a mid-size tech company |
| Primary Platform | LinkedIn (8K followers — CTOs, VPs, engineering leaders) |
| Secondary Platform | X/Twitter (shorter-form thought leadership) |
| Posting Frequency | 3–4x/week |
| Writing Standards | High. Posts in Notion first, schedules via Buffer. Reads every word before publishing. |
| Content Style | Authoritative, no-emoji, long-form for LinkedIn. Punchy hot-takes for X. |
| Key Constraint | Quality. If AI content reads like generic LinkedIn engagement bait, he's out immediately. |

---

## Round 1 — Baseline Review (21+ Fixes Merged)

**Codebase state:** All DK-1 through DK-5 (demo-killers), H-1 through H-8 (high-priority), M-1 through M-8 and L-1 through L-8 (polish) fixes merged. ~172KB across 17 files.

### Maria's Review — 8.5/10

| Screen | Score | Key Feedback |
|--------|-------|--------------|
| Landing | 9/10 | "No sign-up, no credit card" is the difference between trying and closing the tab. "Describe your business" over "Paste your URL" (L-1 fix) is smarter — Verde Kitchen doesn't have a marketing-ready website. |
| Onboard | 8.5/10 | Pulsing "Finalizing..." animation prevents confusion during brand analysis. Animated 6-step plan generation is educational — "I can see it building my strategy." |
| Dashboard | 9/10 | EventsInput analysis lock (DK-1) prevents silent failure. Animated plan generation turns loading into education. BrandProfileCard is editable with async save feedback. |
| Generate | 8.5/10 | Human-readable subtitle with day/platform/theme context (H-2). Back button always goes to dashboard (H-1). Caption-only mode (M-3) essential — "I use my own photos, I just need the words." |
| Review | 9/10 | Auto-review on mount (DK-3) saves a click on every post. Copy button with timer cleanup. "Next Day →" CTA (L-8) creates the Sunday night batch workflow. |
| Export | 8.5/10 | Approved-only ZIP filter (M-8) is correct. But Maria really wants clipboard-per-post, not a ZIP download. |
| Video | 7/10 | Grayed out on non-video platforms is better than hidden, but adds visual noise when she's only making Instagram caption posts. |
| Voice Coach | 7.5/10 | Tooltip helps explain the feature. Demo voice data button is nice for first-time exploration. |
| **Overall** | **8.5/10** | |

**Maria's biggest concern:** "Need to see content *look* like Verde Kitchen content. AI-generated image quality and brand consistency is everything. UI workflow is exactly right for Sunday night batch, but can't judge output quality from code alone."

### Jason's Review — 8/10

| Screen | Score | Key Feedback |
|--------|-------|--------------|
| Landing | 7.5/10 | Value prop is clear but generic. Platform list (Instagram, TikTok, Facebook) suggests visual-first bias. LinkedIn should be more prominent for B2B users. |
| Onboard | 8.5/10 | Animated 6-step progress feels premium. "Describe your business" is the right CTA. |
| Dashboard | 8/10 | BrandProfileCard editing is critical for voice verification — "I need to see what the AI thinks my voice sounds like and correct it." ContentCalendar pillar-based strategy maps to his workflow. |
| Generate | 9/10 | Caption-only mode is *essential* for text-first creators. Grid switching to full-width caption when `captionOnly=true` is exactly right. |
| Review | 8/10 | Auto-review saves a click. Brand alignment score is what matters most. `revised_caption` field means Review Agent rewrites — this is where the tool wins or loses. Quality depends entirely on prompt engineering behind the agent. |
| Export | 7.5/10 | Wants Buffer-compatible CSV, not ZIP. His workflow is: generate → review → export to Notion → schedule in Buffer. ZIP adds friction. |
| Video | 6/10 | Grayed out is better than hidden, but adds visual noise for text-first creators. "I never use video on LinkedIn. This section shouldn't take up screen real estate when I'm writing captions." |
| Voice Coach | 8/10 | Conceptually sound for maintaining brand voice. But demo voice data is Instagram-only — his business runs on LinkedIn. Sample should match platform. |
| **Overall** | **8/10** | |

**Jason's biggest concern:** "ReviewPanel has `revised_caption` field, meaning the Review Agent rewrites. The tool either wins or loses here. If revised caption reads like generic LinkedIn engagement bait, I'm out. If it reads like something I'd actually write, I'm in. Can't evaluate output quality from codebase. Architecture is right, but prompt engineering behind Review Agent is what matters."

### Unanimous Wins (Round 1)

1. **No sign-up / no credit card** — single biggest conversion factor for both personas
2. **"Describe your business" over "Paste your URL"** (L-1) — URL-first is a barrier for small businesses
3. **Caption-only mode** (M-3) — essential for both use cases (own photos for Maria, text-first for Jason)
4. **Auto-review on mount** (DK-3) — removes a step from every post
5. **"Next Day →" CTA** (L-8) — creates batch workflow
6. **Animated plan generation** (DK-2) — turns loading into education
7. **Analysis lock on EventsInput** (DK-1) — prevents silent failure

### Flags (Round 1)

| # | Flag | Maria | Jason | Severity |
|---|------|-------|-------|----------|
| 1 | Demo voice data is Instagram-only (DK-4) | Neutral (Instagram is her platform) | 7.5/10 — "My business runs on LinkedIn, sample should match platform" | High |
| 2 | Export format is ZIP-only | 8.5/10 — Wants clipboard-per-post | 7.5/10 — Wants Buffer-compatible CSV | High |
| 3 | Video section noise for text-first users (H-6) | 7/10 — Adds noise when making caption posts | 6/10 — "I never use video on LinkedIn" | Medium |
| 4 | Output quality unknowable from code | Both flagged as make-or-break | Both flagged as make-or-break | Expected (requires live demo) |

---

## Round 2 — 3 Flag Fix Branches + MUST FIX Follow-ups

**Fixes merged:** 3 new feature branches directly addressing Round 1 flags.

### Feature 1: Per-Platform Demo Voice Data

**Commits:** `85e5b0a` + `8b86867` fix + `13e5421` merge

- Replaced single Instagram-only demo button with per-platform "try demo" links on each platform card
- **LinkedIn demo:** B2B executive coaching persona — no emoji, long-form, authoritative
- **Instagram demo:** Warm artisanal food/lifestyle (existing data kept)
- **X/Twitter demo:** Punchy, opinionated, short-form hot-take style
- Global "Try with sample voice data" button removed; demo links live inline on each card
- Fix: `type="button"` prevents form submit, `hasAnyActive` covers all 4 voice-analysis data sources, click target padding increased

### Feature 2: Video Collapse for Text-First Platforms

**Commits:** `c2924cb` + `c407a27` fix + `4006a61` fix + `71db2ac` merge

- TEXT_PLATFORMS set: LinkedIn, X, Twitter, Facebook
- Text-first platforms show collapsed pill: "🎬 Video Clip (not typical for this platform) ›"
- Click to expand, "‹ collapse" to restore
- State resets to collapsed on every new post/day switch
- Video platforms (Instagram, TikTok, Reels) unchanged — fully expanded
- Fixes: pill visibility (font 11→12, border/background/hover tint for interactivity), 'x' added to PLATFORM_ICONS to prevent silent 📱 fallback

### Feature 3: Clipboard-First Export

**Commits:** `3fb7f4a` + `f49c1d2` fix + `b738285` merge

- "📋 Copy All" button in PostLibrary header row (between Refresh and Export)
- Structured clipboard format:
  ```
  [1] Instagram · Day 1
  caption text
  #hashtag1 #hashtag2

  ---

  [2] LinkedIn · Day 2
  ...
  ```
- "✓ Copied N" confirmation flash for 1.5s
- Count snapshotted at click time via ref (not re-derived at render) to avoid drift during polling refresh
- Timer cleaned up on unmount
- ExportPage subtitle updated: "Copy captions to clipboard" as primary path before ZIP download

### Maria's Review — 9/10 (+0.5)

| Screen | R1 | R2 | Key Feedback |
|--------|----|----|--------------|
| Landing | 9 | 9 | No change. |
| Onboard | 8.5 | 8.5 | No change. |
| Dashboard | 9 | 9.5 | Per-platform demo data on Instagram card shows warm artisanal food/lifestyle voice — "the tool understands what restaurant content sounds like." |
| Generate | 8.5 | 8.5 | No change. |
| Review | 9 | 9 | No change. |
| Export | 8.5 | **9.5** | "Copy All is exactly what I wanted. Sunday night at 11pm, I don't want to download a ZIP. I want to tap one button, open Instagram, paste." Structured format with `[1] Instagram · Day 1` headers lets her scan and find the right day. "✓ Copied 7" confirmation tells her everything is in clipboard. |
| Video | 7 | 7 | Doesn't affect her much — Instagram-primary with own videos. Neutral. |
| Voice Coach | 7.5 | 7.5 | No change. |
| **Overall** | **8.5** | **9** | |

**Maria's remaining concern:** "Same as before — need to see actual generated content quality. The workflow is now nearly frictionless. If the AI writes captions that sound like Verde Kitchen and not generic food content, this is a 10."

### Jason's Review — 9.5/10 (+1.5)

| Screen | R1 | R2 | Key Feedback |
|--------|----|----|--------------|
| Landing | 7.5 | 7.5 | No change. |
| Onboard | 8.5 | 8.5 | No change. |
| Dashboard | 8 | **9** | Per-platform demo: LinkedIn shows B2B executive coaching persona — "no emoji, long-form, authoritative. That's my voice." This is the difference between "this tool is for restaurants" and "this tool understands professional thought leadership." `hasAnyActive` fix means stored analyses persist correctly across sessions. |
| Generate | 9 | **9.5** | Video collapse for LinkedIn: collapsed pill "🎬 Video Clip (not typical for this platform) ›" — "I don't have to scroll past a grayed-out video section that's irrelevant to my workflow." One tap to expand if needed. State resets per-post. |
| Review | 8 | 8.5 | Per-platform demo data gives confidence the team understands voice differentiation. If demo data is this thoughtful, prompt engineering is probably solid too. |
| Export | 7.5 | **9** | "Copy All solves my Buffer workflow better than CSV would. I copy all 7 captions, paste into Notion, do final edits, schedule in Buffer." Structured format with `[1] LinkedIn · Day 1` headers lets him parse which post goes where. Snapshotted count prevents confusion during polling refresh. |
| Video | 6 | **9** | Collapsed pill is exactly what he asked for. "The pill has visible weight — border, background, hover state signal interactivity without competing with the caption section." |
| Voice Coach | 8 | 8 | No change. |
| **Overall** | **8** | **9.5** | |

**Jason's remaining concern:** "Output quality is still unknowable from code. But the per-platform demo data gives me confidence the team understands voice differentiation across platforms. If they put that care into demo data, the prompt engineering behind the Review Agent is probably solid too. Seeing a generated LinkedIn post that reads like something I'd write is the only remaining gate."

### Flag Resolution Status

| # | Flag | R1 Status | R2 Resolution | Resolved? |
|---|------|-----------|---------------|-----------|
| 1 | Demo voice data Instagram-only | Jason 7.5/10 | Per-platform demos: LinkedIn B2B, Instagram artisanal, X punchy | **Yes** |
| 2 | Export format ZIP-only | Jason 7.5, Maria "just paste" | "Copy All" clipboard-first + structured format | **Yes** |
| 3 | Video section noise for text-first | Jason 6/10 | Collapsed pill on LinkedIn/X/Facebook, expandable on click | **Yes** |
| 4 | Output quality unknowable from code | Both flagged | Still unknowable — requires live demo | **Open (expected)** |

---

## Score Progression Summary

```
          R1      R2
Maria    8.5 ──→ 9.0   (+0.5)
Jason    8.0 ──→ 9.5   (+1.5)
──────────────────────
AVG      8.25    9.25   (+1.0)
```

---

## Per-Screen Score Comparison

| Screen | Maria R1 | Maria R2 | Jason R1 | Jason R2 |
|--------|----------|----------|----------|----------|
| Landing | 9 | 9 | 7.5 | 7.5 |
| Onboard | 8.5 | 8.5 | 8.5 | 8.5 |
| Dashboard | 9 | 9.5 | 8 | 9 |
| Generate | 8.5 | 8.5 | 9 | 9.5 |
| Review | 9 | 9 | 8 | 8.5 |
| Export | 8.5 | 9.5 | 7.5 | 9 |
| Video | 7 | 7 | 6 | 9 |
| Voice Coach | 7.5 | 7.5 | 8 | 8 |

---

## What Each Persona Would Tell a Friend

**Maria:** "There's this AI tool where you describe your business and it generates a week of social media posts. No sign-up, no credit card. You just describe Verde Kitchen, tell it your events, and it builds a whole content calendar. Sunday night I can copy all 7 captions to my clipboard and paste them into Instagram one by one. The whole batch session takes maybe 20 minutes instead of 2 hours."

**Jason:** "I found a content tool that actually understands LinkedIn isn't Instagram. The demo shows a B2B coaching voice — no emoji, authoritative, the way I actually write. It collapses the video section on LinkedIn because it knows I don't need it. I can copy all my week's posts to clipboard and paste into Notion for final edits. If the actual AI output quality matches the UX quality, this replaces my entire content workflow."
