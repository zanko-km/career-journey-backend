from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.exceptions import APIException


async def api_exception_handler(
    request: Request,
    exc: APIException,
) -> JSONResponse:
    status_code = 401 if exc.code == "UNAUTHORIZED" else 400

    return JSONResponse(
        status_code=status_code,
        content={
            "code": exc.code,
            "message": exc.message,
            "details": exc.details,
        },
    )