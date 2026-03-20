from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from app.models.user import ActivityType


class GPSPoint(BaseModel):
    lat: float
    lng: float
    ts: int    # timestamp unix en milisegundos


class ActivitySessionCreate(BaseModel):
    activity_type: ActivityType
    started_at: datetime


class ActivitySessionEnd(BaseModel):
    ended_at: datetime
    steps: float = 0
    distance_km: float = 0
    calories_burned: float = 0
    avg_speed_kmh: Optional[float] = None
    gps_route: Optional[List[GPSPoint]] = None


class ActivitySessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    activity_type: ActivityType
    started_at: datetime
    ended_at: Optional[datetime]
    duration_seconds: Optional[float]
    steps: float
    distance_km: float
    calories_burned: float
    avg_speed_kmh: Optional[float]
    created_at: datetime


class DailySummary(BaseModel):
    date: str
    total_steps: float
    total_calories: float
    total_distance_km: float
    total_duration_minutes: float
    sessions_count: int
    steps_goal: float
    calories_goal: float
    steps_progress_pct: float
    calories_progress_pct: float
