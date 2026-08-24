"""Load/performance tests for the Career Journey API.

This measures the app's own request handling (routing, auth
middleware, permission checks, SQLAlchemy queries) under concurrent
load. It talks to a running instance of the app (e.g. `uvicorn
app.main:app`), NOT to the test suite's in-process ASGI transport.

--------------------------------------------------------------------
Why the Supabase login only happens ONCE per account, ever
--------------------------------------------------------------------
`POST /auth/login` in this app proxies to Supabase's password grant.
Supabase enforces its own rate limit on that endpoint (see your
project's Auth settings) -- if every simulated Locust user logs in
independently in on_start, spawning e.g. 100 users fires 100 real
logins in a few seconds and Supabase responds with 429 Too Many
Requests, which has nothing to do with this app's performance.

So instead: the very first simulated user to need a token fetches it
once, real access tokens are cached at module scope, and every other
simulated user (however many you spawn) reuses the same cached token.
A gevent Semaphore guards the fetch so concurrent greenlets can't
both slip past the cache-miss check and both fire a login. This is a
deliberate simplification -- JWTs are stateless, so the app can't
tell the difference between "50 requests from 50 sessions" and "50
requests carrying the same token" for the purposes of load-testing
its own routing/DB/permission-check performance, which is what this
suite is for.

--------------------------------------------------------------------
Required environment variables (same values as tests/.env.test)
--------------------------------------------------------------------
SUPABASE_URL
SUPABASE_PUBLISHABLE_KEY
TEST_USER_EMAIL
TEST_USER_PASSWORD

Optional, for the ElevatedUser class (HR_MANAGER-role coverage):
ELEVATED_TEST_USER_EMAIL
ELEVATED_TEST_USER_PASSWORD

--------------------------------------------------------------------
Role coverage caveat
--------------------------------------------------------------------
AuthenticatedUser logs in as a plain EMPLOYEE (see
tests/conftest.py::provisioned_test_employee /
scripts/provision_test_employee.py) and covers every endpoint
reachable by that role: unrestricted list endpoints (/competencies,
/notifications, /meetings) plus self-scoped employee endpoints (using
the employee_id resolved from /auth/me in on_start). Endpoints gated
to MANAGER/HRBP/HR_MANAGER still get hit (e.g. GET /employees) so the
permission-check code path is measured, but they correctly return 403
for this user -- treated as expected/passing, not a failure.

ElevatedUser covers the HR_MANAGER-gated paths for real, using a
second Supabase account. It's inactive (weight=0, spawns no users)
unless ELEVATED_TEST_USER_EMAIL/PASSWORD are set -- see that class's
docstring for how to provision one. It also resolves the "Perf Test
Team" fixture created by scripts/create_perf_fixtures.py to exercise
GET /teams/{id} and GET /teams/{id}/employees; if that script hasn't
been run yet, those two tasks are skipped gracefully instead of
failing.
"""
import os

import gevent.lock
from locust import HttpUser, task, between
import requests


SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
SUPABASE_PUBLISHABLE_KEY = os.environ["SUPABASE_PUBLISHABLE_KEY"]
TEST_USER_EMAIL = os.environ["TEST_USER_EMAIL"]
TEST_USER_PASSWORD = os.environ["TEST_USER_PASSWORD"]

ELEVATED_TEST_USER_EMAIL = os.environ.get("ELEVATED_TEST_USER_EMAIL")
ELEVATED_TEST_USER_PASSWORD = os.environ.get("ELEVATED_TEST_USER_PASSWORD")


_token_cache: dict[str, str] = {}
_token_cache_lock = gevent.lock.Semaphore()


def _login_to_supabase(email: str, password: str) -> str:
    response = requests.post(
        f"{SUPABASE_URL}/auth/v1/token",
        params={"grant_type": "password"},
        headers={"apikey": SUPABASE_PUBLISHABLE_KEY},
        json={"email": email, "password": password},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def get_cached_token(email: str, password: str) -> str:
    """Returns a cached Supabase access token for this account,
    logging in for real only the first time it's needed. Safe to call
    from many concurrent Locust users -- the semaphore ensures only
    one of them actually hits Supabase's login endpoint.
    """
    if email in _token_cache:
        return _token_cache[email]

    with _token_cache_lock:
        # Another greenlet may have already populated this while we
        # were waiting for the lock.
        if email not in _token_cache:
            _token_cache[email] = _login_to_supabase(email, password)

    return _token_cache[email]


class AuthenticatedUser(HttpUser):
    """Simulates a logged-in employee browsing the app."""

    wait_time = between(1, 3)

    def on_start(self):
        self.token = get_cached_token(TEST_USER_EMAIL, TEST_USER_PASSWORD)
        self.auth_headers = {"Authorization": f"Bearer {self.token}"}

        # Resolve our own employee_id once, so self-scoped endpoints
        # (GET /employees/{id}, .../competencies, .../roles) can be
        # exercised without hardcoding an id that may not exist in
        # every environment.
        me = self.client.get(
            "/auth/me", headers=self.auth_headers, name="/auth/me (on_start)"
        )
        self.employee_id = me.json()["employee_id"]

    @task(5)
    def get_current_user(self):
        self.client.get("/auth/me", headers=self.auth_headers, name="/auth/me")

    @task(5)
    def get_my_onboarding(self):
        with self.client.get(
            "/me/onboarding",
            headers=self.auth_headers,
            name="/me/onboarding",
            catch_response=True,
        ) as response:
            # 404 is a legitimate outcome if the test user has no
            # onboarding record yet.
            if response.status_code in (200, 404):
                response.success()

    @task(3)
    def list_competencies(self):
        self.client.get(
            "/competencies", headers=self.auth_headers, name="/competencies"
        )

    @task(3)
    def list_notifications(self):
        self.client.get(
            "/notifications", headers=self.auth_headers, name="/notifications"
        )

    @task(3)
    def list_meetings(self):
        self.client.get("/meetings", headers=self.auth_headers, name="/meetings")

    @task(3)
    def get_own_employee(self):
        self.client.get(
            f"/employees/{self.employee_id}",
            headers=self.auth_headers,
            name="/employees/{id}",
        )

    @task(2)
    def get_own_employee_competencies(self):
        self.client.get(
            f"/employees/{self.employee_id}/competencies",
            headers=self.auth_headers,
            name="/employees/{id}/competencies",
        )

    @task(2)
    def get_own_employee_roles(self):
        self.client.get(
            f"/employees/{self.employee_id}/roles",
            headers=self.auth_headers,
            name="/employees/{id}/roles",
        )

    @task(2)
    def list_employees(self):
        with self.client.get(
            "/employees",
            headers=self.auth_headers,
            name="/employees",
            catch_response=True,
        ) as response:
            # See the role-coverage caveat in the module docstring.
            if response.status_code in (200, 403):
                response.success()


class AnonymousUser(HttpUser):
    """Unauthenticated traffic: health checks and expected 401s."""

    wait_time = between(1, 3)
    weight = 1  # spawn far fewer of these than AuthenticatedUser

    @task(3)
    def health_check(self):
        self.client.get("/health", name="/health")

    @task(1)
    def me_without_token(self):
        with self.client.get(
            "/auth/me", name="/auth/me (no token)", catch_response=True
        ) as response:
            if response.status_code == 401:
                response.success()


class ElevatedUser(HttpUser):
    """Simulates an HR_MANAGER, unlocking role-gated endpoints that
    AuthenticatedUser gets 403 on (see app/core/scope.py -- HR_MANAGER
    bypasses per-employee/per-team scope checks entirely).

    Requires ELEVATED_TEST_USER_EMAIL/PASSWORD to point at a Supabase
    account provisioned with the HR_MANAGER role, e.g.:

        python3 scripts/create_second_test_user.py mgr-test@gmail.com <password>
        python3 scripts/provision_test_employee.py mgr-test@gmail.com <password> HR_MANAGER

    If those env vars aren't set, this user class disables itself
    (weight=0) instead of failing every run.
    """

    wait_time = between(1, 3)
    weight = 1 if (ELEVATED_TEST_USER_EMAIL and ELEVATED_TEST_USER_PASSWORD) else 0

    def on_start(self):
        self.token = get_cached_token(
            ELEVATED_TEST_USER_EMAIL, ELEVATED_TEST_USER_PASSWORD
        )
        self.auth_headers = {"Authorization": f"Bearer {self.token}"}

        me = self.client.get(
            "/auth/me", headers=self.auth_headers, name="/auth/me (elevated, on_start)"
        )
        self.employee_id = me.json()["employee_id"]

        # Resolve the "Perf Test Team" created by
        # scripts/create_perf_fixtures.py. If it hasn't been run yet,
        # team-scoped tasks below are skipped gracefully.
        self.team_id = None
        teams = self.client.get(
            "/teams", headers=self.auth_headers, name="/teams (on_start)"
        )
        if teams.status_code == 200:
            for team in teams.json():
                if team.get("name") == "Perf Test Team":
                    self.team_id = team["id"]
                    break

    @task(5)
    def list_employees(self):
        # HR_MANAGER: this is the real 200/DB-querying path, unlike
        # AuthenticatedUser's 403-only hit on the same endpoint.
        self.client.get(
            "/employees", headers=self.auth_headers, name="/employees (elevated)"
        )

    @task(3)
    def get_own_employee_onboarding(self):
        with self.client.get(
            f"/employees/{self.employee_id}/onboarding",
            headers=self.auth_headers,
            name="/employees/{id}/onboarding (elevated)",
            catch_response=True,
        ) as response:
            # 404 is expected: this test account has no onboarding
            # record of its own.
            if response.status_code in (200, 404):
                response.success()

    @task(2)
    def list_own_roles(self):
        self.client.get(
            f"/employees/{self.employee_id}/roles",
            headers=self.auth_headers,
            name="/employees/{id}/roles (elevated)",
        )

    @task(2)
    def list_notifications(self):
        self.client.get(
            "/notifications",
            headers=self.auth_headers,
            name="/notifications (elevated)",
        )

    @task(3)
    def list_teams(self):
        self.client.get("/teams", headers=self.auth_headers, name="/teams")

    @task(2)
    def get_perf_test_team(self):
        if self.team_id is None:
            return
        self.client.get(
            f"/teams/{self.team_id}",
            headers=self.auth_headers,
            name="/teams/{id}",
        )

    @task(2)
    def get_perf_test_team_employees(self):
        if self.team_id is None:
            return
        self.client.get(
            f"/teams/{self.team_id}/employees",
            headers=self.auth_headers,
            name="/teams/{id}/employees",
        )