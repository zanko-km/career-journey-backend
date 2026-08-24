# Performance tests (Locust)

Load-tests the running API (not the in-process test client), measuring
throughput and latency under concurrent traffic.

## 1. Install

```bash
pip install -e ".[perf]" --break-system-packages   # or: pip install locust requests
```

## 2. Run the app against a real (test) database

Locust needs an actual running server, not the pytest ASGI client. In one
terminal:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Make sure `.env` points at a database you're OK generating load-test data in
(ideally a dedicated perf/staging DB, not production).

## 3. Set Supabase test-user credentials

Same values as `tests/.env.test`:

```bash
export SUPABASE_URL=https://your-project.supabase.co
export SUPABASE_PUBLISHABLE_KEY=your-publishable-key
export TEST_USER_EMAIL=test@example.com
export TEST_USER_PASSWORD=your-test-password
```

## 4. Run Locust

**Interactive (web UI, recommended for exploring)**

```bash
locust -f tests/performance/locustfile.py --host=http://localhost:8000
```

Then open http://localhost:8089, set number of users and spawn rate, and
click Start.

**Headless (for CI / scripted runs)**

```bash
locust -f tests/performance/locustfile.py \
  --host=http://localhost:8000 \
  --users 50 \
  --spawn-rate 5 \
  --run-time 2m \
  --headless \
  --html tests/performance/report.html \
  --csv tests/performance/results
```

- `--users 50 --spawn-rate 5`: ramp up to 50 concurrent simulated users, 5
  new users/sec.
- `--run-time 2m`: stop after 2 minutes.
- `--html`: a self-contained HTML report with response-time charts.
- `--csv`: raw stats (`results_stats.csv`, `results_stats_history.csv`,
  `results_failures.csv`) for diffing between runs or plotting yourself.

## Database connection pool

By default, SQLAlchemy's async engine allows only 5 pooled + 10
overflow = 15 concurrent DB connections -- easy to exhaust once
Locust has 50-100 concurrent users in flight (every authenticated
request does at least one DB round trip in `get_current_user` alone).
When the pool is exhausted, requests queue for a free connection,
which shows up as a big gap between median and p95/p99 latency in the
Locust report.

`app/core/database.py` now reads `db_pool_size` / `db_max_overflow`
from settings (defaults: 20 / 20 = 40 total). Override via `.env` if
needed:

```dotenv
db_pool_size=20
db_max_overflow=20
```

Check your Postgres instance's connection ceiling before raising
these further:

```sql
SHOW max_connections;
```

And if you run `uvicorn` with `--workers N`, each worker process gets
its **own** engine and therefore its own pool -- total possible
connections is `N * (db_pool_size + db_max_overflow)`, not just one
pool shared across workers.

## What it covers

- `GET /health` (unauthenticated baseline)
- `GET /auth/me` (both with and without a token — measures the auth
  middleware itself)
- `GET /me/onboarding` (a real DB query with `selectinload`)
- `GET /employees` (role-gated; see the caveat in `locustfile.py`'s
  docstring about which roles the default test user needs to hit the
  200-OK/DB-querying path instead of 403)

Extend `locustfile.py` with more `@task`s as you add scenarios — e.g.
`POST /meetings` or `GET /employees/{id}/onboarding` once you have known
fixture IDs to target.

## Reading the results

Watch for, in order of importance:
1. **Failure rate** — should be ~0% (excluding intentionally-tolerated
   403/404s noted in the docstring).
2. **p95 / p99 response time** — a few slow outliers matter more than the
   average; that's usually where an N+1 query or missing index shows up.
3. **RPS at your target concurrency** — compare against your expected
   production traffic to see if there's headroom.

Keep a copy of the CSV/HTML from a "known good" run so you have a baseline
to compare against after future changes.