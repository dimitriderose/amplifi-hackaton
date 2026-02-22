from pydantic import BaseModel
from typing import Optional, Any

class APIResponse(BaseModel):
    success: bool = True
    data: Optional[Any] = None
    error: Optional[str] = None

class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "amplifi-backend"
    version: str = "1.0.0"
