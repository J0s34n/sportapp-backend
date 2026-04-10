from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
import traceback

from app.db.database import get_db
from app.models.user import User
from app.core.dependencies import get_current_user
from app.services.fcm_service import fcm_service

router = APIRouter(prefix="/notifications", tags=["Notificaciones"])


class FCMTokenUpdate(BaseModel):
    fcm_token: str


class NotificationTest(BaseModel):
    type: str
    value: float = 0
    message: str = ""


@router.post("/token")
def save_fcm_token(
    body: FCMTokenUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    current_user.fcm_token = body.fcm_token
    db.commit()
    return {"status": "ok"}


@router.post("/test")
async def send_test_notification(
    body: NotificationTest,
    current_user: User = Depends(get_current_user),
):
    if not current_user.fcm_token:
        raise HTTPException(status_code=400, detail="Usuario sin FCM token")

    token = current_user.fcm_token
    try:
        if body.type == "goal_steps":
            sent = await fcm_service.notify_goal_reached(token, "steps", body.value)
        elif body.type == "goal_calories":
            sent = await fcm_service.notify_goal_reached(token, "calories", body.value)
        elif body.type == "reminder":
            sent = await fcm_service.notify_activity_reminder(token)
        elif body.type == "health_alert":
            sent = await fcm_service.notify_health_alert(token, body.message)
        else:
            raise HTTPException(status_code=400, detail="Tipo inválido")

        if not sent:
            raise HTTPException(status_code=500, detail="FCM respondió con error")

        return {"status": "sent"}

    except HTTPException:
        raise
    except Exception as e:
        # Mostrar error completo en respuesta (solo para debug)
        raise HTTPException(
            status_code=500,
            detail=f"Error: {str(e)} | Traceback: {traceback.format_exc()}"
        )


@router.get("/debug-config")
def debug_config():
    import os
    b64 = os.environ.get("FIREBASE_B64", "EMPTY")
    b64_long = os.environ.get("FIREBASE_CREDENTIALS_B64", "EMPTY")
    return {
        "FIREBASE_B64": {"length": len(b64), "first_10": b64[:10]},
        "FIREBASE_CREDENTIALS_B64": {"length": len(b64_long), "first_10": b64_long[:10]},
        "all_firebase_keys": [k for k in os.environ if "FIREBASE" in k],
    }


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