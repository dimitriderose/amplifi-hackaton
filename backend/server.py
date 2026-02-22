import asyncio
import io
import json
import logging
import os
import uuid
import zipfile
from fastapi import FastAPI, HTTPException, Query, UploadFile, File, Form, Body, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, StreamingResponse

from backend.config import CORS_ORIGINS
from backend.models.brand import BrandProfileCreate, BrandProfile
from backend.services import firestore_client
from backend.services.storage_client import (
    upload_brand_asset,
    get_signed_url,
    download_from_gcs,
    upload_byop_photo,
)
from google import genai as _genai
from google.genai import types as _gtypes
from backend.config import GOOGLE_API_KEY, GEMINI_MODEL
from backend.agents.brand_analyst import run_brand_analysis
from backend.agents.strategy_agent import run_strategy
from backend.agents.voice_coach import build_coaching_prompt

_live_client = _genai.Client(api_key=GOOGLE_API_KEY)
_LIVE_MODEL = "gemini-2.0-flash-live-001"

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
async def update_brand(brand_id: str, data: dict = Body(...)):
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


# ── Posts ─────────────────────────────────────────────────────

@app.get("/api/posts")
async def list_posts_endpoint(
    brand_id: str = Query(...),
    plan_id: str | None = Query(None),
):
    """List all posts for a brand, optionally filtered by plan."""
    posts = await firestore_client.list_posts(brand_id, plan_id)
    return {"posts": posts}


# ── Export / Download ─────────────────────────────────────────

@app.get("/api/posts/{post_id}/export")
async def export_post(
    post_id: str,
    brand_id: str = Query(..., description="Brand ID that owns the post"),
):
    """Return post metadata plus a download URL.

    If the post has an ``image_gcs_uri`` (a ``gs://`` URI stored at upload
    time), it is converted to a short-lived signed URL and returned as
    ``download_url``.  The raw ``image_gcs_uri`` is never exposed to callers.
    """
    post = await firestore_client.get_post(brand_id, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    image_gcs_uri: str | None = post.get("image_gcs_uri")
    download_url: str | None = None
    image_url: str | None = None

    if image_gcs_uri:
        try:
            signed = await get_signed_url(image_gcs_uri)
            download_url = signed
            image_url = signed
        except Exception as exc:
            logger.warning("Could not sign GCS URI %s: %s", image_gcs_uri, exc)
    else:
        # Fall back to the first element of image_urls if present
        urls: list = post.get("image_urls", [])
        if urls:
            image_url = urls[0]
            download_url = image_url

    return {
        "post_id": post_id,
        "platform": post.get("platform"),
        "caption": post.get("caption", ""),
        "hashtags": post.get("hashtags", []),
        "image_url": image_url,
        "download_url": download_url,
    }


@app.post("/api/export/{plan_id}")
async def export_plan_zip(
    plan_id: str,
    brand_id: str = Query(..., description="Brand ID that owns the plan"),
):
    """Build and stream a ZIP archive containing all posts for a content plan.

    Archive layout::

        amplifi_export_<plan_id>/
            instagram_0.jpg
            instagram_0_caption.txt
            linkedin_1.jpg
            linkedin_1_caption.txt
            …
            content_plan.json

    Each ``*_caption.txt`` file contains the post caption followed by the
    hashtags (one per line, prefixed with ``#``).
    ``content_plan.json`` contains full metadata for every post.
    """
    # ── Fetch plan to confirm it exists ───────────────────────
    plan = await firestore_client.get_plan(plan_id, brand_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    # ── List all posts belonging to this plan ─────────────────
    posts: list[dict] = await firestore_client.list_posts(brand_id, plan_id)
    if not posts:
        raise HTTPException(status_code=404, detail="No posts found for this plan")

    # ── Resolve signed URLs for every post that has an image ──
    async def _resolve_image_url(post: dict) -> str | None:
        gcs_uri: str | None = post.get("image_gcs_uri")
        if gcs_uri:
            try:
                return await get_signed_url(gcs_uri)
            except Exception as exc:
                logger.warning(
                    "Could not sign GCS URI %s for post %s: %s",
                    gcs_uri,
                    post.get("post_id"),
                    exc,
                )
                return None
        # Fall back to the first element of image_urls
        urls: list = post.get("image_urls", [])
        return urls[0] if urls else None

    signed_urls: list[str | None] = await asyncio.gather(
        *[_resolve_image_url(p) for p in posts]
    )

    # ── Download image bytes in parallel (skip posts without images) ──
    async def _download_image(url: str | None) -> bytes | None:
        if not url:
            return None
        try:
            return await download_from_gcs(url)
        except Exception as exc:
            logger.warning("Could not download image from %s: %s", url, exc)
            return None

    image_bytes_list: list[bytes | None] = await asyncio.gather(
        *[_download_image(u) for u in signed_urls]
    )

    # ── Build ZIP in memory ───────────────────────────────────
    zip_buffer = io.BytesIO()
    archive_root = f"amplifi_export_{plan_id}"

    # Collect clean metadata for content_plan.json (strip internal GCS URIs)
    plan_metadata: list[dict] = []

    with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for index, (post, img_bytes, img_url) in enumerate(
            zip(posts, image_bytes_list, signed_urls)
        ):
            platform: str = post.get("platform", "post")
            caption: str = post.get("caption", "")
            hashtags: list[str] = post.get("hashtags", [])
            base_name = f"{platform}_{index}"

            # Image file — detect PNG vs JPEG by magic bytes
            if img_bytes:
                ext = "png" if img_bytes[:4] == b"\x89PNG" else "jpg"
                zf.writestr(f"{archive_root}/{base_name}.{ext}", img_bytes)

            # Caption + hashtags text file
            hashtag_block = "\n".join(f"#{tag.lstrip('#')}" for tag in hashtags)
            caption_text = caption
            if hashtag_block:
                caption_text = f"{caption}\n\n{hashtag_block}"
            zf.writestr(
                f"{archive_root}/{base_name}_caption.txt",
                caption_text.encode("utf-8"),
            )

            # Collect metadata (safe copy — omit internal GCS URI)
            post_meta = {
                k: v for k, v in post.items() if k != "image_gcs_uri"
            }
            post_meta["image_url"] = img_url
            plan_metadata.append(post_meta)

        # content_plan.json
        zf.writestr(
            f"{archive_root}/content_plan.json",
            json.dumps(plan_metadata, indent=2, default=str).encode("utf-8"),
        )

    zip_buffer.seek(0)

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename=amplifi_export_{plan_id}.zip"
        },
    )


