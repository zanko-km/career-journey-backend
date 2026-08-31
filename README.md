# Career Journey Backend

Backend API for Career Journey — an onboarding, meetings, competency-review,
and performance-management system for four roles: **EMPLOYEE**, **MANAGER**,
**HRBP**, and **HR_MANAGER**.

## Tech stack

| Layer | Choice |
|---|---|
| Language / runtime | Python 3.12 |
| Web framework | FastAPI |
| ORM | SQLAlchemy 2.x (async) |
| Database | PostgreSQL (via `asyncpg`) |
| Migrations | Alembic |
| Auth | Supabase Auth (JWT, ES256, verified against Supabase's JWKS endpoint) |
| Tests | pytest, pytest-asyncio, httpx |

## Project structure

```
app/
  api/routes/          FastAPI routers, grouped by resource
    employees/           CRUD, roles, onboarding, competencies, decisions
    competency_cycles/    self/manager assessment, radar data, IDP
    meetings/             create/respond/confirm-held, queries
  core/                config, auth/JWT verification, permission & scope
                        helpers, exception handling
  models/              SQLAlchemy models
  schemas/             Pydantic request/response schemas
  services/            business logic that doesn't belong in a route
                        (OnboardingService, notifications, auth)
alembic/               migration environment + versions
tests/                 pytest suite, organized by domain
scripts/               one-off/manual scripts (test user provisioning, perf
                        fixtures, local token helper)
docs/
  DEPLOYMENT.md          how to run this in production
  AUTHORIZATION.md       what each role (EMPLOYEE/MANAGER/HRBP/HR_MANAGER)
                         can do, and which endpoint enforces it
```

## Running locally

### 1. Prerequisites
- Python 3.12
- A PostgreSQL database (local via Docker, or a hosted one)
- A Supabase project (used for authentication — login/refresh/logout and
  JWT verification all go through Supabase)

### 2. Configure environment

Copy `.env.example` to `.env` and fill in the values:

```
APP_ENV=development
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/career_journey
AUTH_ISSUER=https://<your-project>.supabase.co/auth/v1
AUTH_AUDIENCE=authenticated
SUPABASE_URL=https://<your-project>.supabase.co
SUPABASE_PUBLISHABLE_KEY=<your publishable/anon key>
SUPABASE_SERVICE_ROLE_KEY=<your service role key>
```

See `docs/DEPLOYMENT.md` for what each variable is used for.

### 3. Install and run

```bash
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload
```

The API is now at `http://localhost:8000`, interactive docs at
`http://localhost:8000/docs`.

### 4. Or, with Docker Compose

```bash
docker compose up --build
```

This starts the API container and a local Postgres 16 container. You still
need to run `alembic upgrade head` against that database before the API can
serve real requests (see `docs/DEPLOYMENT.md` — migrations are not baked
into the image).

## Running tests

```bash
pip install -e ".[dev]"
pytest -q
```

Tests use their own database session fixtures (see `tests/conftest.py`) and
don't require Supabase — auth is bypassed in tests via
`app.dependency_overrides[get_current_user]`.

## Further reading

- [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) — production deployment,
  required environment variables, migrations, and operational notes
  (including a background job the API depends on).
- [`docs/AUTHORIZATION.md`](docs/AUTHORIZATION.md) — the full role/permission
  matrix: what EMPLOYEE, MANAGER, HRBP, and HR_MANAGER can each do, and
  which endpoint/scope check enforces it.
