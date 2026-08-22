# tests/test_uw_client.py

import httpx
import pytest

from app.errors import CourseNotFoundError, UWAPIError
from app.uw_client import UWClient


def test_get_current_term_returns_term_code():
    def handler(request):
        assert request.url.path == "/v3/Terms/current"
        assert request.headers["x-api-key"] == "test-key"

        return httpx.Response(
            200,
            json={"termCode": "1269"},
        )

    client = UWClient(
        api_key="test-key",
        transport=httpx.MockTransport(handler),
    )

    assert client.get_current_term() == "1269"


def test_get_course_sections_returns_section_list():
    def handler(request):
        assert request.url.path == "/v3/ClassSchedules/1269/CS/136"

        return httpx.Response(
            200,
            json=[
                {
                    "courseComponent": "LEC",
                    "classSection": 1,
                    "enrolledStudents": 100,
                    "maxEnrollmentCapacity": 120,
                }
            ],
        )

    client = UWClient(
        api_key="test-key",
        transport=httpx.MockTransport(handler),
    )

    sections = client.get_course_sections(
        term_code="1269",
        subject="CS",
        catalog="136",
    )

    assert sections == [
        {
            "courseComponent": "LEC",
            "classSection": 1,
            "enrolledStudents": 100,
            "maxEnrollmentCapacity": 120,
        }
    ]


def test_get_course_sections_rejects_empty_result():
    def handler(_request):
        return httpx.Response(200, json=[])

    client = UWClient(
        api_key="test-key",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(CourseNotFoundError):
        client.get_course_sections("1269", "CS", "999")


def test_rejected_api_key_raises_uw_api_error():
    def handler(_request):
        return httpx.Response(403, json={"message": "Forbidden"})

    client = UWClient(
        api_key="bad-key",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(
        UWAPIError,
        match="The UW API key was rejected.",
    ):
        client.get_current_term()


def test_missing_api_key_raises_uw_api_error(monkeypatch):
    monkeypatch.delenv("UW_API_KEY", raising=False)

    client = UWClient(api_key=None)

    with pytest.raises(
        UWAPIError,
        match="UW_API_KEY is not set",
    ):
        client.get_current_term()


@pytest.mark.parametrize(
    "term_code",
    [
        True,
        1269,
        ["1269"],
        {"code": "1269"},
        "fall",
        "12690",
    ],
)
def test_get_current_term_rejects_invalid_term_code(
    term_code,
):
    def handler(_request):
        return httpx.Response(
            200,
            json={"termCode": term_code},
        )

    client = UWClient(
        api_key="test-key",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(
        UWAPIError,
        match="The UW API returned an invalid current term.",
    ):
        client.get_current_term()