# ── Content Plans ─────────────────────────────────────────────

from pydantic import BaseModel as _PydanticBaseModel


class CreatePlanBody(_PydanticBaseModel):
    num_days: int = 7
    business_events: str | None = None


@app.get("/api/brands/{brand_id}/plans")
async def list_plans(brand_id: str):
    """List all content plans for a brand, newest first."""
    plans = await firestore_client.list_plans(brand_id)
    return {"plans": plans}


@app.post("/api/brands/{brand_id}/plans")
async def create_plan(brand_id: str, body: CreatePlanBody = Body(CreatePlanBody())):
    """Generate a content calendar plan using the Strategy Agent."""
    brand = await firestore_client.get_brand(brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    num_days = max(1, min(body.num_days, 30))

    try:
        days = await run_strategy(brand_id, brand, num_days, business_events=body.business_events)
    except Exception as e:
        logger.error(f"Strategy agent error for brand {brand_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    plan_data = {
        "brand_id": brand_id,
        "num_days": num_days,
        "status": "complete",
        "days": days,
        "business_events": body.business_events,
    }

    try:
        plan_id = await firestore_client.create_plan(brand_id, plan_data)
    except Exception as e:
        logger.error(f"Failed to persist plan for brand {brand_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    return {"plan_id": plan_id, "status": "complete", "days": days}


@app.get("/api/brands/{brand_id}/plans/{plan_id}")
async def get_plan(brand_id: str, plan_id: str):
    """Get a content plan by ID."""
    plan = await firestore_client.get_plan(plan_id, brand_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return {"plan_profile": plan}


@app.put("/api/brands/{brand_id}/plans/{plan_id}/days/{day_index}")
async def update_plan_day(
    brand_id: str,
    plan_id: str,
    day_index: int,
    data: dict = Body(...),
):
    """Update a specific day in a content plan."""
    plan = await firestore_client.get_plan(plan_id, brand_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    days = plan.get("days", [])
    if day_index < 0 or day_index >= len(days):
        raise HTTPException(
            status_code=400,
            detail=f"day_index {day_index} out of range (plan has {len(days)} days)",
        )

    # Remove protected fields from user-supplied data
    safe_data = {k: v for k, v in data.items() if k not in ("day_index", "brand_id", "plan_id")}

    try:
        await firestore_client.update_plan_day(brand_id, plan_id, day_index, safe_data)
    except Exception as e:
        logger.error(f"Failed to update day {day_index} for plan {plan_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    updated_plan = await firestore_client.get_plan(plan_id, brand_id)
    return {"plan_profile": updated_plan}


# ── BYOP — Bring Your Own Photos ─────────────────────────────

_ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


@app.post("/api/brands/{brand_id}/plans/{plan_id}/days/{day_index}/photo")
async def upload_day_photo(
    brand_id: str,
    plan_id: str,
    day_index: int,
    file: UploadFile = File(...),
):
    """Upload a custom photo for a specific calendar day (BYOP).

    Stores the image in GCS and records the signed URL + GCS URI on the
    day's plan document so that content generation later uses the photo
    instead of generating one via Imagen.
    """
    plan = await firestore_client.get_plan(plan_id, brand_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    days = plan.get("days", [])
    if day_index < 0 or day_index >= len(days):
        raise HTTPException(status_code=400, detail=f"day_index {day_index} out of range")

    mime = file.content_type or "image/jpeg"
    if mime not in _ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Only JPEG, PNG, or WebP images are accepted")

    file_bytes = await file.read()
    if len(file_bytes) > 20 * 1024 * 1024:  # 20 MB cap
        raise HTTPException(status_code=400, detail="Image must be smaller than 20 MB")

    try:
        signed_url, gcs_uri = await upload_byop_photo(
            brand_id, plan_id, day_index, file_bytes, mime
        )
    except Exception as e:
        logger.error("BYOP upload failed for brand %s plan %s day %s: %s", brand_id, plan_id, day_index, e)
        raise HTTPException(status_code=500, detail=str(e))

    await firestore_client.update_plan_day(brand_id, plan_id, day_index, {
        "custom_photo_url": signed_url,
        "custom_photo_gcs_uri": gcs_uri,
        "custom_photo_mime": mime,
    })

    return {"custom_photo_url": signed_url, "day_index": day_index}


@app.delete("/api/brands/{brand_id}/plans/{plan_id}/days/{day_index}/photo")
async def delete_day_photo(brand_id: str, plan_id: str, day_index: int):
    """Remove a custom photo from a calendar day, reverting to AI image generation."""
    plan = await firestore_client.get_plan(plan_id, brand_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    days = plan.get("days", [])
    if day_index < 0 or day_index >= len(days):
        raise HTTPException(status_code=400, detail=f"day_index {day_index} out of range")

    await firestore_client.update_plan_day(brand_id, plan_id, day_index, {
        "custom_photo_url": None,
        "custom_photo_gcs_uri": None,
        "custom_photo_mime": None,
    })

    return {"status": "removed", "day_index": day_index}


# ── Interleaved Generation (SSE) ──────────────────────────────
from sse_starlette.sse import EventSourceResponse

from backend.agents.content_creator import generate_post


@app.get("/api/generate/{plan_id}/{day_index}")
async def stream_generate(
    plan_id: str,
    day_index: int,
    brand_id: str = Query(...),
):
    """SSE endpoint: streams interleaved caption + image generation events."""

    # Fetch plan and brand
    plan = await firestore_client.get_plan(plan_id, brand_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    days = plan.get("days", [])
    if day_index < 0 or day_index >= len(days):
        raise HTTPException(status_code=400, detail="day_index out of range")

    day_brief = days[day_index]

    brand = await firestore_client.get_brand(brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    # BYOP: if the day has a custom photo, download it for vision-based generation.
    # We use the gs:// URI (not the stored signed URL) to generate a fresh short-lived
    # signed URL at request time. This avoids both SSRF (no user-controlled URL is
    # fetched) and staleness (the GCS URI never expires).
    custom_photo_bytes: bytes | None = None
    custom_photo_mime = "image/jpeg"
    custom_photo_gcs_uri = day_brief.get("custom_photo_gcs_uri")
    if custom_photo_gcs_uri:
        try:
            fresh_url = await get_signed_url(custom_photo_gcs_uri)
            custom_photo_bytes = await download_from_gcs(fresh_url)
            custom_photo_mime = day_brief.get("custom_photo_mime", "image/jpeg")
        except Exception as e:
            logger.warning("Could not download custom photo for day %s: %s", day_index, e)
            custom_photo_bytes = None  # fall back to normal generation

    # Create a pending post record in Firestore.
    # save_post(brand_id, plan_id, data) generates and returns its own post_id.
    post_id = await firestore_client.save_post(brand_id, plan_id, {
        "day_index": day_index,
        "platform": day_brief.get("platform", "instagram"),
        "status": "generating",
        "caption": "",
        "hashtags": [],
        "image_url": None,
        "byop": custom_photo_bytes is not None,
    })

    async def event_stream():
        final_caption = ""
        final_hashtags = []
        final_image_url = None
        final_image_gcs_uri = None

        async for event in generate_post(
            plan_id, day_brief, brand, post_id,
            custom_photo_bytes=custom_photo_bytes,
            custom_photo_mime=custom_photo_mime,
        ):
            event_name = event["event"]
            event_data = event["data"]

            # Track final values
            if event_name == "caption" and not event_data.get("chunk"):
                final_caption = event_data.get("text", "")
                final_hashtags = event_data.get("hashtags", [])
            elif event_name == "image":
                final_image_url = event_data.get("url")
                final_image_gcs_uri = event_data.get("gcs_uri")
            elif event_name == "complete":
                final_caption = event_data.get("caption", final_caption)
                final_hashtags = event_data.get("hashtags", final_hashtags)
                final_image_url = event_data.get("image_url", final_image_url)
                final_image_gcs_uri = event_data.get("image_gcs_uri", final_image_gcs_uri)

                # Persist complete post to Firestore
                update_data: dict = {
                    "status": "complete",
                    "caption": final_caption,
                    "hashtags": final_hashtags,
                    "image_url": final_image_url,
                }
                if final_image_gcs_uri:
                    update_data["image_gcs_uri"] = final_image_gcs_uri
                await firestore_client.update_post(brand_id, post_id, update_data)
            elif event_name == "error":
                # Mark post as failed so it doesn't stay stuck in "generating"
                await firestore_client.update_post(brand_id, post_id, {
                    "status": "failed",
                })

            yield {
                "event": event_name,
                "data": json.dumps(event_data),
            }

    return EventSourceResponse(event_stream())


# ── Post Review ───────────────────────────────────────────────
from backend.agents.review_agent import review_post as _run_review

_PATCHABLE_POST_FIELDS = {"caption", "hashtags"}


@app.patch("/api/brands/{brand_id}/posts/{post_id}")
async def patch_post_endpoint(brand_id: str, post_id: str, data: dict = Body(...)):
    """Patch individual post fields (caption, hashtags) for inline editing."""
    post = await firestore_client.get_post(brand_id, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    allowed = {k: v for k, v in data.items() if k in _PATCHABLE_POST_FIELDS}
    if not allowed:
        raise HTTPException(status_code=400, detail="No patchable fields provided")
    await firestore_client.update_post(brand_id, post_id, {**allowed, "user_edited": True})
    updated = await firestore_client.get_post(brand_id, post_id)
    return {"post": updated}


@app.post("/api/brands/{brand_id}/posts/{post_id}/review")
async def review_post_endpoint(brand_id: str, post_id: str):
    """AI-review a generated post against brand guidelines."""
    post = await firestore_client.get_post(brand_id, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    brand = await firestore_client.get_brand(brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    result = await _run_review(post, brand)

    # Save review to Firestore
    await firestore_client.save_review(brand_id, post_id, result)

    # If approved, update post status
    if result.get("approved"):
        await firestore_client.update_post(brand_id, post_id, {"status": "approved"})

    # If revised caption provided, update post
    if result.get("revised_caption"):
        await firestore_client.update_post(brand_id, post_id, {
            "caption": result["revised_caption"],
            "review_revised": True,
        })

    return {"review": result, "post_id": post_id}


@app.post("/api/brands/{brand_id}/posts/{post_id}/approve")
async def approve_post_endpoint(brand_id: str, post_id: str):
    """Manually approve a post (user override)."""
    post = await firestore_client.get_post(brand_id, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    await firestore_client.update_post(brand_id, post_id, {"status": "approved"})
    return {"status": "approved", "post_id": post_id}



# ── Video Generation ──────────────────────────────────────────

from backend.agents.video_creator import generate_video_clip
import backend.services.budget_tracker as bt


async def _run_video_generation(
    job_id: str,
    post_id: str,
    brand_id: str,
    hero_image_bytes: bytes,
    post: dict,
    brand: dict,
    tier: str,
):
    """Background task that runs Veo generation and updates Firestore."""
    try:
        await firestore_client.update_video_job(job_id, "generating")
        result = await generate_video_clip(
            hero_image_bytes=hero_image_bytes,
            caption=post.get("caption", ""),
            brand_profile=brand,
            platform=post.get("platform", "instagram"),
            post_id=post_id,
            tier=tier,
        )
        bt.budget_tracker.record_video(tier)
        await firestore_client.update_video_job(job_id, "complete", result)
        # Also update the post with video metadata
        await firestore_client.update_post(brand_id, post_id, {
            "video": {
                "url": result["video_url"],
                "video_gcs_uri": result.get("video_gcs_uri"),
                "duration_seconds": 8,
                "model": result["model"],
                "job_id": job_id,
            }
        })
    except Exception as e:
        logger.error(f"Video generation failed for job {job_id}: {e}")
        await firestore_client.update_video_job(job_id, "failed", {"error": str(e)})


@app.post("/api/posts/{post_id}/generate-video")
async def start_video_generation(
    post_id: str,
    brand_id: str = Query(...),
    tier: str = Query("fast"),
):
    """Queue async Veo video generation for a post that has a hero image.

    Returns: {job_id, status: "processing", estimated_seconds: 150}
    """
    # Check budget
    if not bt.budget_tracker.can_generate_video():
        return JSONResponse(
            status_code=429,
            content={
                "error": "Video generation budget exhausted",
                "budget_status": bt.budget_tracker.get_status(),
            },
        )

    # Load post
    post = await firestore_client.get_post(brand_id, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    # Load brand
    brand = await firestore_client.get_brand(post.get("brand_id", brand_id))
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    # Download hero image from GCS
    image_gcs_uri = post.get("image_gcs_uri")
    if not image_gcs_uri:
        raise HTTPException(
            status_code=400,
            detail="Post has no hero image. Generate the post fully before requesting a video.",
        )

    try:
        signed_url = await get_signed_url(image_gcs_uri)
        hero_image_bytes = await download_from_gcs(signed_url)
    except Exception as e:
        logger.error("Failed to download hero image for post %s: %s", post_id, e)
        raise HTTPException(status_code=500, detail=f"Failed to fetch hero image: {e}")

    # Create job record in Firestore
    job_id = await firestore_client.create_video_job(post_id, tier)

    # Fire background task (non-blocking)
    asyncio.create_task(
        _run_video_generation(job_id, post_id, brand_id, hero_image_bytes, post, brand, tier)
    )

    return {
        "job_id": job_id,
        "status": "processing",
        "estimated_seconds": 150,
    }


@app.get("/api/video-jobs/{job_id}")
async def get_video_job_status(job_id: str):
    """Poll video generation job status.

    Returns the job dict including result.video_url when complete.
    """
    job = await firestore_client.get_video_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Video job not found")
    return job


# ── Voice Coaching (Gemini Live API) ──────────────────────────

@app.websocket("/api/brands/{brand_id}/voice-coaching")
async def voice_coaching_ws(websocket: WebSocket, brand_id: str):
    """Bidirectional voice coaching via Gemini Live API.

    Frontend sends PCM audio (16kHz, 16-bit, mono) as binary WebSocket frames.
    Backend proxies to Gemini Live and returns PCM audio responses (24kHz).

    Control messages sent to frontend:
      { "type": "connected" }            — session ready
      { "type": "transcript", "text" }  — AI text transcript (when available)
      { "type": "error", "message" }    — fatal error
    """
    await websocket.accept()

    brand = await firestore_client.get_brand(brand_id)
    if not brand:
        await websocket.close(code=1008, reason="Brand not found")
        return

    system_prompt = build_coaching_prompt(brand)
    config = _gtypes.LiveConnectConfig(
        response_modalities=["AUDIO"],
        system_instruction=_gtypes.Content(
            parts=[_gtypes.Part(text=system_prompt)]
        ),
        speech_config=_gtypes.SpeechConfig(
            voice_config=_gtypes.VoiceConfig(
                prebuilt_voice_config=_gtypes.PrebuiltVoiceConfig(voice_name="Aoede")
            )
        ),
    )

    try:
        async with _live_client.aio.live.connect(model=_LIVE_MODEL, config=config) as session:
            await websocket.send_json({"type": "connected"})

            async def recv_from_frontend():
                """Forward mic audio from browser → Gemini Live.

                Re-raises on non-disconnect errors so asyncio.wait propagates them.
                Normal return (WebSocketDisconnect) signals the session to end.
                """
                try:
                    while True:
                        msg = await websocket.receive()
                        raw = msg.get("bytes")
                        if raw:
                            await session.send(
                                input=_gtypes.LiveClientRealtimeInput(
                                    media_chunks=[
                                        _gtypes.Blob(
                                            data=raw,
                                            mime_type="audio/pcm;rate=16000",
                                        )
                                    ]
                                )
                            )
                except WebSocketDisconnect:
                    pass  # normal client close — let the task return
                except Exception:
                    logger.exception("recv_from_frontend error for brand %s", brand_id)
                    raise

            async def recv_from_gemini():
                """Forward Gemini audio responses → browser."""
                try:
                    async for response in session.receive():
                        sc = getattr(response, "server_content", None)
                        if not sc:
                            continue

                        # Signal end-of-turn to frontend (so it knows AI finished speaking)
                        if getattr(sc, "turn_complete", False):
                            try:
                                await websocket.send_json({"type": "turn_complete"})
                            except Exception:
                                return

                        model_turn = getattr(sc, "model_turn", None)
                        if not model_turn:
                            continue
                        for part in model_turn.parts:
                            inline = getattr(part, "inline_data", None)
                            if inline and inline.data:
                                try:
                                    await websocket.send_bytes(inline.data)
                                except Exception:
                                    return
                            text = getattr(part, "text", None)
                            if text:
                                try:
                                    await websocket.send_json(
                                        {"type": "transcript", "text": text}
                                    )
                                except Exception:
                                    return
                except asyncio.CancelledError:
                    raise  # let the task framework handle cancellation
                except Exception:
                    logger.exception("recv_from_gemini error for brand %s", brand_id)
                    try:
                        await websocket.send_json(
                            {"type": "error", "message": "Voice session interrupted"}
                        )
                    except Exception:
                        pass

            # BUG-1 fix: use asyncio.wait(FIRST_COMPLETED) so that when either task
            # finishes (frontend disconnect or Gemini session end), the other is
            # explicitly cancelled — preventing zombie Gemini sessions.
            fe_task = asyncio.create_task(recv_from_frontend())
            gm_task = asyncio.create_task(recv_from_gemini())
            try:
                done, pending = await asyncio.wait(
                    [fe_task, gm_task],
                    return_when=asyncio.FIRST_COMPLETED,
                )
            finally:
                for task in (fe_task, gm_task):
                    if not task.done():
                        task.cancel()
                        try:
                            await task
                        except (asyncio.CancelledError, Exception):
                            pass

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error("Voice coaching error for brand %s: %s", brand_id, e)
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass


# ── Static frontend (production) ──────────────────────────────
frontend_dist = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.exists(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
