from supabase import Client, create_client

from app.core.config import settings


def get_supabase() -> Client:
    return create_client(
        settings.supabase_url,
        settings.supabase_publishable_key,
    )


def get_supabase_admin() -> Client:
    """Client authenticated with the service-role key.

    Required for admin-only operations such as provisioning a new
    Supabase auth user (`auth.admin.create_user`). Do not use this
    client for anything that should respect a caller's own session.
    """
    if not settings.supabase_service_role_key:
        raise RuntimeError(
            "SUPABASE_SERVICE_ROLE_KEY is not configured; "
            "admin user-provisioning operations are unavailable."
        )

    return create_client(
        settings.supabase_url,
        settings.supabase_service_role_key,
    )