from supabase import Client


class AuthService:
    def __init__(self, supabase: Client):
        self.supabase = supabase

    def login(self, username: str, password: str):
        response = self.supabase.auth.sign_in_with_password(
            {"email": username, "password": password}
        )
        if response.session is None:
            raise ValueError("Authentication failed")
        return response

    def refresh(self, refresh_token: str):
        try:
            response = self.supabase.auth.refresh_session(refresh_token)
        except Exception:
            raise ValueError("Invalid refresh token")

        if response.session is None:
            raise ValueError("Invalid refresh token")
        return response

    def logout(self, access_token: str):
        self.supabase.auth.sign_out()

    def change_password(self, access_token: str, new_password: str):
        self.supabase.auth.set_session(access_token, access_token)
        response = self.supabase.auth.update_user({"password": new_password})
        if response.user is None:
            raise ValueError("Failed to update password")
        return response