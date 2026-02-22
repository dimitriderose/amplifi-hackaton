import logging
import os
import uuid
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from backend.config import CORS_ORIGINS
from backend.models.brand import BrandProfileCreate, BrandProfile
from backend.services import firestore_client
from backend.services.storage_client import upload_brand_asset
from backend.agents.brand_analyst import run_brand_analysis

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Amplifi API",
    description="AI-powered social media content generation",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Health ────────────────────────────────────────────────────

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "amplifi-backend", "version": "1.0.0"}

# ── Brand Management ──────────────────────────────────────────

@app.post("/api/brands")
async def create_brand(data: BrandProfileCreate):
    """Create a new brand profile record (without analysis)."""
    brand_id = await firestore_client.create_brand({
        "website_url": data.website_url,
        "description": data.description,
        "uploaded_assets": data.uploaded_assets or [],
        "analysis_status": "pending",
    })
    return {"brand_id": brand_id, "status": "created"}


@app.post("/api/brands/{brand_id}/analyze")
async def analyze_brand(brand_id: str, data: BrandProfileCreate):
    """Trigger Brand Analyst agent to build the brand profile."""
    # Mark as analyzing
    await firestore_client.update_brand(brand_id, {"analysis_status": "analyzing"})

    try:
        profile = await run_brand_analysis(
            description=data.description,
            website_url=data.website_url,
        )

        # Merge AI results into Firestore document
        update_data = {
            **profile,
            "description": data.description,
            "website_url": data.website_url,
            "analysis_status": "complete",
        }
        await firestore_client.update_brand(brand_id, update_data)

        brand = await firestore_client.get_brand(brand_id)
        return {"brand_profile": brand, "status": "analyzed"}

    except Exception as e:
        logger.error(f"Brand analysis error for {brand_id}: {e}")
        await firestore_client.update_brand(brand_id, {"analysis_status": "failed"})
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/brands/{brand_id}")
async def get_brand(brand_id: str):
    """Get brand profile by ID."""
    brand = await firestore_client.get_brand(brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    return {"brand_profile": brand}


@app.put("/api/brands/{brand_id}")
async def update_brand(brand_id: str, data: dict):
    """Update brand profile fields (user corrections)."""
    brand = await firestore_client.get_brand(brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    await firestore_client.update_brand(brand_id, data)
    updated = await firestore_client.get_brand(brand_id)
    return {"brand_profile": updated, "status": "updated"}


@app.post("/api/brands/{brand_id}/upload")
async def upload_brand_asset_endpoint(
    brand_id: str,
    files: list[UploadFile] = File(...),
):
    """Upload brand assets (logo, product photos, PDFs). Max 3 files."""
    brand = await firestore_client.get_brand(brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    if len(files) > 3:
        raise HTTPException(status_code=400, detail="Maximum 3 files allowed")

    uploaded = []
    for file in files:
        content = await file.read()
        mime = file.content_type or "application/octet-stream"
        file_type = "document" if "pdf" in mime else "image"
        gcs_uri = await upload_brand_asset(brand_id, content, file.filename, mime)
        uploaded.append({
            "filename": file.filename,
            "url": gcs_uri,
            "type": file_type,
        })

    # Update brand assets list in Firestore
    existing = brand.get("uploaded_assets", [])
    await firestore_client.update_brand(brand_id, {"uploaded_assets": existing + uploaded})

    return {"uploaded": uploaded}


# ── Static frontend (production) ──────────────────────────────
frontend_dist = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.exists(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
