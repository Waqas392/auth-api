# Auth · Login & protect (FastAPI + Supabase Auth)

A secure API: sign up, log in, log out, and routes that only answer to users holding a valid Supabase JWT. Passwords and tokens are handled by Supabase; this server only forwards credentials and verifies tokens.

## Setup
```bash
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env        # then fill in SUPABASE_URL and SUPABASE_KEY (anon key!)
```
In the Supabase Dashboard: Authentication → Sign In / Providers → Email → turn **Confirm email** off (practice only).

## Run
```bash
python main.py        # http://127.0.0.1:8000, Swagger at /docs
```

## API reference
| Method | Route | Auth? | Success | Errors |
|---|---|---|---|---|
| POST | /auth/signup | no | 201 + user | 400 |
| POST | /auth/login | no | 200 + access/refresh token | 400, 401 |
| POST | /auth/logout | Bearer | 204 | 401, 502 |
| POST | /auth/refresh | no (refresh token in body) | 200 + new tokens | 400, 401 |
| GET | /public/info | no | 200 | – |
| GET | /protected/profile | Bearer | 200 + user | 401 |
| GET | /protected/dashboard | Bearer | 200 | 401 |
| GET | /admin/stats | Bearer + admin role | 200 | 401, 403 |

All errors are JSON: `{"error": "..."}`.

## Try it
```bash
curl -i -X POST localhost:8000/auth/signup -H "Content-Type: application/json" -d '{"email":"test@example.com","password":"password123"}'
curl -i -X POST localhost:8000/auth/login  -H "Content-Type: application/json" -d '{"email":"test@example.com","password":"password123"}'
curl -i localhost:8000/protected/profile -H "Authorization: Bearer <ACCESS_TOKEN>"      # 200
curl -i localhost:8000/protected/profile -H "Authorization: Bearer <TAMPERED_TOKEN>"    # 401
```

## Swagger
![Swagger UI](docs/swagger.png)  <!-- add your screenshot -->

## 401 vs 403
401 = "I don't know who you are" (missing, malformed, invalid or expired token). 403 = "I know who you are, and you may not" (`/admin/stats` requires `app_metadata.role == "admin"`).

## Why access tokens are short-lived
A stolen access token is only useful until it expires (1 hour by default); the refresh token lets the client get a new one without re-entering a password.

## Notes
- Logout calls Supabase with the user's own token and global scope, which revokes their refresh sessions. An access token already issued can still work until it expires, so clients should discard it.
- Run the offline tests with `python -m pytest -v`. They use a fake Supabase client, so a real signup, login and logout still need a manual check.
- Never commit `.env`; only `.env.example` is tracked.
