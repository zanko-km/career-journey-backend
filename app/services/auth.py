from supabase import Client


class AuthService:
    def __init__(self, supabase: Client):
        self.supabase = supabase

    def login(self, username: str, password: str):
        response = self.supabase.auth.sign_in_with_password(
            {
                "email": username,
                "password": password,
            }
        )

        if response.session is None:
            raise ValueError("Authentication failed")

        return response