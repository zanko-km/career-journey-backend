import jwt
from fastapi import HTTPException, status
from fastapi.security import HTTPBearer
from jwt import PyJWKClient

from app.core.config import settings


bearer_scheme = HTTPBearer()

jwks_client = PyJWKClient(
    f"{settings.auth_issuer}/.well-known/jwks.json"
)


def decode_token(token: str) -> dict:
    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256"],
            audience=settings.auth_audience,
            issuer=settings.auth_issuer,
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )

    return payload