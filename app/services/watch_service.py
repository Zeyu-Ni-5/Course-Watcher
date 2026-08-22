# app/services/watch_service.py

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.errors import (
    DuplicateWatchError,
    NoMatchingSectionsError,
    UWAPIError,
    WatchNotFoundError,
)
from app.models import Snapshot, Watch
from app.schemas import WatchCreate, WatchUpdate
from app.uw_client import uw_client


def _component_condition(
    component: str | None,
):
    if component is None:
        return Watch.component.is_(None)

    return Watch.component == component


def _find_duplicate_watch(
    database: Session,
    payload: WatchCreate,
    term_code: str,
) -> Watch | None:
    statement = select(Watch).where(
        Watch.subject == payload.subject,
        Watch.catalog == payload.catalog,
        _component_condition(payload.component),
        Watch.term_code == term_code,
    )

    return database.scalar(statement)


def create_watch(
    database: Session,
    payload: WatchCreate,
) -> Watch:
    term_code = (
        payload.term_code
        or uw_client.get_current_term()
    )

    duplicate = _find_duplicate_watch(
        database,
        payload,
        term_code,
    )

    if duplicate is not None:
        raise DuplicateWatchError(
            "This watch already exists."
        )

    watch = Watch(
        subject=payload.subject,
        catalog=payload.catalog,
        component=payload.component,
        term_code=term_code,
        active=True,
    )

    database.add(watch)

    try:
        database.commit()

    except IntegrityError as error:
        database.rollback()

        duplicate = _find_duplicate_watch(
            database,
            payload,
            term_code,
        )

        if duplicate is not None:
            raise DuplicateWatchError(
                "This watch already exists."
            ) from error

        raise

    database.refresh(watch)

    return watch


def list_watches(
    database: Session,
    active: bool | None = None,
) -> list[Watch]:
    statement = select(Watch).order_by(Watch.id)

    if active is not None:
        statement = statement.where(
            Watch.active == active
        )

    return list(
        database.scalars(statement).all()
    )


def get_watch(
    database: Session,
    watch_id: int,
) -> Watch:
    watch = database.get(Watch, watch_id)

    if watch is None:
        raise WatchNotFoundError(
            f"Watch {watch_id} was not found."
        )

    return watch


def update_watch(
    database: Session,
    watch_id: int,
    payload: WatchUpdate,
) -> Watch:
    watch = get_watch(database, watch_id)
    watch.active = payload.active

    database.commit()
    database.refresh(watch)

    return watch


def delete_watch(
    database: Session,
    watch_id: int,
) -> None:
    watch = get_watch(database, watch_id)

    database.delete(watch)
    database.commit()


def _parse_integer(
    value: Any,
    *,
    minimum: int,
) -> int:
    if isinstance(value, bool):
        raise ValueError(
            "Boolean is not a valid integer."
        )

    if isinstance(value, int):
        parsed_value = value

    elif (
        isinstance(value, str)
        and value.strip().isdigit()
    ):
        parsed_value = int(value.strip())

    else:
        raise ValueError(
            "Value is not a valid integer."
        )

    if parsed_value < minimum:
        raise ValueError(
            f"Value must be at least {minimum}."
        )

    return parsed_value


def _convert_section(
    section: dict[str, Any],
    subject: str,
    catalog: str,
) -> dict[str, Any]:
    try:
        raw_component = section[
            "courseComponent"
        ]

        if not isinstance(raw_component, str):
            raise ValueError(
                "Course component must be a string."
            )

        component = (
            raw_component.strip().upper()
        )

        if (
            not component
            or not component.isalpha()
        ):
            raise ValueError(
                "Course component is invalid."
            )

        section_number = _parse_integer(
            section["classSection"],
            minimum=1,
        )
        enrolled_total = _parse_integer(
            section["enrolledStudents"],
            minimum=0,
        )
        capacity = _parse_integer(
            section["maxEnrollmentCapacity"],
            minimum=0,
        )

    except (KeyError, TypeError, ValueError) as error:
        raise UWAPIError(
            f"The UW API returned invalid or incomplete "
            f"data for {subject} {catalog}."
        ) from error

    return {
        "section": (
            f"{component} {section_number:03d}"
        ),
        "component": component,
        "enrolled_total": enrolled_total,
        "capacity": capacity,
        "status": (
            "OPEN"
            if enrolled_total < capacity
            else "FULL"
        ),
    }


def check_watch_status(
    database: Session,
    watch_id: int,
) -> dict[str, Any]:
    watch = get_watch(database, watch_id)

    sections = uw_client.get_course_sections(
        term_code=watch.term_code,
        subject=watch.subject,
        catalog=watch.catalog,
    )

    matched_sections = []

    for raw_section in sections:
        section = _convert_section(
            raw_section,
            watch.subject,
            watch.catalog,
        )

        if (
            watch.component is not None
            and section["component"]
            != watch.component
        ):
            continue

        matched_sections.append(section)

    if not matched_sections:
        component_text = (
            watch.component or "requested"
        )

        raise NoMatchingSectionsError(
            f"No matching {component_text} sections "
            f"found for {watch.subject} {watch.catalog}."
        )

    checked_at = datetime.now(timezone.utc)

    snapshots = [
        Snapshot(
            watch_id=watch.id,
            section=section["section"],
            enrolled_total=section[
                "enrolled_total"
            ],
            capacity=section["capacity"],
            checked_at=checked_at,
        )
        for section in matched_sections
    ]

    database.add_all(snapshots)
    database.commit()

    return {
        "watch_id": watch.id,
        "term_code": watch.term_code,
        "checked_at": checked_at,
        "sections": matched_sections,
    }