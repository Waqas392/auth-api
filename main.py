import logging
import os
from typing import Optional

import httpx
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from supabase import Client, create_client
from supabase_auth.errors import AuthApiError

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("auth-api")

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
PORT = int(os.getenv("PORT", "8000"))

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError(
        "Set SUPABASE_URL and SUPABASE_KEY in your .env file."
    )

app = FastAPI(
    title="Auth - Login & Protect",
    version="1.1.0",
    description="FastAPI authentication with Supabase Auth and JWT verification.",
)

bearer_scheme = HTTPBearer(auto_error=False)


def get_client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)


@app.exception_handler(HTTPException)
async def http_error_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail},
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    request: Request,
    exc: RequestValidationError,
):
    return JSONResponse(
        status_code=400,
        content={"error": "Invalid request body or field values."},
    )


class Credentials(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    email: EmailStr
    password: str = Field(min_length=1)


class RefreshBody(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    refresh_token: str = Field(min_length=1)


def safe_user(user) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "created_at": str(user.created_at),
    }


def token_payload(session) -> dict:
    return {
        "access_token": session.access_token,
        "refresh_token": session.refresh_token,
        "token_type": "bearer",
        "expires_in": session.expires_in,
    }


def get_current_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
):
    if creds is None or not creds.credentials.strip():
        raise HTTPException(
            status_code=401,
            detail="Access token required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = creds.credentials.strip()

    try:
        result = get_client().auth.get_user(token)
        user = result.user if result else None
    except AuthApiError:
        user = None
    except Exception:
        logger.exception("Supabase token verification failed.")
        raise HTTPException(
            status_code=502,
            detail="Authentication service is temporarily unavailable",
        )

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {"user": user, "token": token}


def require_admin(ctx=Depends(get_current_user)):
    app_metadata = ctx["user"].app_metadata or {}

    if app_metadata.get("role") != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required",
        )

    return ctx


@app.post("/auth/signup", status_code=201, tags=["auth"])
def signup(body: Credentials):
    try:
        result = get_client().auth.sign_up(
            {
                "email": str(body.email),
                "password": body.password,
            }
        )
    except AuthApiError:
        raise HTTPException(
            status_code=400,
            detail="Signup failed. Check the supplied details or account status.",
        )
    except Exception:
        logger.exception("Supabase signup service failed.")
        raise HTTPException(
            status_code=502,
            detail="Authentication service is temporarily unavailable",
        )

    if not result or not result.user:
        raise HTTPException(
            status_code=400,
            detail="Signup could not be completed. Check your account status.",
        )

    return {"user": safe_user(result.user)}


@app.post("/auth/login", tags=["auth"])
def login(body: Credentials):
    try:
        result = get_client().auth.sign_in_with_password(
            {
                "email": str(body.email),
                "password": body.password,
            }
        )
    except AuthApiError:
        raise HTTPException(
            status_code=401,
            detail="Invalid login credentials",
        )
    except Exception:
        logger.exception("Supabase login service failed.")
        raise HTTPException(
            status_code=502,
            detail="Authentication service is temporarily unavailable",
        )

    if not result or not result.session:
        raise HTTPException(
            status_code=401,
            detail="Invalid login credentials",
        )

    return token_payload(result.session)


@app.post("/auth/logout", status_code=204, tags=["auth"])
def logout(ctx=Depends(get_current_user)):
    try:
        response = httpx.post(
            f"{SUPABASE_URL}/auth/v1/logout",
            params={"scope": "global"},
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {ctx['token']}",
            },
            timeout=10.0,
        )
    except httpx.RequestError:
        logger.exception("Supabase logout request failed.")
        raise HTTPException(
            status_code=502,
            detail="Logout service is temporarily unavailable",
        )

    if response.status_code in (200, 204):
        return Response(status_code=204)

    if response.status_code in (401, 403):
        logger.warning(
            "Supabase rejected the logout request with HTTP %s.",
            response.status_code,
        )
        raise HTTPException(
            status_code=502,
            detail="Logout service is temporarily unavailable",
        )

    logger.warning(
        "Supabase logout returned HTTP %s.",
        response.status_code,
    )
    raise HTTPException(
        status_code=502,
        detail="Logout service is temporarily unavailable",
    )


@app.post("/auth/refresh", tags=["auth"])
def refresh(body: RefreshBody):
    try:
        result = get_client().auth.refresh_session(body.refresh_token)
    except AuthApiError:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired refresh token",
        )
    except Exception:
        logger.exception("Supabase refresh service failed.")
        raise HTTPException(
            status_code=502,
            detail="Authentication service is temporarily unavailable",
        )

    if not result or not result.session:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired refresh token",
        )

    return token_payload(result.session)


@app.get("/public/info", tags=["public"])
def public_info():
    return {"message": "Welcome stranger! This info is public."}


@app.get("/protected/profile", tags=["protected"])
def profile(ctx=Depends(get_current_user)):
    return safe_user(ctx["user"])


@app.get("/protected/dashboard", tags=["protected"])
def dashboard(ctx=Depends(get_current_user)):
    return {"message": f"Welcome back, {ctx['user'].email}!"}


@app.get("/admin/stats", tags=["admin"])
def admin_stats(ctx=Depends(require_admin)):
    return {"message": "Top-secret admin stats"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=PORT,
        reload=True,
    )