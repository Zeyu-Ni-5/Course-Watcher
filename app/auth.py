import secrets

from fastapi import HTTPException, status
from fastapi.security import APIKeyHeader

from app.errors import ConfigurationError
from app.settings import ParseSettings


parse_token_header = APIKeyHeader(
    name="X-Token",
    auto_error=False,
)


def require_parse_token(
    supplied_token: str | None,
    settings: ParseSettings,
) -> None:
    expected_token = settings.app_access_token

    if expected_token is None:
        raise ConfigurationError("Parse access is not configured.")

    if supplied_token is None or not secrets.compare_digest(
        supplied_token,
        expected_token,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid parse access token.",
        )
