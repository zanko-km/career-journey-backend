from typing import Any


class APIException(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ):
        self.code = code
        self.message = message
        self.details = details or {}