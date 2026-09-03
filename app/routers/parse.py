from typing import Annotated

from fastapi import APIRouter, Depends, Security

from app.auth import (
    parse_token_header,
    require_parse_token,
)
from app.parsing.base import CourseRequestParser
from app.parsing.openai_parser import create_openai_parser
from app.schemas import ParsePreview, ParseRequest
from app.services.parse_service import parse_course_request
from app.settings import ParseSettings, get_parse_settings


router = APIRouter(tags=["parsing"])


def get_course_request_parser(
    settings: Annotated[
        ParseSettings,
        Depends(get_parse_settings),
    ],
) -> CourseRequestParser:
    return create_openai_parser(settings)


def authorize_parse(
    supplied_token: Annotated[
        str | None,
        Security(parse_token_header),
    ],
    settings: Annotated[
        ParseSettings,
        Depends(get_parse_settings),
    ],
) -> None:
    require_parse_token(supplied_token, settings)


@router.post(
    "/parse",
    response_model=ParsePreview,
    dependencies=[Depends(authorize_parse)],
)
def parse_course(
    payload: ParseRequest,
    parser: Annotated[
        CourseRequestParser,
        Depends(get_course_request_parser),
    ],
):
    return parse_course_request(parser, payload.text)
