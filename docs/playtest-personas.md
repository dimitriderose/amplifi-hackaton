# Amplifi — Playtest Personas

## Overview

Two small business personas reviewed the Amplifi codebase and UI across 4 rounds. The panel evaluated UX fixes incrementally as they were merged to `main`, reviewed live AI-generated output in Round 3, then watched a full live website recording in Round 4.

| Round | Composite | Delta | HEAD Commit |
|-------|-----------|-------|-------------|
| Round 1 (21+ Fixes: DK/H/M/L tiers) | 8.25/10 | — | `2b6642e` |
| Round 2 (3 Flag Fixes) | 9.25/10 | +1.0 | `b738285` |
| Round 3 (Live Output Review) | 9.4375/10 | +0.1875 | `a9e544d` |
| Round 4 (Live Website Recording) | 9.625/10 | +0.1875 | `a9e544d` |

**Final Verdict:** Ship it. Voice Coach is the sleeper differentiator. One P1 bug (hashtag auto-clean) may be resolved — clean hashtags observed on LinkedIn in R4.

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

### Flag Resolution Status (Round 2)

| # | Flag | R1 Status | R2 Resolution | Resolved? |
|---|------|-----------|---------------|-----------|
| 1 | Demo voice data Instagram-only | Jason 7.5/10 | Per-platform demos: LinkedIn B2B, Instagram artisanal, X punchy | **Yes** |
| 2 | Export format ZIP-only | Jason 7.5, Maria "just paste" | "Copy All" clipboard-first + structured format | **Yes** |
| 3 | Video section noise for text-first | Jason 6/10 | Collapsed pill on LinkedIn/X/Facebook, expandable on click | **Yes** |
| 4 | Output quality unknowable from code | Both flagged | Still unknowable — requires live demo | **Open (expected)** |

---

## Round 3 — Live Output Review (AI-Generated Content)

**Context:** Both personas watched a screen recording of Amplifi generating real content for a CPA firm (Derose & Associates). This is the first time either persona has seen actual AI-generated output — captions, images, video, and brand review — not just the UI shell.

**What the recording shows:**
1. Instagram post: "Essential Tax Season Checklist for Businesses" — full caption mentioning Derose & Associates, NYC and Long Island, tax deadlines
2. AI-generated image — professional styled tax checklist with coffee cup, on-brand
3. Hashtags — #TaxSeason, #BusinessTax, #TaxPreparation, #SmallBusiness, #DeroseAndAssociates, #TaxReady, plus junk hashtags (#Here's, #an, #image, #for, #your, #post:)
4. Veo 3 video clip — 8-second animated version of the checklist image
5. AI Brand Review — Score 9/10 "STRONG BRAND ALIGNMENT", auto-approved, engagement predictions (Hook: 9, Relevance: 10, CTA: 9, Platform Fit: 8), strengths, suggested improvements
6. "Next Day → Day 2" CTA for batch workflow

### Maria's Review — 9.25/10 (+0.25)

| Screen | R2 | R3 | Delta | Notes |
|--------|----|----|-------|-------|
| Landing | 9 | 9 | — | |
| Onboard | 8.5 | 8.5 | — | |
| Dashboard | 9.5 | 9.5 | — | |
| Generate | 8.5 | **9.5** | +1.0 | Caption reads like a real business wrote it — mentions firm by name, references NYC and Long Island, has a clear dual CTA. Image looks like a styled stock photo shoot. Veo 3 clip is usable as a Reel intro. |
| Review | 9 | **9.5** | +0.5 | Brand review caught hashtag pollution, engagement prediction bars are useful, auto-approved at 9/10 is well-calibrated. |
| Export | 9.5 | 9.5 | — | |
| Video | 7 | **8.5** | +1.5 | "That 8-second animated checklist is actually usable as a Reel intro. My Sunday night workflow just got a video option I didn't expect." |
| Voice Coach | 7.5 | 7.5 | — | |
| **Overall** | **9.0** | **9.25** | **+0.25** | |

**Maria's key quotes:**
- Caption: "It reads like a real business wrote it, not an AI. The tone is professional but approachable — warm without being corny."
- Image: "That image looks like something from a real accounting firm's Instagram. The coffee cup, the professional lighting, the checklist with checkmarks — it doesn't look AI-generated in the 'melted fingers' way."
- Hashtags: "The first 8 hashtags are great. The last 5 (`#Here's #an #image #for #your #post:`) are garbage. The Review Agent caught it — but it should have auto-fixed it, not just flagged it."

**Maria's remaining flag:** Hashtag pollution needs to be auto-cleaned, not just flagged. That's the only thing stopping her from hitting Copy All and pasting straight into Instagram without editing.

