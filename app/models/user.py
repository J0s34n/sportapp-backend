from sqlalchemy import Column, String, Float, Boolean, DateTime, ForeignKey, Enum, Text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, timezone
import uuid
import enum

from app.db.database import Base


class AuthProvider(str, enum.Enum):
    EMAIL = "email"
    GOOGLE = "google"
    FACEBOOK = "facebook"
    APPLE = "apple"


class ActivityType(str, enum.Enum):
    WALKING = "walking"
    RUNNING = "running"
    CYCLING = "cycling"
    SWIMMING = "swimming"
    GYM = "gym"
    OTHER = "other"


class HealthCondition(str, enum.Enum):
    NONE = "none"
    HYPERTENSION = "hypertension"
    DIABETES = "diabetes"
    CARDIAC = "cardiac"
    OTHER = "other"


# ── Usuario ────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=True)   # null si usa OAuth
    auth_provider = Column(Enum(AuthProvider), default=AuthProvider.EMAIL)
    provider_id = Column(String(255), nullable=True)       # ID externo de OAuth

    # Perfil
    full_name = Column(String(100), nullable=True)
    avatar_url = Column(Text, nullable=True)
    birth_date = Column(DateTime, nullable=True)
    gender = Column(String(10), nullable=True)

    # Métricas de salud
    weight_kg = Column(Float, nullable=True)
    height_cm = Column(Float, nullable=True)
    health_condition = Column(Enum(HealthCondition), default=HealthCondition.NONE)
    max_heart_rate = Column(Float, nullable=True)          # para alertas personalizadas

    # Metas
    daily_steps_goal = Column(Float, default=10000)
    daily_calories_goal = Column(Float, default=500)

    # Control
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    # Relaciones
    activity_sessions = relationship("ActivitySession", back_populates="user", cascade="all, delete-orphan")
    weight_logs = relationship("WeightLog", back_populates="user", cascade="all, delete-orphan")


# ── Sesión de actividad ────────────────────────────────────

class ActivitySession(Base):
    __tablename__ = "activity_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    activity_type = Column(Enum(ActivityType), nullable=False)
    started_at = Column(DateTime, nullable=False)
    ended_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)

    # Métricas calculadas
    steps = Column(Float, default=0)
    distance_km = Column(Float, default=0)
    calories_burned = Column(Float, default=0)
    avg_speed_kmh = Column(Float, nullable=True)

    # Ruta GPS (lista de puntos JSON guardada como texto)
    gps_route = Column(Text, nullable=True)   # JSON: [{"lat":x,"lng":y,"ts":z}, ...]

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="activity_sessions")


# ── Registro de peso ───────────────────────────────────────

class WeightLog(Base):
    __tablename__ = "weight_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    weight_kg = Column(Float, nullable=False)
    recorded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="weight_logs")
