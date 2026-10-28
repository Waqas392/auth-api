
# Auth - Login & Protect

A REST API built with FastAPI and Supabase Auth. It supports user signup, login, logout, token refresh, JWT verification, protected routes, and admin-only access.

## Features

- User signup and login through Supabase Auth
- Bearer-token authentication for protected routes
- User profile and dashboard endpoints
- Logout using the authenticated user's token
- Refresh-token endpoint
- Admin-only route with role-based authorization
- Interactive API documentation through Swagger UI
- Automated tests using a mocked Supabase client

## Requirements

- Python 3.11 or newer
- A Supabase project with email authentication enabled
- Git

## Setup

### 1. Clone the repository

```powershell
git clone https://github.com/Waqas392/auth-api.git
cd auth-api
```

### 2. Create a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, you can use the virtual environment's Python executable directly.

### 3. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

If you did not activate the environment, use:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 4. Configure environment variables

Create your local environment file:

```powershell
Copy-Item .env.example .env
notepad .env
```

Set your own Supabase project URL and publishable key:

```dotenv
SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
SUPABASE_KEY=YOUR_SUPABASE_PUBLISHABLE_KEY
PORT=8000
```

Never use a Supabase `service_role` key or secret key as the application key. Keep `.env` private; it is excluded by `.gitignore` and must not be committed.

### 5. Configure Supabase Auth

In your Supabase dashboard, enable email authentication and signup. If email confirmation is enabled, confirm the signup email before logging in.

Use a dedicated practice project rather than changing settings in a project used by another application.

## Run the API

```powershell
python main.py
```

Open Swagger UI:

http://127.0.0.1:8000/docs

## API Reference

| Method | Endpoint | Authentication | Expected success |
|---|---|---|---|
| POST | `/auth/signup` | None | 201 Created |
| POST | `/auth/login` | None | 200 OK |
| POST | `/auth/logout` | Bearer token | 204 No Content |
| POST | `/auth/refresh` | Refresh token in request body | 200 OK |
| GET | `/public/info` | None | 200 OK |
| GET | `/protected/profile` | Bearer token | 200 OK |
| GET | `/protected/dashboard` | Bearer token | 200 OK |
| GET | `/admin/stats` | Bearer token and admin role | 200 OK |

### Common error responses

- `400 Bad Request`: Invalid input or a rejected signup request.
- `401 Unauthorized`: Missing or invalid authentication credentials.
- `403 Forbidden`: An authenticated user lacks the required permission.
- `502 Bad Gateway`: An upstream service error that the API handles as a gateway failure.

The exact response depends on the endpoint and the error encountered.

## Test with Swagger

1. Open `/docs`.
2. Use `POST /auth/signup` to create a test user.
3. Confirm the user's email if required by your Supabase settings.
4. Use `POST /auth/login` to obtain an access token and refresh token.
5. Click **Authorize** and enter the access token if Swagger requests it without the `Bearer ` prefix.
6. Call `GET /protected/profile`. A valid token should return `200 OK`.
7. Remove authorization and call the same endpoint again. It should return `401 Unauthorized`.
8. Call `POST /auth/refresh` with the refresh token in its JSON request body.
9. Call `GET /admin/stats` with a regular user's token. It should return `403 Forbidden`.

Never share access tokens, refresh tokens, passwords, or `.env` contents.

## Automated Tests

Run the test suite:

```powershell
python -m pytest -v
```

The automated tests use a mocked Supabase client, so they test the API's behavior without making real authentication requests. Test live integration behavior separately against your Supabase project.

## Authentication: 401 vs. 403

- **401 Unauthorized:** The request has missing, invalid, or expired authentication credentials.
- **403 Forbidden:** The user is authenticated but does not have permission to access the resource.

The admin endpoint relies on the role-checking logic implemented in the application.

## Token and Logout Notes

Access tokens expire. Refresh tokens can obtain replacement tokens while the Supabase session remains valid.

The logout endpoint requests sign-out through Supabase. Clients should discard their local tokens after logout. An already-issued access token may remain usable until expiration, depending on how token verification and revocation are implemented.

## Security

- Never commit `.env`.
- Never expose Supabase secret or `service_role` keys.
- Never commit real passwords, access tokens, or refresh tokens.
- Use HTTPS in production.
- Review authentication and authorization rules before deployment.
