# Amplifi — Deployment Guide

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.12+ | Backend runtime |
| Node.js | 20+ | Frontend build (TypeScript + Vite 7) |
| npm | 10+ | Frontend package manager |
| Google Cloud SDK (`gcloud`) | Latest | GCP services + deployment |
| Docker | 24+ | Container builds (production) |
| ffmpeg | 6+ | Video processing (installed in Docker, needed locally for video features) |
| Git | 2.x | Source control |

### GCP Services Required

| Service | Purpose | Free Tier? |
|---------|---------|------------|
| **Gemini API** | Brand analysis, content creation (interleaved text+image), review, voice coach | Yes — generous free tier |
| **Cloud Firestore** | Brand profiles, content plans, posts | Yes — 1 GiB free |
| **Cloud Storage** | Generated images, uploaded assets, video clips | Yes — 5 GB free |
| **Cloud Run** | Backend hosting (production) | Yes — 2M requests/month |
| **Cloud Build** | CI/CD pipeline (production) | Yes — 120 build-min/day |

---

## Part 1: Local Development

### 1.1 Clone the Repo

```bash
git clone https://github.com/dimitriderose/amplifi-hackaton.git
cd amplifi-hackaton
```

### 1.2 Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate    # macOS/Linux
# .venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

**Dependencies installed:**
- `fastapi==0.115.0` + `uvicorn[standard]==0.30.0` — ASGI web framework
- `google-adk==0.5.0` — Google Agent Development Kit (ADK sequential pipeline)
- `google-genai==1.0.0` — Gemini API (interleaved text+image generation)
- `google-cloud-firestore==2.19.0` — Firestore client
- `google-cloud-storage==2.18.0` — Cloud Storage client (images, video)
- `httpx==0.27.0` — Async HTTP (web scraping, external API calls)
- `beautifulsoup4==4.12.3` — HTML parsing (brand URL scraping)
- `pydantic==2.9.0` — Data models
- `python-dotenv==1.0.0` — Environment variable loading
- `python-multipart==0.0.9` — File upload handling
- `sse-starlette==1.8.2` — Server-Sent Events (streaming generation)

### 1.3 Environment Variables

```bash
cp .env.example .env
```

Edit `backend/.env`:

```env
# === REQUIRED ===
GOOGLE_API_KEY=your-gemini-api-key
GCP_PROJECT_ID=your-gcp-project-id

# === STORAGE ===
GCS_BUCKET_NAME=your-project-id-amplifi-assets

# === CORS ===
CORS_ORIGINS=http://localhost:5173

# === OPTIONAL: Gemini model override ===
GEMINI_MODEL=gemini-2.5-flash

# === OPTIONAL: Social OAuth (future) ===
LINKEDIN_CLIENT_ID=
LINKEDIN_CLIENT_SECRET=
META_APP_ID=
META_APP_SECRET=
X_CLIENT_ID=
X_CLIENT_SECRET=
```

**Getting credentials:**

