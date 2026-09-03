import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ParseSettings:
    app_access_token: str | None
    openai_api_key: str | None
    model_name: str


def _optional_environment(name: str) -> str | None:
    value = os.getenv(name)

    if value is None:
        return None

    normalized = value.strip()
    return normalized or None


def get_parse_settings() -> ParseSettings:
    return ParseSettings(
        app_access_token=_optional_environment("APP_ACCESS_TOKEN"),
        openai_api_key=_optional_environment("OPENAI_API_KEY"),
        model_name=_optional_environment("MODEL_NAME") or "gpt-5.6-luna",
    )
