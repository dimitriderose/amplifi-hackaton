from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class Pillar(BaseModel):
    id: str
    theme: str
    key_message: str
    source: str = "generated"  # "event" | "generated"
    derivative_count: int = 0

class DayBrief(BaseModel):
    day_index: int
    day_name: str
    platform: str  # instagram | linkedin | x | tiktok | facebook
    theme: str
    content_type: str  # photo | carousel | story | reel | thread
    caption_direction: str
    image_direction: str
    posting_time: str
    pillar_id: Optional[str] = None
    derivative_type: Optional[str] = None  # original | condensed | visual | conversational | engagement | standalone
    pillar_context: Optional[str] = None
    user_photo_url: Optional[str] = None
    image_source: str = "generated"  # generated | user_upload
    generated: bool = False
    post_id: Optional[str] = None
    status: str = "planned"  # planned | generated | approved | posted

class ContentPlanCreate(BaseModel):
    brand_id: str
    goals: Optional[str] = None
    platforms: Optional[List[str]] = ["instagram"]
    business_events: Optional[str] = None

class ContentPlan(BaseModel):
    plan_id: str
    brand_id: str
    week_of: str
    goals: Optional[str] = None
    business_events: Optional[str] = None
    platforms: List[str] = []
    pillars: List[Pillar] = []
    days: List[DayBrief] = []
    status: str = "draft"  # draft | generating | complete
    created_at: Optional[datetime] = None
