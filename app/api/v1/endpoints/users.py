from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.db.database import get_db
from app.models.user import User, WeightLog
from app.schemas.user import UserResponse, UserProfileUpdate, WeightLogCreate, WeightLogResponse
from app.core.dependencies import get_current_user

router = APIRouter(prefix="/users", tags=["Usuarios"])


# ── Perfil propio ──────────────────────────────────────────

@router.get("/me", response_model=UserResponse)
def get_my_profile(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=UserResponse)
def update_my_profile(
    body: UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(current_user, field, value)
    current_user.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(current_user)
    return current_user


# ── IMC ────────────────────────────────────────────────────

@router.get("/me/imc")
def get_imc(current_user: User = Depends(get_current_user)):
    if not current_user.weight_kg or not current_user.height_cm:
        raise HTTPException(
            status_code=400,
            detail="Completa tu peso y talla en el perfil para calcular el IMC"
        )
    height_m = current_user.height_cm / 100
    imc = round(current_user.weight_kg / (height_m ** 2), 1)

    if imc < 18.5:
        category = "Bajo peso"
    elif imc < 25:
        category = "Normal"
    elif imc < 30:
        category = "Sobrepeso"
    else:
        category = "Obesidad"

    return {
        "imc": imc,
        "category": category,
        "weight_kg": current_user.weight_kg,
        "height_cm": current_user.height_cm,
    }


# ── Registro de peso ───────────────────────────────────────

@router.post("/me/weight", response_model=WeightLogResponse, status_code=201)
def log_weight(
    body: WeightLogCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Actualizar peso actual en el perfil también
    current_user.weight_kg = body.weight_kg
    log = WeightLog(user_id=current_user.id, weight_kg=body.weight_kg)
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


@router.get("/me/weight/history", response_model=list[WeightLogResponse])
def get_weight_history(
    limit: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    logs = (
        db.query(WeightLog)
        .filter(WeightLog.user_id == current_user.id)
        .order_by(WeightLog.recorded_at.desc())
        .limit(limit)
        .all()
    )
    return logs
