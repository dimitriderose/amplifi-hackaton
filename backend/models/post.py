from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class ReviewCheck(BaseModel):
    score: float
    feedback: str

class ReviewResult(BaseModel):
    overall_score: float
    approved: bool
    checks: dict  # tone, audience, platform, visual, quality — each with score + feedback
    suggestions: List[str] = []
    reviewed_at: Optional[datetime] = None

class Post(BaseModel):
    post_id: str
    plan_id: str
    brand_id: str
    day_index: int
    platform: str
    caption: str = ""
    image_urls: List[str] = []
    hashtags: List[str] = []
    posting_time: str = ""
    status: str = "draft"  # draft | approved | posted
    image_source: str = "generated"  # generated | user_upload
    review: Optional[ReviewResult] = None
    video_url: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class VideoJob(BaseModel):
    job_id: str
    post_id: str
    status: str = "queued"  # queued | generating | complete | failed
    tier: str = "fast"  # fast | standard
    result: Optional[dict] = None
    error: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
