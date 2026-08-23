# tests/test_watches.py

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.errors import UWAPIError
from app.models import Snapshot, Watch
from app.services import watch_service


def create_watch(
    client,
    *,
    subject="CS",
    catalog="136",
    component="LEC",
    term_code="1269",
):
    response = client.post(
        "/watches",
        json={
            "subject": subject,
            "catalog": catalog,
            "component": component,
            "term_code": term_code,
        },
    )

    assert response.status_code == 201
    return response.json()


def test_create_watch_with_provided_term(client):
    response = client.post(
        "/watches",
        json={
            "subject": "cs",
            "catalog": "136",
            "component": "lec",
            "term_code": "1269",
        },
    )

    assert response.status_code == 201

    body = response.json()

    assert body["id"] == 1
    assert body["subject"] == "CS"
    assert body["catalog"] == "136"
    assert body["component"] == "LEC"
    assert body["term_code"] == "1269"
    assert body["active"] is True


def test_create_watch_uses_current_term_when_missing(
    client,
    monkeypatch,
):
    monkeypatch.setattr(
        watch_service.uw_client,
        "get_current_term",
        lambda: "1269",
    )

    response = client.post(
        "/watches",
        json={
            "subject": "CS",
            "catalog": "136",
        },
    )

    assert response.status_code == 201
    assert response.json()["term_code"] == "1269"
    assert response.json()["component"] is None


def test_create_watch_missing_subject_returns_422(client):
    response = client.post(
        "/watches",
        json={
            "catalog": "136",
            "term_code": "1269",
        },
    )

    assert response.status_code == 422


def test_duplicate_watch_returns_409(client):
    payload = {
        "subject": "CS",
        "catalog": "136",
        "component": None,
        "term_code": "1269",
    }

    first_response = client.post("/watches", json=payload)
    second_response = client.post("/watches", json=payload)

    assert first_response.status_code == 201
    assert second_response.status_code == 409


def test_list_watches_filters_active(client):
    first = create_watch(
        client,
        subject="CS",
        catalog="136",
    )
    create_watch(
        client,
        subject="ECE",
        catalog="106",
    )

    patch_response = client.patch(
        f"/watches/{first['id']}",
        json={"active": False},
    )

    assert patch_response.status_code == 200

    active_response = client.get(
        "/watches",
        params={"active": True},
    )
    inactive_response = client.get(
        "/watches",
        params={"active": False},
    )

    assert active_response.status_code == 200
    assert inactive_response.status_code == 200

    assert [watch["subject"] for watch in active_response.json()] == [
        "ECE"
    ]
    assert [watch["subject"] for watch in inactive_response.json()] == [
        "CS"
    ]


def test_get_watch(client):
    created = create_watch(client)

    response = client.get(f"/watches/{created['id']}")

    assert response.status_code == 200
    assert response.json() == created


def test_get_missing_watch_returns_404(client):
    response = client.get("/watches/999")

    assert response.status_code == 404


def test_patch_watch_active(client):
    created = create_watch(client)

    response = client.patch(
        f"/watches/{created['id']}",
        json={"active": False},
    )

    assert response.status_code == 200
    assert response.json()["active"] is False


def test_delete_watch_returns_204(client):
    created = create_watch(client)

    delete_response = client.delete(
        f"/watches/{created['id']}"
    )
    get_response = client.get(
        f"/watches/{created['id']}"
    )

    assert delete_response.status_code == 204
    assert delete_response.content == b""
    assert get_response.status_code == 404


def test_status_skips_null_component_before_valid_lec(
    client,
    db_session,
    monkeypatch,
):
    monkeypatch.setattr(
        watch_service.uw_client,
        "get_course_sections",
        lambda term_code, subject, catalog: [
            {
                "courseComponent": None,
                "classSection": 99,
                "enrolledStudents": 10,
                "maxEnrollmentCapacity": 20,
            },
            {
                "courseComponent": "LEC",
                "classSection": 1,
                "enrolledStudents": 100,
                "maxEnrollmentCapacity": 120,
            },
        ],
    )

    created = create_watch(
        client,
        component="LEC",
    )

    response = client.get(
        f"/watches/{created['id']}/status"
    )

    assert response.status_code == 200

    assert response.json()["sections"] == [
        {
            "section": "LEC 001",
            "component": "LEC",
            "enrolled_total": 100,
            "capacity": 120,
            "status": "OPEN",
        }
    ]

    snapshots = db_session.scalars(
        select(Snapshot)
    ).all()

    assert len(snapshots) == 1
    assert snapshots[0].section == "LEC 001"


