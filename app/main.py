# app/main.py

from fastapi import FastAPI, Request
from fastapi.exception_handlers import (
    request_validation_exception_handler,
)
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.database import Base, engine
from app.errors import (
    ConfigurationError,
    CourseNotFoundError,
    DuplicateWatchError,
    ModelOutputError,
    ModelServiceError,
    NoMatchingSectionsError,
    ParseInputError,
    UWAPIError,
    WatchNotFoundError,
)
from app.routers.parse import router as parse_router
from app.routers.watches import router as watches_router

import app.models


Base.metadata.create_all(bind=engine)


app = FastAPI(
    title="Course Watcher",
    version="2.0.0",
    description=(
        "Monitor University of Waterloo "
        "course enrollment."
    ),
)


@app.exception_handler(RequestValidationError)
async def handle_request_validation_error(
    request: Request,
    error: RequestValidationError,
):
    if request.url.path == "/parse":
        return JSONResponse(
            status_code=422,
            content={
                "detail": (
                    "The parse request must include 1 to 500 "
                    "characters of text."
                )
            },
        )

    return await request_validation_exception_handler(
        request,
        error,
    )


@app.get("/health", include_in_schema=False)
def health():
    return {"status": "ok"}


@app.exception_handler(ParseInputError)
async def handle_parse_input_error(
    _request: Request,
    error: ParseInputError,
):
    return JSONResponse(
        status_code=422,
        content={"detail": str(error)},
    )


@app.exception_handler(ModelServiceError)
@app.exception_handler(ModelOutputError)
async def handle_model_error(
    _request: Request,
    error: ModelServiceError | ModelOutputError,
):
    return JSONResponse(
        status_code=502,
        content={"detail": str(error)},
    )


@app.exception_handler(ConfigurationError)
async def handle_configuration_error(
    _request: Request,
    error: ConfigurationError,
):
    return JSONResponse(
        status_code=503,
        content={"detail": str(error)},
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
app.include_router(parse_router)
