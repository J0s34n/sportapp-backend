from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import httpx

from app.db.database import get_db
from app.models.user import User, AuthProvider
from app.schemas.user import (
    RegisterRequest, LoginRequest, OAuthRequest,
    TokenResponse, RefreshRequest, UserResponse
)
from app.core.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token
)
from app.core.config import settings

router = APIRouter(prefix="/auth", tags=["Autenticación"])


# ── Registro con email ─────────────────────────────────────

@router.post("/register", response_model=TokenResponse, status_code=201)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="El email ya está registrado")

    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        auth_provider=AuthProvider.EMAIL,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


# ── Login con email ────────────────────────────────────────

@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()

    if not user or not user.hashed_password:
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")

    if not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Cuenta desactivada")

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


# ── Login con Google OAuth ─────────────────────────────────

@router.post("/oauth", response_model=TokenResponse)
async def oauth_login(body: OAuthRequest, db: Session = Depends(get_db)):
    if body.provider == AuthProvider.GOOGLE:
        user_info = await _verify_google_token(body.id_token)
    else:
        raise HTTPException(status_code=400, detail=f"Proveedor '{body.provider}' no soportado aún")

    email = user_info["email"]
    provider_id = user_info["sub"]

    # Buscar usuario existente por email o provider_id
    user = db.query(User).filter(
        (User.email == email) | (User.provider_id == provider_id)
    ).first()

    if not user:
        # Crear cuenta automáticamente al primer login OAuth
        user = User(
            email=email,
            full_name=user_info.get("name"),
            avatar_url=user_info.get("picture"),
            auth_provider=body.provider,
            provider_id=provider_id,
            is_verified=True,   # Google ya verificó el email
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


async def _verify_google_token(id_token: str) -> dict:
    """Verifica el id_token con Google y retorna los datos del usuario."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://oauth2.googleapis.com/tokeninfo",
            params={"id_token": id_token},
        )
    if response.status_code != 200:
        raise HTTPException(status_code=401, detail="Token de Google inválido")

    data = response.json()

    # Verificar que el token fue emitido para nuestra app
    if data.get("aud") != settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=401, detail="Token de Google no pertenece a esta app")

    return data


# ── Refresh token ──────────────────────────────────────────

@router.post("/refresh", response_model=TokenResponse)
def refresh_token(body: RefreshRequest, db: Session = Depends(get_db)):
    payload = decode_token(body.refresh_token)

    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Refresh token inválido o expirado")

    user = db.query(User).filter(User.id == payload["sub"]).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )
