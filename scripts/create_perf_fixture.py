"""Creates a minimal Department + Team fixture in the local database,
so tests/performance/locustfile.py can exercise GET /teams/{id} and
GET /teams/{id}/employees (which need a real team_id to hit).

This writes directly via SQLAlchemy rather than through the API,
because Department has no create endpoint (it's expected to be seeded
separately) -- there's nothing to reuse from the app's business logic
here, unlike e.g. onboarding/competency-cycle creation, which involve
enough workflow logic that going through the real API would be safer
if we ever add fixtures for those.

Local/dev/perf databases only -- do NOT point this at production.

Usage:
    python3 scripts/create_perf_fixtures.py

Safe to re-run: skips creation if a "Perf Test Team" already exists.
"""
import asyncio

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.department import Department
from app.models.employee import Employee
from app.models.team import Team


async def main() -> None:
    async with AsyncSessionLocal() as db:
        existing = (
            await db.execute(select(Team).where(Team.name == "Perf Test Team"))
        ).scalar_one_or_none()

        if existing is not None:
            print(f"Already exists: team_id={existing.id}, department_id={existing.department_id}")
            return

        manager = (await db.execute(select(Employee).limit(1))).scalar_one_or_none()
        if manager is None:
            raise RuntimeError(
                "No employees exist yet -- run scripts/provision_test_employee.py first."
            )

        department = Department(name="Perf Test Department")
        db.add(department)
        await db.flush()

        team = Team(
            name="Perf Test Team",
            department_id=department.id,
            team_manager_id=manager.id,
        )
        db.add(team)
        await db.flush()

        manager.team_id = team.id

        await db.commit()

        print(f"Created: team_id={team.id}, department_id={department.id}, team_manager_id={manager.id}")


if __name__ == "__main__":
    asyncio.run(main())