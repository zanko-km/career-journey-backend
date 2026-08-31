# Deployment Guide

## 1. Required environment variables

The app reads these via `app/core/config.py` (`pydantic-settings`, backed by
a `.env` file or real environment variables — either works). All variables
below marked **required** will cause the app to fail at startup if missing.

| Variable | Required | Description |
|---|---|---|
| `APP_ENV` | ✅ | Free-text environment label (e.g. `development`, `staging`, `production`). Not currently branched on in code, but keep it accurate for logging/ops clarity. |
| `DATABASE_URL` | ✅ | Async SQLAlchemy connection string, e.g. `postgresql+asyncpg://user:pass@host:5432/dbname`. Must use the `asyncpg` driver (`postgresql+asyncpg://`), not plain `postgresql://`. |
| `AUTH_ISSUER` | ✅ | Your Supabase project's auth URL, e.g. `https://<project-ref>.supabase.co/auth/v1`. Used both to verify JWTs (`iss` claim) and to fetch the JWKS from `{AUTH_ISSUER}/.well-known/jwks.json`. |
| `AUTH_AUDIENCE` | ✅ | JWT audience claim to verify. Supabase issues `authenticated` by default — leave as `authenticated` unless you've customized this in Supabase. |
| `SUPABASE_URL` | ✅ | Your Supabase project URL, e.g. `https://<project-ref>.supabase.co`. Used by the Supabase SDK client for login/refresh/logout/change-password. |
| `SUPABASE_PUBLISHABLE_KEY` | ✅ | Supabase's publishable/anon key. Used for the client-facing Supabase SDK calls (login, refresh, logout). |
| `SUPABASE_SERVICE_ROLE_KEY` | optional | Supabase service-role key, only needed if/when server-side admin operations against Supabase are added. Safe to leave unset for current functionality. |
| `DB_POOL_SIZE` | optional (default `20`) | SQLAlchemy async engine pool size. |
| `DB_MAX_OVERFLOW` | optional (default `20`) | Extra connections allowed beyond pool size under load. |
| `DB_POOL_TIMEOUT` | optional (default `30`) | Seconds to wait for a pooled connection before erroring. |
| `DB_POOL_RECYCLE` | optional (default `1800`) | Seconds before a pooled connection is recycled (avoids stale-connection errors with managed Postgres). |

Copy `.env.example` as a starting point — note it doesn't list the four
`DB_*` pool settings since they all have safe defaults.

**Auth model:** this API does not implement its own password hashing or
session storage — it delegates entirely to Supabase Auth. `POST /auth/login`,
`/auth/refresh`, `/auth/logout`, and `/auth/change-password` all call the
Supabase SDK; every other endpoint verifies the bearer JWT locally against
Supabase's public JWKS (ES256), so those requests never round-trip to
Supabase. This means Supabase must be reachable from wherever this API
verifies tokens (i.e. from every request), so plan network/egress access to
`{AUTH_ISSUER}/.well-known/jwks.json` accordingly.

## 2. Database migrations

This project uses Alembic. **Migrations are not run automatically** on
container start — run them explicitly as a separate step before (or right
after) deploying a new version:

```bash
# locally / in CI, against the target DATABASE_URL
alembic upgrade head

# or, once the image is running via docker compose:
docker compose exec api alembic upgrade head
```

Run migrations **before** rolling out application instances that depend on
schema changes introduced in that release, to avoid a window where new code
queries columns/tables that don't exist yet.

## 3. Running with Docker

```bash
docker compose up --build
```

`docker-compose.yml` provisions:
- `api` — the FastAPI app, built from the local `Dockerfile`, on port 8000
- `db` — Postgres 16 for local/staging use, on port 5432

> The image now includes `alembic/` and `alembic.ini` (fixed — previously
> only `app/` was copied into the image, which meant migrations couldn't be
> run from inside the container at all). Run migrations with
> `docker compose exec api alembic upgrade head` after the containers are up.

For a real production deployment, replace the `db` service with your managed
Postgres instance (set `DATABASE_URL` accordingly) rather than relying on
the bundled `db` service, which has no volume configured and has no data
persistence across recreates.

## 4. Background job you must schedule

`POST /employees/{employee_id}/onboarding/check-month2-tasks-deadline` is
**not triggered automatically by anything in this codebase.** Per the
business requirement, month-2 onboarding tasks must be set by the employee's
manager by end of day; if they aren't, the HRBP must be notified. That
notification only happens when this endpoint is called.

You need an external scheduler (cron, a scheduled CI/CD job, a serverless
scheduled function, Celery beat, etc.) to call this endpoint once per
business day, for every employee currently in month 2 of onboarding, near
end-of-day in your organization's timezone. Nothing in the application will
do this on its own.

## 5. CORS

No CORS middleware is currently configured in `app/main.py`. If the frontend
is served from a different origin than the API, requests will be blocked by
the browser until `fastapi.middleware.cors.CORSMiddleware` (or an equivalent
reverse-proxy rule) is added and configured with the frontend's origin(s).

## 6. Health check

`GET /health` returns `{"status": "ok"}` with no auth required and no
database access — suitable for a load balancer / orchestrator liveness
probe. It does **not** check database connectivity, so it will report
healthy even if the database is unreachable; if you need a DB-aware
readiness probe, add a separate endpoint or extend this one.

## 7. Post-deploy smoke checklist

- [ ] `GET /health` returns 200
- [ ] `GET /docs` loads (interactive OpenAPI docs)
- [ ] `alembic upgrade head` has been run against the target database
- [ ] `alembic current` matches the latest revision in `alembic/versions/`
- [ ] A real login via `POST /auth/login` succeeds against the configured
      Supabase project
- [ ] The month-2 deadline-check scheduler (section 4) is configured and
      firing
