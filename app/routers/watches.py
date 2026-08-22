# app/routers/watches.py

from fastapi import (
    APIRouter,
    Depends,
    Response,
    status,
)
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import (
    WatchCreate,
    WatchRead,
    WatchStatusRead,
    WatchUpdate,
)
from app.services import watch_service


router = APIRouter(
    prefix="/watches",
    tags=["watches"],
)


@router.post(
    "",
    response_model=WatchRead,
    status_code=status.HTTP_201_CREATED,
)
def create_watch(
    payload: WatchCreate,
    database: Session = Depends(get_db),
):
    return watch_service.create_watch(
        database,
        payload,
    )


@router.get(
    "",
    response_model=list[WatchRead],
)
def list_watches(
    active: bool | None = None,
    database: Session = Depends(get_db),
):
    return watch_service.list_watches(
        database,
        active,
    )


@router.get(
    "/{watch_id}",
    response_model=WatchRead,
)
def get_watch(
    watch_id: int,
    database: Session = Depends(get_db),
):
    return watch_service.get_watch(
        database,
        watch_id,
    )


@router.patch(
    "/{watch_id}",
    response_model=WatchRead,
)
def update_watch(
    watch_id: int,
    payload: WatchUpdate,
    database: Session = Depends(get_db),
):
    return watch_service.update_watch(
        database,
        watch_id,
        payload,
    )


@router.delete(
    "/{watch_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_watch(
    watch_id: int,
    database: Session = Depends(get_db),
):
    watch_service.delete_watch(
        database,
        watch_id,
    )

    return Response(
        status_code=status.HTTP_204_NO_CONTENT
    )


@router.get(
    "/{watch_id}/status",
    response_model=WatchStatusRead,
)
def get_watch_status(
    watch_id: int,
    database: Session = Depends(get_db),
):
    return watch_service.check_watch_status(
        database,
        watch_id,
    )