def test_status_filters_component_and_saves_snapshot(
    client,
    db_session,
    monkeypatch,
):
    monkeypatch.setattr(
        watch_service.uw_client,
        "get_course_sections",
        lambda term_code, subject, catalog: [
            {
                "courseComponent": "LEC",
                "classSection": 1,
                "enrolledStudents": 100,
                "maxEnrollmentCapacity": 120,
            },
            {
                "courseComponent": "LAB",
                "classSection": 101,
                "enrolledStudents": 30,
                "maxEnrollmentCapacity": 30,
            },
        ],
    )

    created = create_watch(
        client,
        component="LEC",
    )

    response = client.get(
        f"/watches/{created['id']}/status"
    )

    assert response.status_code == 200

    body = response.json()

    assert body["watch_id"] == created["id"]
    assert body["term_code"] == "1269"
    assert body["sections"] == [
        {
            "section": "LEC 001",
            "component": "LEC",
            "enrolled_total": 100,
            "capacity": 120,
            "status": "OPEN",
        }
    ]

    snapshots = db_session.scalars(
        select(Snapshot)
    ).all()

    assert len(snapshots) == 1
    assert snapshots[0].section == "LEC 001"
    assert snapshots[0].enrolled_total == 100
    assert snapshots[0].capacity == 120


def test_null_component_returns_and_saves_all_sections(
    client,
    db_session,
    monkeypatch,
):
    monkeypatch.setattr(
        watch_service.uw_client,
        "get_course_sections",
        lambda term_code, subject, catalog: [
            {
                "courseComponent": "LEC",
                "classSection": 1,
                "enrolledStudents": 120,
                "maxEnrollmentCapacity": 120,
            },
            {
                "courseComponent": "LAB",
                "classSection": 101,
                "enrolledStudents": 20,
                "maxEnrollmentCapacity": 30,
            },
        ],
    )

    created = create_watch(
        client,
        component=None,
    )

    response = client.get(
        f"/watches/{created['id']}/status"
    )

    assert response.status_code == 200
    assert response.json()["sections"] == [
        {
            "section": "LEC 001",
            "component": "LEC",
            "enrolled_total": 120,
            "capacity": 120,
            "status": "FULL",
        },
        {
            "section": "LAB 101",
            "component": "LAB",
            "enrolled_total": 20,
            "capacity": 30,
            "status": "OPEN",
        },
    ]

    snapshot_count = db_session.scalar(
        select(func.count())
        .select_from(Snapshot)
    )

    assert snapshot_count == 2


def test_delete_watch_cascades_snapshots(
    client,
    db_session,
    monkeypatch,
):
    monkeypatch.setattr(
        watch_service.uw_client,
        "get_course_sections",
        lambda term_code, subject, catalog: [
            {
                "courseComponent": "LEC",
                "classSection": 1,
                "enrolledStudents": 100,
                "maxEnrollmentCapacity": 120,
            }
        ],
    )

    created = create_watch(client)

    status_response = client.get(
        f"/watches/{created['id']}/status"
    )

    assert status_response.status_code == 200

    client.delete(f"/watches/{created['id']}")

    snapshot_count = db_session.scalar(
        select(func.count())
        .select_from(Snapshot)
    )

    assert snapshot_count == 0


def test_status_uw_api_error_returns_502(
    client,
    monkeypatch,
):
    def raise_error(term_code, subject, catalog):
        from app.errors import UWAPIError

        raise UWAPIError("The UW API request timed out.")

    monkeypatch.setattr(
        watch_service.uw_client,
        "get_course_sections",
        raise_error,
    )

    created = create_watch(client)

    response = client.get(
        f"/watches/{created['id']}/status"
    )

    assert response.status_code == 502


def test_openapi_contains_six_watch_routes(client):
    response = client.get("/openapi.json")

    assert response.status_code == 200

    paths = response.json()["paths"]

    assert {"post", "get"} <= set(paths["/watches"])
    assert {"get", "patch", "delete"} <= set(
        paths["/watches/{watch_id}"]
    )
    assert {"get"} <= set(
        paths["/watches/{watch_id}/status"]
    )