1. **Gemini API Key:** Go to [Google AI Studio](https://aistudio.google.com/apikey) → Create API Key
2. **GCP Project:** `gcloud projects create amplifi-hackathon` (or use existing)
3. **Authentication (local dev):**
   ```bash
   gcloud auth application-default login
   ```
   This uses ADC (Application Default Credentials) — no service account file needed locally.
4. **Cloud Storage Bucket:**
   ```bash
   gcloud storage buckets create gs://YOUR_PROJECT_ID-amplifi-assets \
     --location=us-central1 \
     --uniform-bucket-level-access
   ```
5. **Firestore:**
   ```bash
   gcloud firestore databases create --location=us-central1
   ```

### 1.4 Start the Backend

```bash
cd backend
uvicorn server:app --host 0.0.0.0 --port 8080 --reload
```

**Note:** Amplifi's backend is `server.py` (not `main.py`) and runs on port **8080** (not 8000).

Verify: `curl http://localhost:8080/health`

### 1.5 Frontend Setup

Open a **new terminal**:

```bash
cd frontend
npm install
npm run dev
```

This starts Vite on `http://localhost:5173` with HMR. The Vite config proxies:
- `/api/*` → `http://localhost:8080` (REST + SSE endpoints)
- `/health` → `http://localhost:8080`

**Note:** The frontend is TypeScript (`.tsx`) with React 19, Vite 7, and ESLint. The build step is `tsc -b && vite build`.

### 1.6 Test Locally

1. Open `http://localhost:5173` in your browser
2. Click "Get Started" — no sign-up required
3. Describe your business (or paste a URL)
4. Watch brand analysis run → content calendar generates via SSE stream
5. Review posts → Copy All to clipboard

**Architecture (local dev):**
```
Browser :5173 ──Vite proxy──→ FastAPI :8080
                                 ├── /api/* (REST + SSE streams)
                                 ├── Gemini API (brand analysis, content creation, review)
                                 ├── Cloud Firestore (brand profiles, plans, posts)
                                 └── Cloud Storage (generated images)
```

---

## Part 2: Production Deployment (Cloud Run)

### 2.1 Architecture

The Dockerfile builds both frontend and backend into a single image. The backend serves the compiled frontend:

```
Internet → Cloud Run :8080
             ├── /api/*  → FastAPI routes + SSE streams
             └── /*      → frontend/dist/ (static React app)
```

### 2.2 Build the Docker Image

From the **repo root**:

```bash
docker build -f backend/Dockerfile -t amplifi .
```

**What the Dockerfile does:**
1. Base: `python:3.12-slim`
2. Installs system deps: `build-essential`, `curl`, `ffmpeg`, Node.js 20
3. Copies `frontend/` → runs `npm ci && npm run build` (TypeScript compile + Vite build)
4. Installs Python deps from `backend/requirements.txt`
5. Copies `backend/`
6. Runs `uvicorn backend.server:app` on port 8080

### 2.3 Test Docker Locally

```bash
docker run -p 8080:8080 \
  -e GOOGLE_API_KEY=your-key \
  -e GCP_PROJECT_ID=your-project-id \
  -e GCS_BUCKET_NAME=your-project-id-amplifi-assets \
  -e CORS_ORIGINS=http://localhost:8080 \
  -e GOOGLE_APPLICATION_CREDENTIALS=/app/sa.json \
  -v $(pwd)/service-account.json:/app/sa.json:ro \
  amplifi
```

Visit `http://localhost:8080` — should serve the full app.

### 2.4 Deploy to Cloud Run

```bash
# Set your project
export PROJECT_ID=your-gcp-project-id
gcloud config set project $PROJECT_ID

# Enable required APIs
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  firestore.googleapis.com \
  storage.googleapis.com \
  aiplatform.googleapis.com

# Build and push (note: --timeout is important, frontend build takes time)
gcloud builds submit \
  --tag gcr.io/$PROJECT_ID/amplifi \
  --timeout=900

# Deploy
gcloud run deploy amplifi \
  --image gcr.io/$PROJECT_ID/amplifi \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8080 \
  --memory 2Gi \
  --cpu 2 \
  --min-instances 0 \
  --max-instances 10 \
  --timeout 300 \
  --set-env-vars="GOOGLE_API_KEY=your-key,GCP_PROJECT_ID=$PROJECT_ID,GCS_BUCKET_NAME=$PROJECT_ID-amplifi-assets,CORS_ORIGINS=https://amplifi-HASH.run.app"
```

**Critical flags:**
- `--memory 2Gi` — Gemini interleaved generation (text+image) responses can be large
- `--timeout 300` — SSE content generation streams can run 2-3 minutes for a full 7-day plan
- `--port 8080` — Matches Dockerfile
- `CORS_ORIGINS` — Set to your Cloud Run URL after first deploy

### 2.5 Post-Deploy: Set CORS

Get your Cloud Run URL and update:

```bash
gcloud run services update amplifi \
  --set-env-vars="CORS_ORIGINS=https://amplifi-abc123-uc.a.run.app"
```

### 2.6 Cloud Storage CORS (Required for Image Display)

If generated images are stored in GCS and loaded directly by the browser, set CORS on the bucket:

```bash
cat > cors.json << 'EOF'
[
  {
    "origin": ["https://amplifi-abc123-uc.a.run.app", "http://localhost:5173"],
    "method": ["GET"],
    "responseHeader": ["Content-Type"],
    "maxAgeSeconds": 3600
  }
]
EOF

gcloud storage buckets update gs://$PROJECT_ID-amplifi-assets --cors-file=cors.json
```

### 2.7 Custom Domain (Optional)

```bash
gcloud run domain-mappings create \
  --service amplifi \
  --domain app.amplifi.ai \
  --region us-central1
```

---

## Part 3: Environment Variable Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GOOGLE_API_KEY` | Yes | `""` | Gemini API key for all agents |
| `GCP_PROJECT_ID` | Yes | `amplifi-hackathon` | GCP project ID |
| `GCS_BUCKET_NAME` | Yes | `{project}-amplifi-assets` | Cloud Storage bucket for images/video |
| `CORS_ORIGINS` | Yes | `http://localhost:5173` | Comma-separated allowed origins |
| `GEMINI_MODEL` | No | `gemini-2.5-flash` | Default Gemini model |
| `LINKEDIN_CLIENT_ID` | No | `""` | LinkedIn OAuth (future) |
| `LINKEDIN_CLIENT_SECRET` | No | `""` | LinkedIn OAuth (future) |
| `META_APP_ID` | No | `""` | Meta/Facebook OAuth (future) |
| `META_APP_SECRET` | No | `""` | Meta/Facebook OAuth (future) |
| `X_CLIENT_ID` | No | `""` | X/Twitter OAuth (future) |
| `X_CLIENT_SECRET` | No | `""` | X/Twitter OAuth (future) |

### Budget Constants (hardcoded in `config.py`)

| Constant | Value | Description |
|----------|-------|-------------|
| `IMAGE_COST_PER_UNIT` | $0.039 | Per generated image |
| `VIDEO_COST_FAST` | $1.20 | Per 8-sec Veo Fast clip |
| `VIDEO_COST_STD` | $3.20 | Per 8-sec Veo Standard clip |
| `TOTAL_BUDGET` | $100 | Per-session budget cap |
| `IMAGE_BUDGET` | $70 | Image generation cap |
| `VIDEO_BUDGET` | $30 | Video generation cap |

---

## Part 4: Project Structure

```
amplifi-hackaton/
├── backend/
│   ├── agents/
│   │   ├── brand_analyst.py          # URL scraping + brand DNA extraction
│   │   ├── strategy_agent.py         # 7-day content calendar + pillar strategy
│   │   ├── content_creator.py        # Gemini interleaved text+image generation
│   │   ├── review_agent.py           # Brand alignment review + revised captions
│   │   ├── social_voice_agent.py     # Platform voice analysis (LinkedIn/IG/X)
│   │   ├── voice_coach.py            # Ongoing brand voice coaching
│   │   ├── video_creator.py          # Veo 3.1 video generation
│   │   └── video_repurpose_agent.py  # Video clip repurposing
│   ├── models/
│   │   ├── brand.py                  # BrandProfile Pydantic model
│   │   ├── plan.py                   # ContentPlan + DayBrief models
│   │   ├── post.py                   # Post model (caption, image, status)
│   │   └── api.py                    # Request/response schemas
│   ├── services/
│   │   ├── firestore_client.py       # Firestore CRUD for brands, plans, posts
│   │   ├── storage_client.py         # GCS upload/download for images
│   │   └── budget_tracker.py         # Per-session cost tracking
│   ├── tools/
│   │   ├── web_scraper.py            # httpx + BeautifulSoup URL crawling
│   │   └── brand_tools.py            # ADK tool wrappers for brand analysis
│   ├── server.py                     # FastAPI app (REST + SSE + static mount)
│   ├── config.py                     # Environment config + budget constants
│   ├── Dockerfile                    # Multi-stage: Node build + Python runtime
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/               # React components (TypeScript)
│   │   │   ├── LandingPage.tsx
│   │   │   ├── OnboardPage.tsx
│   │   │   ├── DashboardPage.tsx
│   │   │   ├── GeneratePage.tsx
│   │   │   ├── PostGenerator.tsx
│   │   │   ├── ReviewPanel.tsx
│   │   │   ├── ExportPage.tsx
│   │   │   ├── PostLibrary.tsx       # Copy All clipboard button
│   │   │   ├── VoiceCoach.tsx
│   │   │   ├── VideoRepurpose.tsx
│   │   │   ├── BrandProfileCard.tsx
│   │   │   └── EventsInput.tsx       # Analysis lock on edit
│   │   └── ...
│   ├── package.json                  # React 19 + react-router-dom + Vite 7
│   ├── tsconfig.json                 # TypeScript config
│   ├── vite.config.ts                # Proxy /api → :8080
│   └── index.html
└── docs/
    ├── PRD.md
    ├── TDD.md
    ├── amplifi-ui.jsx
    └── playtest-personas.md
```

---

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| `CORS error` in browser | `CORS_ORIGINS` doesn't include your frontend URL | Update `CORS_ORIGINS` env var (comma-separated) |
| SSE stream hangs / times out | Cloud Run default timeout too short | Deploy with `--timeout 300` |
| `ModuleNotFoundError: google.adk` | Missing ADK dependency | `pip install google-adk==0.5.0` |
| Images not loading from GCS | Bucket CORS not configured | Set GCS CORS policy (see §2.6) |
| `tsc -b` fails during Docker build | TypeScript compilation errors | Run `cd frontend && npm run build` locally first to catch errors |
| `ffmpeg not found` locally | ffmpeg not installed on host | `brew install ffmpeg` (macOS) or `sudo apt install ffmpeg` (Linux) — only needed for video features |
| Brand analysis returns empty | URL not crawlable / description too short | Use "describe your business" with 2-3 sentences minimum |
| Budget exceeded error | Session hit $100 cap | Budget resets per session; reduce image count or use caption-only mode |
| `npm ci` fails in Docker | `package-lock.json` out of sync | Run `cd frontend && npm install` locally to regenerate lockfile, commit |

---

## Key Differences from Fireside

| Aspect | Fireside | Amplifi |
|--------|----------|---------|
| Backend entry | `backend/main.py` | `backend/server.py` |
| Backend port | 8000 | 8080 |
| Python version | 3.11 | 3.12 |
| Frontend language | JavaScript (JSX) | TypeScript (TSX) |
| React version | 18 | 19 |
| Vite version | 5 | 7 |
| Real-time | WebSocket | SSE (Server-Sent Events) |
| Agent framework | Direct Gemini API calls | Google ADK pipeline |
| External storage | Firestore only | Firestore + Cloud Storage |
| Dockerfile scope | Backend only | Full-stack (Node build + Python) |
