from collections.abc import Mapping

import pytest

from app.errors import (
    ModelOutputError,
    ModelResponseInvalidError,
    ModelServiceError,
    ParseInputError,
)
from app.services.parse_service import parse_course_request


class FakeParser:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = []

    def parse(
        self,
        text: str,
        *,
        feedback: str | None = None,
    ) -> Mapping[str, object]:
        self.calls.append((text, feedback))
        outcome = self.outcomes.pop(0)

        if isinstance(outcome, Exception):
            raise outcome

        return outcome


def valid_fields(**overrides):
    fields = {
        "subject": "CS",
        "catalog": "136",
        "component": "LEC",
        "term_season": "FALL",
        "term_year": 2026,
    }
    fields.update(overrides)
    return fields


def test_parse_course_request_returns_normalized_preview():
    parser = FakeParser([valid_fields(subject=" cs ")])

    result = parse_course_request(
        parser,
        "Watch CS 136 lectures in Fall 2026",
    )

    assert result.model_dump() == {
        "subject": "CS",
        "catalog": "136",
        "component": "LEC",
        "term_code": "1269",
    }
    assert parser.calls == [
        ("Watch CS 136 lectures in Fall 2026", None)
    ]


def test_parse_course_request_preserves_optional_nulls():
    parser = FakeParser(
        [
            valid_fields(
                component=None,
                term_season=None,
                term_year=None,
            )
        ]
    )

    result = parse_course_request(parser, "Watch CS 136")

    assert result.component is None
    assert result.term_code is None


def test_parse_course_request_rejects_no_single_course():
    parser = FakeParser(
        [
            {
                "subject": None,
                "catalog": None,
                "component": None,
                "term_season": None,
                "term_year": None,
            }
        ]
    )

    with pytest.raises(ParseInputError):
        parse_course_request(parser, "Watch CS 136 and ECE 106")

    assert len(parser.calls) == 1


def test_parse_course_request_repairs_one_invalid_response():
    parser = FakeParser(
        [
            valid_fields(term_season="AUTUMN"),
            valid_fields(),
        ]
    )

    result = parse_course_request(parser, "Watch CS 136 in Fall 2026")

    assert result.term_code == "1269"
    assert len(parser.calls) == 2
    assert parser.calls[0][1] is None
    assert "term_season" in parser.calls[1][1]
    assert "AUTUMN" not in parser.calls[1][1]


def test_parse_course_request_fails_after_two_invalid_responses():
    parser = FakeParser(
        [
            ModelResponseInvalidError("No parsed output."),
            ModelResponseInvalidError("No parsed output."),
        ]
    )

    with pytest.raises(ModelOutputError):
        parse_course_request(parser, "Watch CS 136")

    assert len(parser.calls) == 2


def test_parse_course_request_does_not_retry_service_errors():
    parser = FakeParser(
        [ModelServiceError("The model service timed out.")]
    )

    with pytest.raises(ModelServiceError):
        parse_course_request(parser, "Watch CS 136")

    assert len(parser.calls) == 1
