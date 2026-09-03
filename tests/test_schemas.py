# tests/test_schemas.py

import pytest
from pydantic import ValidationError

from app.schemas import (
    ModelCourseFields,
    ParsePreview,
    ParseRequest,
    WatchCreate,
)


def test_parse_request_strips_text():
    request = ParseRequest(
        text="  Watch CS 136 lectures  "
    )

    assert request.text == "Watch CS 136 lectures"


@pytest.mark.parametrize("text", ["", "   ", "x" * 501])
def test_parse_request_rejects_invalid_length(text):
    with pytest.raises(ValidationError):
        ParseRequest(text=text)


def test_model_course_fields_requires_term_pair():
    with pytest.raises(ValidationError):
        ModelCourseFields(
            subject="CS",
            catalog="136",
            component="LEC",
            term_season="FALL",
            term_year=None,
        )


def test_model_course_fields_forbids_extra_fields():
    with pytest.raises(ValidationError):
        ModelCourseFields.model_validate(
            {
                "subject": "CS",
                "catalog": "136",
                "component": None,
                "term_season": None,
                "term_year": None,
                "confidence": 0.9,
            }
        )


def test_model_course_fields_rejects_string_term_year():
    with pytest.raises(ValidationError):
        ModelCourseFields(
            subject="CS",
            catalog="136",
            component="LEC",
            term_season="FALL",
            term_year="2026",
        )


def test_parse_preview_reuses_watch_normalization():
    preview = ParsePreview(
        subject=" cs ",
        catalog=" 136 ",
        component=" lec ",
        term_code="1269",
    )

    assert preview.model_dump() == {
        "subject": "CS",
        "catalog": "136",
        "component": "LEC",
        "term_code": "1269",
    }


def test_watch_create_normalizes_input():
    watch = WatchCreate(
        subject=" cs ",
        catalog=" 136 ",
        component=" lec ",
    )

    assert watch.subject == "CS"
    assert watch.catalog == "136"
    assert watch.component == "LEC"
    assert watch.term_code is None


def test_watch_create_allows_null_component():
    watch = WatchCreate(
        subject="CS",
        catalog="136",
        component=None,
        term_code="1269",
    )

    assert watch.component is None


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("subject", "CS123"),
        ("catalog", "13 6"),
        ("component", "LEC1"),
        ("term_code", "fall-2026"),
    ],
)
def test_watch_create_rejects_invalid_fields(field, value):
    payload = {
        "subject": "CS",
        "catalog": "136",
        "component": "LEC",
        "term_code": "1269",
    }
    payload[field] = value

    with pytest.raises(ValidationError):
        WatchCreate(**payload)