def test_database_rejects_duplicate_watch_with_null_component(
    db_session,
):
    first_watch = Watch(
        subject="CS",
        catalog="136",
        component=None,
        term_code="1269",
        active=True,
    )

    db_session.add(first_watch)
    db_session.commit()

    duplicate_watch = Watch(
        subject="CS",
        catalog="136",
        component=None,
        term_code="1269",
        active=True,
    )

    db_session.add(duplicate_watch)

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


def test_status_rejects_malformed_section_data(
    client,
    db_session,
    monkeypatch,
):
    monkeypatch.setattr(
        watch_service.uw_client,
        "get_course_sections",
        lambda term_code, subject, catalog: [
            {
                "courseComponent": "LEC",
                "classSection": None,
                "enrolledStudents": 20,
                "maxEnrollmentCapacity": 30,
            }
        ],
    )

    created = create_watch(
        client,
        component="LEC",
    )

    response = client.get(
        f"/watches/{created['id']}/status"
    )

    assert response.status_code == 502

    snapshot_count = db_session.scalar(
        select(func.count()).select_from(Snapshot)
    )

    assert snapshot_count == 0


def test_status_rejects_negative_enrollment(
    client,
    db_session,
    monkeypatch,
):
    monkeypatch.setattr(
        watch_service.uw_client,
        "get_course_sections",
        lambda term_code, subject, catalog: [
            {
                "courseComponent": "LEC",
                "classSection": 1,
                "enrolledStudents": -1,
                "maxEnrollmentCapacity": 30,
            }
        ],
    )

    created = create_watch(client)

    response = client.get(
        f"/watches/{created['id']}/status"
    )

    assert response.status_code == 502

    snapshot_count = db_session.scalar(
        select(func.count()).select_from(Snapshot)
    )

    assert snapshot_count == 0


def test_status_returns_404_when_component_has_no_match(
    client,
    db_session,
    monkeypatch,
):
    monkeypatch.setattr(
        watch_service.uw_client,
        "get_course_sections",
        lambda term_code, subject, catalog: [
            {
                "courseComponent": "LAB",
                "classSection": 101,
                "enrolledStudents": 20,
                "maxEnrollmentCapacity": 30,
            }
        ],
    )

    created = create_watch(
        client,
        component="LEC",
    )

    response = client.get(
        f"/watches/{created['id']}/status"
    )

    assert response.status_code == 404

    snapshot_count = db_session.scalar(
        select(func.count()).select_from(Snapshot)
    )

    assert snapshot_count == 0


def test_repeated_status_checks_preserve_history(
    client,
    db_session,
    monkeypatch,
):
    monkeypatch.setattr(
        watch_service.uw_client,
        "get_course_sections",
        lambda term_code, subject, catalog: [
            {
                "courseComponent": "LEC",
                "classSection": 1,
                "enrolledStudents": 100,
                "maxEnrollmentCapacity": 120,
            }
        ],
    )

    created = create_watch(client)

    first_response = client.get(
        f"/watches/{created['id']}/status"
    )
    second_response = client.get(
        f"/watches/{created['id']}/status"
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    snapshot_count = db_session.scalar(
        select(func.count()).select_from(Snapshot)
    )

    assert snapshot_count == 2


def test_create_watch_current_term_error_returns_502(
    client,
    monkeypatch,
):
    def raise_current_term_error():
        raise UWAPIError(
            "The UW API returned an invalid current term."
        )

    monkeypatch.setattr(
        watch_service.uw_client,
        "get_current_term",
        raise_current_term_error,
    )

    response = client.post(
        "/watches",
        json={
            "subject": "CS",
            "catalog": "136",
        },
    )

    assert response.status_code == 502
    assert response.json() == {
        "detail": (
            "The UW API returned an invalid current term."
        )
    }


def test_database_rejects_duplicate_watch_with_component(
    db_session,
):
    first_watch = Watch(
        subject="CS",
        catalog="136",
        component="LEC",
        term_code="1269",
        active=True,
    )

    db_session.add(first_watch)
    db_session.commit()

    duplicate_watch = Watch(
        subject="CS",
        catalog="136",
        component="LEC",
        term_code="1269",
        active=True,
    )

    db_session.add(duplicate_watch)

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()