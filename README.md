# SportApp Backend

API REST construida con FastAPI + PostgreSQL (Supabase) para la app móvil de monitoreo de actividad física.

## Estructura del proyecto

```
sportapp-backend/
├── main.py                        # Punto de entrada
├── requirements.txt
├── .env.example                   # Copia a .env y configura
└── app/
    ├── api/v1/endpoints/
    │   ├── auth.py                # Registro, login, OAuth, refresh
    │   ├── users.py               # Perfil, IMC, registro de peso
    │   └── activity.py            # Sesiones, dashboard, progreso
    ├── core/
    │   ├── config.py              # Variables de entorno (Pydantic Settings)
    │   ├── security.py            # JWT, bcrypt
    │   └── dependencies.py        # get_current_user
    ├── db/
    │   └── database.py            # SQLAlchemy engine + sesión
    ├── models/
    │   └── user.py                # User, ActivitySession, WeightLog
    └── schemas/
        ├── user.py                # Schemas de auth y perfil
        └── activity.py            # Schemas de sesiones y dashboard
```

## Setup rápido (local)

### 1. Clonar e instalar dependencias

```bash
git clone <tu-repo>
cd sportapp-backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configurar variables de entorno

```bash
cp .env.example .env
# Edita .env con tu DATABASE_URL de Supabase y tu SECRET_KEY
```

Genera una SECRET_KEY segura con:
```bash
openssl rand -hex 32
```

### 3. Crear la base de datos en Supabase

1. Ve a [supabase.com](https://supabase.com) y crea un proyecto gratis
2. En **Project Settings > Database** copia la "Connection string (URI)"
3. Pégala en `DATABASE_URL` dentro de tu `.env`

### 4. Correr el servidor

```bash
uvicorn main:app --reload
```

La API queda disponible en:
- **Documentación interactiva:** http://localhost:8000/docs
- **Health check:** http://localhost:8000/health

---

## Endpoints disponibles

### Autenticación (`/api/v1/auth`)

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/auth/register` | Registro con email y contraseña |
| POST | `/auth/login` | Login con email y contraseña |
| POST | `/auth/oauth` | Login con Google (id_token de Flutter) |
| POST | `/auth/refresh` | Renovar access token |

### Usuarios (`/api/v1/users`)

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/users/me` | Obtener perfil propio |
| PATCH | `/users/me` | Actualizar perfil |
| GET | `/users/me/imc` | Calcular IMC con categoría OMS |
| POST | `/users/me/weight` | Registrar peso del día |
| GET | `/users/me/weight/history` | Historial de peso (últimos 30) |

### Actividad física (`/api/v1/activity`)

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/activity/sessions` | Iniciar sesión de actividad |
| PATCH | `/activity/sessions/{id}` | Finalizar sesión con métricas |
| GET | `/activity/sessions` | Historial de sesiones |
| GET | `/activity/sessions/{id}` | Detalle de una sesión |
| GET | `/activity/summary/today` | Resumen del día para dashboard |
| GET | `/activity/summary/{date}` | Resumen de una fecha específica |
| GET | `/activity/progress/weekly` | Progreso de los últimos 7 días |

---

## Despliegue en Railway (gratis)

1. Sube el proyecto a GitHub
2. Ve a [railway.app](https://railway.app) → **New Project → Deploy from GitHub**
3. Selecciona tu repo
4. En **Variables**, agrega todas las del `.env.example`
5. Railway detecta automáticamente que es Python y corre `uvicorn main:app`

Agrega este archivo para que Railway sepa el comando de inicio:

```
# Procfile
web: uvicorn main:app --host 0.0.0.0 --port $PORT
```

---

## Flujo de autenticación desde Flutter

```
1. Usuario toca "Registrarse" → POST /auth/register → guarda access_token + refresh_token
2. Al abrir la app → usa access_token en header: Authorization: Bearer <token>
3. Si recibe 401 → llama POST /auth/refresh con refresh_token → obtiene nuevos tokens
4. Login con Google → google_sign_in Flutter → obtiene id_token → POST /auth/oauth
```

---

## Próximos pasos sugeridos

- [ ] Agregar Alembic para migraciones de base de datos
- [ ] Implementar notificaciones push con Firebase Admin SDK
- [ ] Agregar endpoint de exportación PDF de reportes
- [ ] Configurar rate limiting con `slowapi`
- [ ] Agregar tests con pytest
