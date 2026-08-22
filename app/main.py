# app/main.py

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.database import Base, engine
from app.errors import (
    CourseNotFoundError,
    DuplicateWatchError,
    NoMatchingSectionsError,
    UWAPIError,
    WatchNotFoundError,
)
from app.routers.watches import router as watches_router

import app.models


Base.metadata.create_all(bind=engine)


app = FastAPI(
    title="Course Watcher",
    version="1.0.0",
    description=(
        "Monitor University of Waterloo "
        "course enrollment."
    ),
)


@app.exception_handler(WatchNotFoundError)
async def handle_watch_not_found(
    _request: Request,
    error: WatchNotFoundError,
):
    return JSONResponse(
        status_code=404,
        content={"detail": str(error)},
    )


@app.exception_handler(CourseNotFoundError)
async def handle_course_not_found(
    _request: Request,
    error: CourseNotFoundError,
):
    return JSONResponse(
        status_code=404,
        content={"detail": str(error)},
    )


@app.exception_handler(NoMatchingSectionsError)
async def handle_no_matching_sections(
    _request: Request,
    error: NoMatchingSectionsError,
):
    return JSONResponse(
        status_code=404,
        content={"detail": str(error)},
    )


@app.exception_handler(DuplicateWatchError)
async def handle_duplicate_watch(
    _request: Request,
    error: DuplicateWatchError,
):
    return JSONResponse(
        status_code=409,
        content={"detail": str(error)},
    )


@app.exception_handler(UWAPIError)
async def handle_uw_api_error(
    _request: Request,
    error: UWAPIError,
):
    return JSONResponse(
        status_code=502,
        content={"detail": str(error)},
    )


app.include_router(watches_router)