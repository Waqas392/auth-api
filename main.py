import logging
import os
from typing import Optional

import httpx
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from supabase import Client, create_client
from supabase_auth.errors import AuthApiError

load_dotenv()
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("auth-api")

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
PORT = int(os.getenv("PORT", "8000"))

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Set SUPABASE_URL and SUPABASE_KEY in your .env file")

app = FastAPI(title="Auth - Login & protect", version="1.0.0")
bearer_scheme = HTTPBearer(auto_error=False)


def get_client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)


@app.exception_handler(HTTPException)
async def http_error(_: Request, exc: HTTPException):
    return JSONResponse({"error": exc.detail}, status_code=exc.status_code)


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError):
    return JSONResponse({"error": "Invalid request body"}, status_code=400)


class Credentials(BaseModel):
    email: Optional[str] = None
    password: Optional[str] = None


class RefreshBody(BaseModel):
    refresh_token: Optional[str] = None


def clean(value: Optional[str]) -> str:
    return (value or "").strip()


def get_current_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
):
    if creds is None or not creds.credentials:
        raise HTTPException(401, "Access token required")
    token = creds.credentials
    try:
        res = get_client().auth.get_user(token)
        user = res.user if res else None
    except AuthApiError:
        user = None
    except Exception:
        log.exception("Token verification could not reach Supabase")
        raise HTTPException(502, "Authentication service unavailable")
    if user is None:
        raise HTTPException(401, "Invalid or expired token")
    return {"user": user, "token": token}


def require_admin(ctx=Depends(get_current_user)):
    role = (ctx["user"].app_metadata or {}).get("role")
    if role != "admin":
        raise HTTPException(403, "Admin access required")
    return ctx


def public_user(user) -> dict:
    return {"id": user.id, "email": user.email, "created_at": str(user.created_at)}


def token_payload(session) -> dict:
    return {
        "access_token": session.access_token,
        "refresh_token": session.refresh_token,
        "token_type": "bearer",
        "expires_in": session.expires_in,
    }


@app.post("/auth/signup", status_code=201, tags=["auth"])
def signup(body: Credentials):
    email, password = clean(body.email), clean(body.password)
    if not email or not password:
        raise HTTPException(400, "Email and password are required")
    try:
        res = get_client().auth.sign_up({"email": email, "password": password})
    except AuthApiError as e:
        raise HTTPException(400, e.message)
    except Exception:
        log.exception("Signup failed")
        raise HTTPException(502, "Authentication service unavailable")
    if res.user is None:
        raise HTTPException(400, "Signup failed")
    return {"user": public_user(res.user)}


@app.post("/auth/login", tags=["auth"])
def login(body: Credentials):
    email, password = clean(body.email), clean(body.password)
    if not email or not password:
        raise HTTPException(400, "Email and password are required")
    try:
        res = get_client().auth.sign_in_with_password(
            {"email": email, "password": password}
        )
    except AuthApiError:
        raise HTTPException(401, "Invalid login credentials")
    except Exception:
        log.exception("Login failed")
        raise HTTPException(502, "Authentication service unavailable")
    if res.session is None:
        raise HTTPException(401, "Invalid login credentials")
    return token_payload(res.session)


@app.post("/auth/logout", status_code=204, tags=["auth"])
def logout(ctx=Depends(get_current_user)):
    try:
        r = httpx.post(
            f"{SUPABASE_URL}/auth/v1/logout",
            params={"scope": "global"},
            headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {ctx['token']}"},
            timeout=10,
        )
    except httpx.HTTPError:
        log.exception("Logout request failed")
        raise HTTPException(502, "Authentication service unavailable")
    if r.status_code not in (200, 204):
        log.error("Logout rejected by Supabase: %s", r.status_code)
        raise HTTPException(502, "Logout failed")
    return Response(status_code=204)


@app.post("/auth/refresh", tags=["auth"])
def refresh(body: RefreshBody):
    refresh_token = clean(body.refresh_token)
    if not refresh_token:
        raise HTTPException(400, "refresh_token is required")
    try:
        res = get_client().auth.refresh_session(refresh_token)
    except AuthApiError:
        raise HTTPException(401, "Invalid or expired refresh token")
    except Exception:
        log.exception("Refresh failed")
        raise HTTPException(502, "Authentication service unavailable")
    if res.session is None:
        raise HTTPException(401, "Invalid or expired refresh token")
    return token_payload(res.session)


@app.get("/public/info", tags=["public"])
def public_info():
    return {"message": "Welcome stranger! This info is public."}


@app.get("/protected/profile", tags=["protected"])
def profile(ctx=Depends(get_current_user)):
    return public_user(ctx["user"])


@app.get("/protected/dashboard", tags=["protected"])
def dashboard(ctx=Depends(get_current_user)):
    return {"message": f"Welcome back, {ctx['user'].email}!"}


@app.get("/admin/stats", tags=["admin"])
def admin_stats(ctx=Depends(require_admin)):
    return {"message": "Admin stats"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=PORT, reload=True)
