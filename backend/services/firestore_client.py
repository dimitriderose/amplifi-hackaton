import uuid
from datetime import datetime, timezone
from typing import Optional
from google.cloud import firestore
from google.cloud.firestore_v1.async_client import AsyncClient

_client: Optional[AsyncClient] = None

def get_client() -> AsyncClient:
    global _client
    if _client is None:
        _client = firestore.AsyncClient()
    return _client

# ── Brand operations ──────────────────────────────────────────

async def create_brand(data: dict) -> str:
    db = get_client()
    brand_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    doc = {
        **data,
        "brand_id": brand_id,
        "analysis_status": "pending",
        "created_at": now,
        "updated_at": now,
    }
    await db.collection("brands").document(brand_id).set(doc)
    return brand_id

async def get_brand(brand_id: str) -> Optional[dict]:
    db = get_client()
    doc = await db.collection("brands").document(brand_id).get()
    return doc.to_dict() if doc.exists else None

async def update_brand(brand_id: str, data: dict) -> None:
    db = get_client()
    await db.collection("brands").document(brand_id).update({
        **data,
        "updated_at": datetime.now(timezone.utc),
    })

# ── Content plan operations ───────────────────────────────────

async def create_plan(brand_id: str, data: dict) -> str:
    db = get_client()
    plan_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    doc = {**data, "plan_id": plan_id, "brand_id": brand_id, "created_at": now}
    await (db.collection("brands").document(brand_id)
             .collection("content_plans").document(plan_id).set(doc))
    return plan_id

async def list_plans(brand_id: str) -> list:
    db = get_client()
    docs = await (db.collection("brands").document(brand_id)
                    .collection("content_plans")
                    .order_by("created_at", direction="DESCENDING")
                    .get())
    return [d.to_dict() for d in docs]

async def get_plan(plan_id: str, brand_id: str) -> Optional[dict]:
    db = get_client()
    # Try to find plan across all brands if brand_id not provided
    doc = await (db.collection("brands").document(brand_id)
                   .collection("content_plans").document(plan_id).get())
    return doc.to_dict() if doc.exists else None

async def update_plan(brand_id: str, plan_id: str, data: dict) -> None:
    db = get_client()
    await (db.collection("brands").document(brand_id)
             .collection("content_plans").document(plan_id).update(data))

async def update_plan_day(brand_id: str, plan_id: str, day_index: int, data: dict) -> None:
    db = get_client()
    plan_ref = (db.collection("brands").document(brand_id)
                  .collection("content_plans").document(plan_id))
    plan_doc = await plan_ref.get()
    if plan_doc.exists:
        days = plan_doc.to_dict().get("days", [])
        if 0 <= day_index < len(days):
            days[day_index].update(data)
            await plan_ref.update({"days": days})

# ── Post operations ───────────────────────────────────────────

async def save_post(brand_id: str, plan_id: str, data: dict) -> str:
    db = get_client()
    post_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    doc = {**data, "post_id": post_id, "brand_id": brand_id, "plan_id": plan_id,
           "created_at": now, "updated_at": now}
    await (db.collection("brands").document(brand_id)
             .collection("posts").document(post_id).set(doc))
    return post_id

async def get_post(brand_id: str, post_id: str) -> Optional[dict]:
    db = get_client()
    doc = await (db.collection("brands").document(brand_id)
                   .collection("posts").document(post_id).get())
    return doc.to_dict() if doc.exists else None

async def update_post(brand_id: str, post_id: str, data: dict) -> None:
    db = get_client()
    await (db.collection("brands").document(brand_id)
             .collection("posts").document(post_id).update({
                 **data,
                 "updated_at": datetime.now(timezone.utc),
             }))

async def list_posts(brand_id: str, plan_id: Optional[str] = None) -> list:
    db = get_client()
    ref = db.collection("brands").document(brand_id).collection("posts")
    if plan_id:
        ref = ref.where("plan_id", "==", plan_id)
    docs = await ref.get()
    return [d.to_dict() for d in docs]

# ── Video job operations ──────────────────────────────────────

async def create_video_job(post_id: str, tier: str) -> str:
    db = get_client()
    job_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    await db.collection("video_jobs").document(job_id).set({
        "job_id": job_id, "post_id": post_id, "tier": tier,
        "status": "queued", "result": None, "error": None,
        "created_at": now, "updated_at": now,
    })
    return job_id

async def update_video_job(job_id: str, status: str, result: Optional[dict] = None) -> None:
    db = get_client()
    await db.collection("video_jobs").document(job_id).update({
        "status": status,
        "result": result,
        "updated_at": datetime.now(timezone.utc),
    })

async def get_video_job(job_id: str) -> Optional[dict]:
    db = get_client()
    doc = await db.collection("video_jobs").document(job_id).get()
    return doc.to_dict() if doc.exists else None

async def save_review(brand_id: str, post_id: str, review: dict) -> None:
    db = get_client()
    await (db.collection("brands").document(brand_id)
             .collection("posts").document(post_id).update({
                 "review": review,
                 "updated_at": datetime.now(timezone.utc),
             }))


# ── Platform trends cache ──────────────────────────────────────

async def get_platform_trends(platform: str, industry: str) -> Optional[dict]:
    """Return cached trend data for platform+industry if not expired (7-day TTL)."""
    db = get_client()
    doc_id = f"{platform}_{industry}".lower().replace(" ", "_")
    snap = await db.collection("platform_trends").document(doc_id).get()
    if not snap.exists:
        return None
    data = snap.to_dict()
    expires_at = data.get("expires_at")
    if expires_at and datetime.now(timezone.utc) > expires_at:
        return None
    return data.get("trends")


async def save_platform_trends(platform: str, industry: str, trends: dict) -> None:
    """Cache trend data for platform+industry with a 7-day TTL."""
    from datetime import timedelta
    db = get_client()
    doc_id = f"{platform}_{industry}".lower().replace(" ", "_")
    now = datetime.now(timezone.utc)
    await db.collection("platform_trends").document(doc_id).set({
        "trends": trends,
        "fetched_at": now,
        "expires_at": now + timedelta(days=7),
    })