### Jason's Review — 9.625/10 (+0.125)

| Screen | R2 | R3 | Delta | Notes |
|--------|----|----|-------|-------|
| Landing | 7.5 | 7.5 | — | |
| Onboard | 8.5 | 8.5 | — | |
| Dashboard | 9 | 9 | — | |
| Generate | 9.5 | **10** | +0.5 | "This caption opens with a benefit-driven hook, establishes urgency, then provides structured value. The CTA is dual-track. For Instagram, this is well-structured." Output quality matches UX quality — the gate is cleared. |
| Review | 8.5 | **10** | +1.5 | "This is where the tool differentiates itself from every other AI content tool. Score 9/10 with specific engagement predictions, actionable strengths, and improvement suggestions. The Review Agent caught the hashtag pollution before I did." |
| Export | 9 | 9 | — | |
| Video | 9 | 9 | — | |
| Voice Coach | 8 | 8 | — | |
| **Overall** | **9.5** | **9.625** | **+0.125** | |

**Jason's key quotes:**
- Caption: "The fact that this Instagram post reads like a professional accountant talking to small business owners — not like generic AI slop — tells me the Brand Analyst and Content Creator agents are working."
- Brand Review: "Score 9/10 with specific engagement predictions, actionable strengths, and improvement suggestions. The Review Agent caught the hashtag pollution before I did. That's the kind of quality control that makes me trust the system."
- Architecture: "The per-platform demo data gave me confidence the team understands voice differentiation. The live output confirms it. The architecture delivers."

**Jason's verdict:** "Flag 4 is resolved. The output quality matches the UX quality. The one remaining issue — hashtag auto-cleaning — is a P1 bug, not an architecture problem. The Review Agent already identifies the issue; it just needs to execute the fix instead of only flagging it. Ship it."

---

## Round 4 — Live Website Recording Review

**Context:** Both personas watched a 2:55 screen recording of the live Amplifi website running end-to-end in a browser. This is the first time they've seen the complete app flow — landing page, dashboard with live data, content generation, Voice Coach live conversation, Veo 3.1 video, and AI Brand Review — as a continuous real-time experience.

**What the recording shows (timestamp map):**

