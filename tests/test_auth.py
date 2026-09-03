import pytest
from fastapi import HTTPException

from app.auth import require_parse_token
from app.errors import ConfigurationError
from app.settings import ParseSettings, get_parse_settings


def test_get_parse_settings_reads_environment(monkeypatch):
    monkeypatch.setenv("APP_ACCESS_TOKEN", "app-secret")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-secret")
    monkeypatch.delenv("MODEL_NAME", raising=False)

    settings = get_parse_settings()

    assert settings == ParseSettings(
        app_access_token="app-secret",
        openai_api_key="openai-secret",
        model_name="gpt-5.6-luna",
    )


def test_require_parse_token_accepts_exact_match():
    settings = ParseSettings(
        app_access_token="correct",
        openai_api_key="key",
        model_name="gpt-5.6-luna",
    )

    assert require_parse_token("correct", settings) is None


@pytest.mark.parametrize("supplied", [None, "wrong"])
def test_require_parse_token_rejects_missing_or_wrong(supplied):
    settings = ParseSettings(
        app_access_token="correct",
        openai_api_key="key",
        model_name="gpt-5.6-luna",
    )

    with pytest.raises(HTTPException) as error:
        require_parse_token(supplied, settings)

    assert error.value.status_code == 401
    assert error.value.detail == "Invalid parse access token."


def test_require_parse_token_reports_server_misconfiguration():
    settings = ParseSettings(
        app_access_token=None,
        openai_api_key="key",
        model_name="gpt-5.6-luna",
    )

    with pytest.raises(ConfigurationError):
        require_parse_token("anything", settings)
