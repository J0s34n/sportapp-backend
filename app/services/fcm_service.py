import json
import os
import base64
import httpx
from datetime import datetime, timezone


class FCMService:
    FCM_URL = "https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"
    TOKEN_URL = "https://oauth2.googleapis.com/token"

    def __init__(self):
        self._credentials = None
        self._access_token = None
        self._token_expiry = None

    def _load_credentials(self) -> dict:
        if self._credentials is not None:
            return self._credentials

        # Intentar FIREBASE_B64 primero (más confiable en Railway)
        raw_b64 = os.environ.get("FIREBASE_B64", "")
        if raw_b64:
            decoded = base64.b64decode(raw_b64).decode("utf-8")
            self._credentials = json.loads(decoded)
            return self._credentials

        # Fallback: FIREBASE_CREDENTIALS_B64
        raw_b64 = os.environ.get("FIREBASE_CREDENTIALS_B64", "")
        if raw_b64:
            decoded = base64.b64decode(raw_b64).decode("utf-8")
            self._credentials = json.loads(decoded)
            return self._credentials

        # Fallback: JSON directo
        raw = os.environ.get("FIREBASE_CREDENTIALS", "")
        if raw:
            self._credentials = json.loads(raw)
            return self._credentials

        raise ValueError(
            "No se encontró configuración de Firebase. "
            "Configura FIREBASE_B64 en Railway."
        )

    async def _get_access_token(self) -> str:
        now = datetime.now(timezone.utc).timestamp()
        if self._access_token and self._token_expiry and now < self._token_expiry - 60:
            return self._access_token

        import jwt as pyjwt
        creds = self._load_credentials()

        iat = int(now)
        exp = iat + 3600
        payload = {
            "iss": creds["client_email"],
            "sub": creds["client_email"],
            "aud": self.TOKEN_URL,
            "iat": iat,
            "exp": exp,
            "scope": "https://www.googleapis.com/auth/firebase.messaging",
        }
        signed_jwt = pyjwt.encode(
            payload, creds["private_key"], algorithm="RS256"
        )

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.TOKEN_URL,
                data={
                    "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                    "assertion": signed_jwt,
                },
            )
            data = response.json()
            self._access_token = data["access_token"]
            self._token_expiry = now + data.get("expires_in", 3600)

        return self._access_token

    async def send(self, fcm_token: str, title: str, body: str, data: dict | None = None) -> bool:
        try:
            creds = self._load_credentials()
            access_token = await self._get_access_token()
            url = self.FCM_URL.format(project_id=creds["project_id"])

            message = {
                "message": {
                    "token": fcm_token,
                    "notification": {"title": title, "body": body},
                    "android": {
                        "notification": {"sound": "default", "priority": "HIGH"}
                    },
                    **({"data": {k: str(v) for k, v in data.items()}} if data else {}),
                }
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json=message,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json",
                    },
                )
                if response.status_code != 200:
                    raise Exception(f"FCM status {response.status_code}: {response.text}")
                return True
        except Exception as e:
            raise Exception(f"FCM error: {e}")

    async def notify_goal_reached(self, fcm_token: str, goal_type: str, value: float) -> bool:
        if goal_type == "steps":
            return await self.send(
                fcm_token,
                title="¡Meta de pasos alcanzada! 🎉",
                body=f"Completaste {int(value):,} pasos hoy. ¡Excelente trabajo!",
                data={"type": "goal_steps"},
            )
        elif goal_type == "calories":
            return await self.send(
                fcm_token,
                title="¡Meta de calorías alcanzada! 🔥",
                body=f"Quemaste {int(value)} kcal hoy. ¡Sigue así!",
                data={"type": "goal_calories"},
            )
        return False

    async def notify_activity_reminder(self, fcm_token: str) -> bool:
        return await self.send(
            fcm_token,
            title="¡Hora de moverse! 🏃",
            body="No olvides registrar tu actividad física de hoy.",
            data={"type": "reminder"},
        )

    async def notify_health_alert(self, fcm_token: str, message: str) -> bool:
        return await self.send(
            fcm_token,
            title="Alerta de salud ⚠️",
            body=message,
            data={"type": "health_alert"},
        )


fcm_service = FCMService()