| Time | Screen | Content |
|------|--------|---------|
| 0:00 | Landing Page | "Your entire week of content. One click." + platform badges (Instagram, LinkedIn, Twitter/X, Facebook) + "How it works: From zero to a week of brand-consistent content in under 3 minutes" |
| 0:09 | Dashboard | Full Brand Profile (Derose & Associates) + 7-Day Content Calendar — Mon/Tue approved (9/10, 7/10), Wed approved, Thu-Sun with Generate buttons. Pillar color-coding (education/blue, promotion/red, inspiration/purple, behind scenes/green, user generated/orange). Voice Coach widget open. |
| 0:15 | Generate Post | LinkedIn Day 3 "Advanced Tax Strategies for Small Businesses" — live streaming caption + image generation with progress indicators |
| 0:20 | Post Complete | Full LinkedIn caption with Copy button, AI-generated professional image, "HOW THIS LOOKS ON LINKEDIN" platform preview, clean hashtags (#SmallBusinessTax, #TaxStrategy, #FinancialPlanning, #BusinessGrowth, #TaxTips) |
| 0:30 | Dashboard + Voice Coach | Voice Coach widget: "Listening... Continuing conversation..." — multi-turn brand-contextualized dialogue |
| 0:50 | Voice Coach Active | "*Acknowledging the Appreciation* I'm feeling positive after the expressed gratitude! As Derose & Associates' AI brand strategist..." |
| 1:10 | Voice Coach Speaking | "*Resuming Facebook Strategy* I'm ready to dive back into our Facebook strategy discussion for Derose & Associates. Following..." |
| 1:40 | Veo 3.1 Video Clip | "Video Clip (Veo 3.1)" — 8-second animated notebook/coffee/hand-writing clip |
| 2:00 | AI Brand Review | Score 9/10 "STRONG BRAND ALIGNMENT", Auto-approved. Engagement Predictions: Hook 9, Relevance 9, CTA 8, Platform Fit 9. Strengths (3 items), Suggested Improvements (direct link/DM CTA). "Done — Go to Dashboard" + "Re-review" buttons. |
| 2:30 | Dashboard + Voice Coach | "*Defining the Approach* I'm now zeroing in on Facebook advertising strategies. My focus is laser-targeted for Derose &..." |
| 2:55 | End | |

### Maria's Review — 9.5/10 (+0.25)

| Screen | R3 | R4 | Delta | Notes |
|--------|----|----|-------|-------|
| Landing | 9 | **9.5** | +0.5 | "Seeing it live changes everything. The landing page with Derose & Associates already listed under YOUR BRANDS with a green 'Ready' badge — it's not just a promise, the brand is already loaded. 'How it works' section below the fold is new to me." |
| Onboard | 8.5 | 8.5 | — | Not shown in recording |
| Dashboard | 9.5 | **10** | +0.5 | "The calendar is alive. Mon and Tue show 'Approved 9/10' with green badges. Wed shows 'Approved 7/10'. The rest have Generate buttons. I can see the batch workflow happening — three posts already done, four to go. The Voice Coach is just there, floating in the corner, having a conversation about Facebook strategy while I'm looking at the calendar. It's like having a marketing intern on a call in the background." |
| Generate | 9.5 | 9.5 | — | "Watching it stream the LinkedIn caption in real-time while simultaneously generating the image — that's satisfying. The progress indicators tell me what it's doing at every step." |
| Review | 9.5 | **10** | +0.5 | "The LinkedIn post review is even cleaner than the Instagram one from Round 3. Hashtags are all professional — no junk hashtags this time! Engagement predictions are slightly different per platform. The Suggested Improvements actually suggests adding a direct link or 'DM us to learn more' CTA. That's specific and actionable." |
| Export | 9.5 | 9.5 | — | Not shown in recording |
| Video | 8.5 | **9** | +0.5 | "Video Clip labeled '(Veo 3.1)' — collapsed as '(not typical for this platform)' on LinkedIn. Exactly what Jason asked for. Expands to show the notebook/coffee clip." |
| Voice Coach | 7.5 | **9** | +1.5 | "THIS is the feature I didn't understand from code. The Voice Coach is having a real conversation — acknowledging what Dimitri said, then pivoting to Facebook strategy with specific recommendations for the CPA firm. It remembers the brand context across the whole conversation. That's not a chatbot, that's a strategist." |
| **Overall** | **9.25** | **9.5** | **+0.25** | |

**Maria's key quote:** "The Voice Coach sold me. In the code review it was just a floating button with a tooltip. Watching it actually have a multi-turn brand strategy conversation while the dashboard is right there — I can picture myself using this on Sunday night. Generate my posts, then ask the Voice Coach 'what should I post about this week's farm delivery?' and get back a real answer in my brand voice."

### Jason's Review — 9.75/10 (+0.125)

| Screen | R3 | R4 | Delta | Notes |
|--------|----|----|-------|-------|
| Landing | 7.5 | **8.5** | +1.0 | "The landing page with a real brand loaded changes the pitch entirely. 'Derose & Associates — Accounting & Financial Services' with platform badges. This isn't a mockup. 'From zero to a week of brand-consistent content in under 3 minutes' — that's the claim, and the recording proves it." |
| Onboard | 8.5 | 8.5 | — | Not shown |
| Dashboard | 9 | **10** | +1.0 | "The 7-Day Content Calendar with live status is everything. Mon/Tue approved at 9/10 and 7/10. Color-coded pillar tags. Mixed formats across days. 9 Content Themes visible. This is a content strategist's dashboard, not a content spinner's dashboard." |
| Generate | 10 | 10 | — | "LinkedIn caption streams in real-time. Professional tone, benefit-driven hook, structured value. Confirmed what I saw in Round 3." |
| Review | 10 | 10 | — | "Clean hashtags on LinkedIn post. Engagement predictions consistent. Review Agent suggestions are platform-specific. Architecture continues to deliver." |
| Export | 9 | 9 | — | Not shown |
| Video | 9 | 9 | — | "Collapsed pill on LinkedIn confirmed live. Works exactly as designed." |
| Voice Coach | 8 | **9.5** | +1.5 | "The Voice Coach is the sleeper feature. Watching it maintain brand context across a multi-turn conversation about Facebook strategy for a CPA firm — '*Resuming Facebook Strategy* I'm ready to dive back into our Facebook strategy discussion for Derose & Associates.' It remembered the topic from earlier in the conversation. '*Defining the Approach* I'm now zeroing in on Facebook advertising strategies...' — that's Gemini Live Audio doing real work, not a chatbot parlor trick. For a B2B coach like me, being able to talk through content strategy while looking at my calendar is a workflow multiplier." |
| **Overall** | **9.625** | **9.75** | **+0.125** | |

**Jason's key quote:** "Two things changed my mind in this recording. First, the calendar with live approval badges — seeing 3 of 7 posts already at 9/10 and 7/10 tells me the batch workflow actually works at scale, not just for one demo post. Second, the Voice Coach. That's the Gemini Live Audio integration that differentiates this from every Buffer/Hootsuite/Jasper clone. It's not generating content — it's having a strategic conversation about my content while I'm looking at my content calendar. That's a fundamentally different product category."

### Key Round 4 Observations

| # | Observation | Maria | Jason | Impact |
|---|------------|-------|-------|--------|
| 5a | Hashtag pollution appears fixed on LinkedIn | ✅ Clean hashtags observed | ✅ Confirmed clean | P1 may be resolved |
| 6 | Voice Coach is the sleeper differentiator | +1.5 score jump (7.5→9) | +1.5 score jump (8→9.5) | Both personas upgraded after seeing live conversation |
| 7 | Calendar with live approval badges validates batch workflow | "Three done, four to go" | "Works at scale, not just one demo" | Dashboard is the anchor screen |

---

## Score Progression Summary (All 4 Rounds)

```
          R1      R2      R3      R4
Maria    8.5 ──→ 9.0 ──→ 9.25 ──→ 9.5     (+1.0 total)
Jason    8.0 ──→ 9.5 ──→ 9.625──→ 9.75    (+1.75 total)
──────────────────────────────────────────────
AVG      8.25    9.25    9.4375   9.625    (+1.375 total)
```

---

## Per-Screen Score Comparison (All 4 Rounds)

| Screen | Maria R1 | Maria R2 | Maria R3 | Maria R4 | Jason R1 | Jason R2 | Jason R3 | Jason R4 |
|--------|----------|----------|----------|----------|----------|----------|----------|----------|
| Landing | 9 | 9 | 9 | 9.5 | 7.5 | 7.5 | 7.5 | 8.5 |
| Onboard | 8.5 | 8.5 | 8.5 | 8.5 | 8.5 | 8.5 | 8.5 | 8.5 |
| Dashboard | 9 | 9.5 | 9.5 | 10 | 8 | 9 | 9 | 10 |
| Generate | 8.5 | 8.5 | 9.5 | 9.5 | 9 | 9.5 | 10 | 10 |
| Review | 9 | 9 | 9.5 | 10 | 8 | 8.5 | 10 | 10 |
| Export | 8.5 | 9.5 | 9.5 | 9.5 | 7.5 | 9 | 9 | 9 |
| Video | 7 | 7 | 8.5 | 9 | 6 | 9 | 9 | 9 |
| Voice Coach | 7.5 | 7.5 | 7.5 | 9 | 8 | 8 | 8 | 9.5 |

---

## Flag Resolution (Final)

| # | Flag | R1 | R2 | R3 | R4 | Status |
|---|------|----|----|-----|-----|--------|
| 1 | Demo voice data Instagram-only | Open | ✅ Resolved | ✅ | ✅ | Per-platform demos |
| 2 | Export format ZIP-only | Open | ✅ Resolved | ✅ | ✅ | Copy All clipboard |
| 3 | Video noise for text-first | Open | ✅ Resolved | ✅ | ✅ | Collapsed pill |
| 4 | Output quality unknowable | Open | Open | ✅ **Resolved** | ✅ | Live output confirms brand alignment |
| 5 | Hashtag pollution | — | — | 🟡 **New P1** | 🟢 **Likely resolved** | Clean hashtags on LinkedIn in R4; Instagram R3 had junk — may be platform-specific fix |
| 6 | Voice Coach undervalued from code | — | — | — | ✅ **Identified** | Both personas +1.5 after live demo; sleeper differentiator |

---

## What Each Persona Would Tell a Friend

**Maria:** "There's this AI tool where you describe your business and it generates a week of social media posts. No sign-up, no credit card. You just describe Verde Kitchen, tell it your events, and it builds a whole content calendar with color-coded pillars. Sunday night I can copy all 7 captions to my clipboard and paste them into Instagram one by one. The whole batch session takes maybe 20 minutes instead of 2 hours. But the thing that surprised me? There's a Voice Coach — you can literally talk to it about your content strategy while you're looking at your calendar. I asked about farm delivery posts and it gave me ideas in my brand voice. It's like having a marketing strategist on a phone call while you're doing your Sunday night batch."

**Jason:** "I found a content tool that actually understands LinkedIn isn't Instagram. The demo shows a B2B coaching voice — no emoji, authoritative, the way I actually write. It collapses the video section on LinkedIn because it knows I don't need it. I can copy all my week's posts to clipboard and paste into Notion for final edits. The brand review scores each post with engagement predictions and catches its own mistakes. But the real differentiator is the Voice Coach — it's Gemini Live Audio having a multi-turn strategy conversation about your content while you're looking at your content calendar. It remembered we were discussing Facebook strategy and picked right back up. That's not a chatbot. That's a different product category from Buffer or Jasper. If you're a solopreneur who needs to sound like yourself at scale, this is the tool."
