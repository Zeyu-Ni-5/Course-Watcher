import pytest
from sqlalchemy import func, select

from app.database import get_db
from app.errors import (
    ConfigurationError,
    ModelOutputError,
    ModelServiceError,
)
from app.main import app
from app.models import Snapshot, Watch
from app.routers.parse import get_course_request_parser
from app.services import watch_service


class FakeParser:
    def parse(self, text, *, feedback=None):
        if "and" in text.lower():
            return {
                "subject": None,
                "catalog": None,
                "component": None,
                "term_season": None,
                "term_year": None,
            }

        return {
            "subject": "CS",
            "catalog": "136",
            "component": "LEC" if "lecture" in text.lower() else None,
            "term_season": "FALL" if "fall" in text.lower() else None,
            "term_year": 2026 if "fall" in text.lower() else None,
        }


def test_health_is_independent(client, monkeypatch):
    monkeypatch.delenv("APP_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_parse_requires_token(client, monkeypatch):
    monkeypatch.setenv("APP_ACCESS_TOKEN", "correct")

    response = client.post(
        "/parse",
        json={"text": "Watch CS 136"},
    )

    assert response.status_code == 401


def test_parse_returns_preview_without_database_writes(
    client,
    db_session,
    monkeypatch,
):
    monkeypatch.setenv("APP_ACCESS_TOKEN", "correct")
    app.dependency_overrides[
        get_course_request_parser
    ] = lambda: FakeParser()

    try:
        response = client.post(
            "/parse",
            headers={"X-Token": "correct"},
            json={
                "text": "Watch CS 136 lectures in Fall 2026"
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "subject": "CS",
        "catalog": "136",
        "component": "LEC",
        "term_code": "1269",
    }
    assert db_session.scalar(
        select(func.count()).select_from(Watch)
    ) == 0
    assert db_session.scalar(
        select(func.count()).select_from(Snapshot)
    ) == 0


def test_parse_success_does_not_use_database_or_uw_client(
    client,
    monkeypatch,
):
    monkeypatch.setenv("APP_ACCESS_TOKEN", "correct")

    def fail_dependency_if_invoked():
        raise AssertionError("database dependency was invoked")

    def fail_uw_if_invoked(*_args, **_kwargs):
        raise AssertionError("unrelated dependency was invoked")

    app.dependency_overrides[get_db] = fail_dependency_if_invoked
    app.dependency_overrides[
        get_course_request_parser
    ] = lambda: FakeParser()
    monkeypatch.setattr(
        watch_service.uw_client,
        "get_current_term",
        fail_uw_if_invoked,
    )
    monkeypatch.setattr(
        watch_service.uw_client,
        "get_course_sections",
        fail_uw_if_invoked,
    )

    try:
        response = client.post(
            "/parse",
            headers={"X-Token": "correct"},
            json={"text": "Watch CS 136"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "subject": "CS",
        "catalog": "136",
        "component": None,
        "term_code": None,
    }


def test_parse_rejects_multiple_courses(
    client,
    monkeypatch,
):
    monkeypatch.setenv("APP_ACCESS_TOKEN", "correct")
    app.dependency_overrides[
        get_course_request_parser
    ] = lambda: FakeParser()

    try:
        response = client.post(
            "/parse",
            headers={"X-Token": "correct"},
            json={"text": "Watch CS 136 and ECE 106"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422


def test_openapi_documents_parse_security(client):
    document = client.get("/openapi.json").json()
    operation = document["paths"]["/parse"]["post"]

    assert document["info"]["version"] == "2.0.0"
    assert operation["security"]
    assert "APIKeyHeader" in document["components"]["securitySchemes"]


@pytest.mark.parametrize(
    "payload",
    [
        {"text": "   "},
        {},
        {"text": 123},
        {"text": "x" * 501},
    ],
    ids=["blank", "missing", "wrong-type", "overlong"],
)
def test_parse_request_validation_is_sanitized(
    client,
    monkeypatch,
    payload,
):
    monkeypatch.setenv("APP_ACCESS_TOKEN", "correct")
    app.dependency_overrides[
        get_course_request_parser
    ] = lambda: FakeParser()

    try:
        response = client.post(
            "/parse",
            headers={"X-Token": "correct"},
            json=payload,
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert response.json() == {
        "detail": (
            "The parse request must include 1 to 500 "
            "characters of text."
        )
    }


def test_v1_request_validation_keeps_detail_list(client):
    response = client.post(
        "/watches",
        json={"subject": "CS123", "catalog": "136"},
    )

    assert response.status_code == 422
    assert isinstance(response.json()["detail"], list)


@pytest.mark.parametrize(
    ("service_error", "expected_status", "expected_detail"),
    [
        (
            ModelServiceError(
                "The model service could not parse the request."
            ),
            502,
            "The model service could not parse the request.",
        ),
        (
            ModelOutputError(
                "The model returned an unusable course request."
            ),
            502,
            "The model returned an unusable course request.",
        ),
        (
            ConfigurationError(
                "OpenAI parsing is not configured."
            ),
            503,
            "OpenAI parsing is not configured.",
        ),
    ],
)
def test_parse_maps_public_service_errors(
    client,
    monkeypatch,
    service_error,
    expected_status,
    expected_detail,
):
    monkeypatch.setenv("APP_ACCESS_TOKEN", "correct")

    def raise_service_error():
        raise service_error

    app.dependency_overrides[
        get_course_request_parser
    ] = raise_service_error

    try:
        response = client.post(
            "/parse",
            headers={"X-Token": "correct"},
            json={"text": "Watch CS 136"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == expected_status
    assert response.json() == {"detail": expected_detail}
    assert "secret" not in response.text.lower()
