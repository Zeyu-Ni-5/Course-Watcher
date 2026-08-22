# tests/test_schemas.py

import pytest
from pydantic import ValidationError

from app.schemas import WatchCreate


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