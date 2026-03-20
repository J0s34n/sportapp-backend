from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional
from datetime import datetime
from uuid import UUID
from app.models.user import AuthProvider, HealthCondition


# ── Auth ───────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class OAuthRequest(BaseModel):
    provider: AuthProvider
    id_token: str          # token que llega desde Flutter tras el login social


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


# ── Perfil de usuario ──────────────────────────────────────

class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    birth_date: Optional[datetime] = None
    gender: Optional[str] = None
    weight_kg: Optional[float] = Field(default=None, gt=0, lt=500)
    height_cm: Optional[float] = Field(default=None, gt=0, lt=300)
    health_condition: Optional[HealthCondition] = None
    max_heart_rate: Optional[float] = Field(default=None, gt=0, lt=300)
    daily_steps_goal: Optional[float] = Field(default=None, gt=0)
    daily_calories_goal: Optional[float] = Field(default=None, gt=0)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    full_name: Optional[str]
    avatar_url: Optional[str]
    weight_kg: Optional[float]
    height_cm: Optional[float]
    health_condition: HealthCondition
    daily_steps_goal: float
    daily_calories_goal: float
    is_verified: bool
    created_at: datetime

    @property
    def imc(self) -> Optional[float]:
        if self.weight_kg and self.height_cm:
            height_m = self.height_cm / 100
            return round(self.weight_kg / (height_m ** 2), 1)
        return None


# ── Registro de peso ───────────────────────────────────────

class WeightLogCreate(BaseModel):
    weight_kg: float = Field(gt=0, lt=500)


class WeightLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    weight_kg: float
    recorded_at: datetime
