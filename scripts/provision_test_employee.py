"""Provisions a Supabase-authenticated user as an Employee + User row in
the local database, so the app's own `get_current_user` lookup succeeds
instead of returning 'User not provisioned in system' (401).

This mirrors what tests/conftest.py::provisioned_test_employee does for
the pytest suite, but commits for real instead of rolling back — meant
for local/dev/perf databases only. Do NOT point this at production.

Usage:
    # Default: reads TEST_USER_EMAIL/PASSWORD from .env.test, role=EMPLOYEE
    python3 scripts/provision_test_employee.py

    # Explicit email/password/role, e.g. for a second, elevated-role
    # test account (see scripts/create_second_test_user.py):
    python3 scripts/provision_test_employee.py manager-test@gmail.com S0mePassw0rd! HR_MANAGER

Valid roles: EMPLOYEE, MANAGER, HRBP, HR_MANAGER (see
app/models/user.py::EmployeeRoleType). Safe to re-run: skips creation
if the auth account is already provisioned.
"""
import asyncio
import sys
from datetime import date

from pydantic_settings import BaseSettings, SettingsConfigDict
from supabase import create_client
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.employee import Employee
from app.models.employee_role import EmployeeRole
from app.models.user import User, EmployeeRoleType


class TestAuthSettings(BaseSettings):
    supabase_url: str
    supabase_publishable_key: str
    test_user_email: str
    test_user_password: str

    model_config = SettingsConfigDict(
        env_file=".env.test",
        env_file_encoding="utf-8",
        extra="ignore",
    )


async def main() -> None:
    settings = TestAuthSettings()

    if len(sys.argv) == 1:
        email, password, role = settings.test_user_email, settings.test_user_password, "EMPLOYEE"
    elif len(sys.argv) == 4:
        email, password, role = sys.argv[1], sys.argv[2], sys.argv[3]
    else:
        print("Usage: python3 scripts/provision_test_employee.py [<email> <password> <role>]")
        sys.exit(1)

    if role not in EmployeeRoleType.__members__:
        valid = ", ".join(EmployeeRoleType.__members__)
        raise SystemExit(f"Invalid role {role!r}. Valid roles: {valid}")

    supabase = create_client(settings.supabase_url, settings.supabase_publishable_key)

    response = supabase.auth.sign_in_with_password({"email": email, "password": password})
    if response.session is None or response.user is None:
        raise RuntimeError(f"Could not authenticate {email!r} against Supabase")

    auth_provider_id = str(response.user.id)

    async with AsyncSessionLocal() as db:  # type: AsyncSession
        existing = (
            await db.execute(select(User).where(User.auth_provider_id == auth_provider_id))
        ).scalar_one_or_none()

        if existing is not None:
            print(f"Already provisioned: user id={existing.id}, employee_id={existing.employee_id}")
            return

        employee = Employee(
            username=email,
            full_name=f"Test {role.title().replace('_', ' ')}",
            join_date=date.today(),
        )
        db.add(employee)
        await db.flush()

        db.add(EmployeeRole(employee_id=employee.id, role=role))
        await db.flush()

        user = User(auth_provider_id=auth_provider_id, employee_id=employee.id)
        db.add(user)
        await db.commit()

        print(
            f"Provisioned: user id={user.id}, employee_id={employee.id}, "
            f"role={role}, auth_provider_id={auth_provider_id}"
        )


if __name__ == "__main__":
    asyncio.run(main())