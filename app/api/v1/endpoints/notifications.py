from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.database import get_db
from app.models.user import User
from app.core.dependencies import get_current_user
from app.services.fcm_service import fcm_service

router = APIRouter(prefix="/notifications", tags=["Notificaciones"])


# ── Schemas ────────────────────────────────────────────────

class FCMTokenUpdate(BaseModel):
    fcm_token: str


class NotificationTest(BaseModel):
    type: str  # "goal_steps" | "goal_calories" | "reminder" | "health_alert"
    value: float = 0
    message: str = ""


# ── Guardar FCM token del dispositivo ─────────────────────

@router.post("/token")
def save_fcm_token(
    body: FCMTokenUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    current_user.fcm_token = body.fcm_token
    db.commit()
    return {"status": "ok"}


# ── Enviar notificación de prueba ──────────────────────────

@router.post("/test")
async def send_test_notification(
    body: NotificationTest,
    current_user: User = Depends(get_current_user),
):
    if not current_user.fcm_token:
        raise HTTPException(
            status_code=400,
            detail="El usuario no tiene FCM token registrado"
        )

    token = current_user.fcm_token
    sent = False

    if body.type == "goal_steps":
        sent = await fcm_service.notify_goal_reached(token, "steps", body.value)
    elif body.type == "goal_calories":
        sent = await fcm_service.notify_goal_reached(token, "calories", body.value)
    elif body.type == "reminder":
        sent = await fcm_service.notify_activity_reminder(token)
    elif body.type == "health_alert":
        sent = await fcm_service.notify_health_alert(token, body.message)
    else:
        raise HTTPException(status_code=400, detail="Tipo de notificación inválido")

    if not sent:
        raise HTTPException(status_code=500, detail="Error enviando notificación")

    return {"status": "sent"}


# ── Trigger automático al completar meta ───────────────────
# (llámalo desde activity.py cuando steps_progress_pct >= 100)

async def check_and_notify_goals(user: User, summary: dict):
    if not user.fcm_token:
        return
    if summary.get("steps_progress_pct", 0) >= 100:
        await fcm_service.notify_goal_reached(
            user.fcm_token, "steps", summary["total_steps"]
        )
    if summary.get("calories_progress_pct", 0) >= 100:
        await fcm_service.notify_goal_reached(
            user.fcm_token, "calories", summary["total_calories"]
        )
