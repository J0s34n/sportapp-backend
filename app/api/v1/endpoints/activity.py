from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date
from datetime import datetime, timezone, date
import json

from app.db.database import get_db
from app.models.user import User, ActivitySession
from app.schemas.activity import (
    ActivitySessionCreate, ActivitySessionEnd,
    ActivitySessionResponse, DailySummary
)
from app.core.dependencies import get_current_user

router = APIRouter(prefix="/activity", tags=["Actividad física"])


# ── Iniciar sesión ─────────────────────────────────────────

@router.post("/sessions", response_model=ActivitySessionResponse, status_code=201)
def start_session(
    body: ActivitySessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = ActivitySession(
        user_id=current_user.id,
        activity_type=body.activity_type,
        started_at=body.started_at,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


# ── Finalizar sesión ───────────────────────────────────────

@router.patch("/sessions/{session_id}", response_model=ActivitySessionResponse)
def end_session(
    session_id: str,
    body: ActivitySessionEnd,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = db.query(ActivitySession).filter(
        ActivitySession.id == session_id,
        ActivitySession.user_id == current_user.id,
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    if session.ended_at:
        raise HTTPException(status_code=400, detail="La sesión ya fue finalizada")

    session.ended_at = body.ended_at
    session.steps = body.steps
    session.distance_km = body.distance_km
    session.calories_burned = body.calories_burned
    session.avg_speed_kmh = body.avg_speed_kmh
    session.duration_seconds = (body.ended_at - session.started_at).total_seconds()

    if body.gps_route:
        session.gps_route = json.dumps([p.model_dump() for p in body.gps_route])

    db.commit()
    db.refresh(session)
    return session


# ── Historial de sesiones ──────────────────────────────────

@router.get("/sessions", response_model=list[ActivitySessionResponse])
def get_sessions(
    limit: int = Query(default=20, le=100),
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sessions = (
        db.query(ActivitySession)
        .filter(ActivitySession.user_id == current_user.id)
        .order_by(ActivitySession.started_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return sessions


# ── Detalle de sesión ──────────────────────────────────────

@router.get("/sessions/{session_id}", response_model=ActivitySessionResponse)
def get_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = db.query(ActivitySession).filter(
        ActivitySession.id == session_id,
        ActivitySession.user_id == current_user.id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    return session


# ── Resumen del día (dashboard) ────────────────────────────

@router.get("/summary/today", response_model=DailySummary)
def get_today_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    today = date.today()
    return _build_summary(db, current_user, today)


@router.get("/summary/{day}", response_model=DailySummary)
def get_day_summary(
    day: date,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _build_summary(db, current_user, day)


def _build_summary(db: Session, user: User, day: date) -> DailySummary:
    sessions = (
        db.query(ActivitySession)
        .filter(
            ActivitySession.user_id == user.id,
            cast(ActivitySession.started_at, Date) == day,
            ActivitySession.ended_at.isnot(None),
        )
        .all()
    )

    total_steps = sum(s.steps or 0 for s in sessions)
    total_calories = sum(s.calories_burned or 0 for s in sessions)
    total_distance = sum(s.distance_km or 0 for s in sessions)
    total_duration = sum(s.duration_seconds or 0 for s in sessions) / 60

    steps_goal = user.daily_steps_goal or 10000
    calories_goal = user.daily_calories_goal or 500

    return DailySummary(
        date=str(day),
        total_steps=round(total_steps),
        total_calories=round(total_calories, 1),
        total_distance_km=round(total_distance, 2),
        total_duration_minutes=round(total_duration, 1),
        sessions_count=len(sessions),
        steps_goal=steps_goal,
        calories_goal=calories_goal,
        steps_progress_pct=min(round(total_steps / steps_goal * 100, 1), 100),
        calories_progress_pct=min(round(total_calories / calories_goal * 100, 1), 100),
    )


# ── Progreso semanal (para gráficas) ──────────────────────

@router.get("/progress/weekly")
def get_weekly_progress(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = (
        db.query(
            cast(ActivitySession.started_at, Date).label("day"),
            func.sum(ActivitySession.steps).label("steps"),
            func.sum(ActivitySession.calories_burned).label("calories"),
            func.sum(ActivitySession.distance_km).label("distance_km"),
        )
        .filter(
            ActivitySession.user_id == current_user.id,
            ActivitySession.ended_at.isnot(None),
        )
        .group_by(cast(ActivitySession.started_at, Date))
        .order_by(cast(ActivitySession.started_at, Date).desc())
        .limit(7)
        .all()
    )

    return [
        {
            "date": str(r.day),
            "steps": round(r.steps or 0),
            "calories": round(r.calories or 0, 1),
            "distance_km": round(r.distance_km or 0, 2),
        }
        for r in rows
    ]
