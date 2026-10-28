# Auth — Login & Protect

A REST API built with FastAPI and Supabase Auth. It supports user signup, login, logout, token refresh, JWT verification, protected routes, and role-based admin access.

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
- A Supabase project
- Git (optional, for version control)

## Setup

### 1. Clone the repository

```powershell
git clone https://github.com/Waqas392/auth-api.git
cd auth-api
```

### 2. Create and activate a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, use the virtual environment's Python executable directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 3. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### 4. Configure environment variables

Create your local environment file:

```powershell
Copy-Item .env.example .env
notepad .env
```

Set the following values using your own Supabase project credentials:

```dotenv
SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
SUPABASE_KEY=YOUR_SUPABASE_PUBLISHABLE_KEY
PORT=8000
```

Use your Supabase Project URL and publishable key (or legacy `anon` key if supported by your setup). Never use a `service_role` or secret key as the application key.

Keep `.env` private. It is excluded by `.gitignore` and must not be committed.

### 5. Configure Supabase Auth

In your Supabase dashboard, open Authentication settings and ensure that email authentication and signup are enabled.

Email confirmation may remain enabled. If it is enabled, confirm the signup email before attempting password login.

For a practice project, use a dedicated Supabase project rather than changing authentication settings in a project used by another application.

## Run the API

Start the development server:

```powershell
python main.py
```

Open Swagger UI:

http://127.0.0.1:8000/docs

## API reference

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

Error responses depend on the endpoint and the error returned by Supabase.

- `400 Bad Request`: Invalid input or a rejected authentication request.
- `401 Unauthorized`: Missing, invalid, expired, or otherwise rejected authentication credentials.
- `403 Forbidden`: The authenticated user lacks the required permission.
- `502 Bad Gateway`: An upstream authentication service error, if handled that way by the endpoint.

## Testing with Swagger

1. Open `/docs`.
2. Use `POST /auth/signup` to create a test user.
3. Use `POST /auth/login` to obtain an access token and refresh token.
4. Click **Authorize** and enter the access token.
5. Execute `GET /protected/profile` and verify that it returns `200 OK`.
6. Remove Swagger authorization and repeat the request. The protected endpoint should return `401 Unauthorized`.
7. Call `POST /auth/refresh` with the refresh token in its JSON request body.
8. Test `GET /admin/stats` with a normal user's token. It should return `403 Forbidden` when the route's admin-role check is working.

Never share access tokens, refresh tokens, passwords, or `.env` contents publicly.

## Automated tests

Run the test suite:

```powershell
python -m pytest -v
```

The automated tests use a mocked Supabase client. They verify application behavior without making real authentication requests. Live integration behavior should also be checked against your Supabase project.

## Authentication: 401 vs. 403

- **401 Unauthorized:** The request does not have acceptable authentication credentials.
- **403 Forbidden:** The user is authenticated but does not have permission to access the requested resource.

The admin endpoint requires the role configured by the application's authorization logic.

## Token and logout notes

Access tokens expire, and refresh tokens can be used to obtain replacement tokens while the Supabase session remains valid.

The logout endpoint requests session sign-out through Supabase. Clients should discard their local tokens after logout. An already-issued access token may remain usable until expiration depending on how token verification and revocation are implemented.

## Security

- Never commit `.env`.
- Never expose Supabase secret or `service_role` keys.
- Do not commit real passwords, access tokens, or refresh tokens.
- Use HTTPS in production.
- Review authorization rules before deploying the API.
