"""Creates a second Supabase auth user, for use as an elevated-role
(HR_MANAGER) test account in performance tests.

Only needed once. If Supabase's project settings require email
confirmation, you'll need to confirm the account (via the Supabase
dashboard's Auth > Users list, or by disabling email confirmation for
your test project) before sign_in_with_password will work for it.

Usage:
    python3 scripts/create_second_test_user.py <email> <password>

Example:
    python3 scripts/create_second_test_user.py manager-test@gmail.com S0mePassw0rd!
"""
import sys

from pydantic_settings import BaseSettings, SettingsConfigDict
from supabase import create_client


class TestAuthSettings(BaseSettings):
    supabase_url: str
    supabase_publishable_key: str

    model_config = SettingsConfigDict(
        env_file=".env.test",
        env_file_encoding="utf-8",
        extra="ignore",
    )


def main() -> None:
    if len(sys.argv) != 3:
        print("Usage: python3 scripts/create_second_test_user.py <email> <password>")
        sys.exit(1)

    email, password = sys.argv[1], sys.argv[2]

    settings = TestAuthSettings()
    supabase = create_client(settings.supabase_url, settings.supabase_publishable_key)

    response = supabase.auth.sign_up({"email": email, "password": password})

    if response.user is None:
        raise RuntimeError("Sign-up failed -- check the error above, if any.")

    print(f"Created Supabase user: id={response.user.id}, email={response.user.email}")
    if response.session is None:
        print(
            "No session was returned -- this project likely requires email "
            "confirmation. Confirm the account in the Supabase dashboard "
            "(Authentication > Users) before using it."
        )


if __name__ == "__main__":
    main()