from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

class RoadmapModel(BaseModel):
    """
    Domain entity for Roadmaps table.
    """
    id: Optional[str] = None
    profile_id: str
    roadmap_data: Dict[str, Any]
    duration_weeks: int = 4
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
