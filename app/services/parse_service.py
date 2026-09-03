from pydantic import ValidationError

from app.errors import (
    ModelOutputError,
    ModelResponseInvalidError,
    ParseInputError,
)
from app.parsing.base import CourseRequestParser
from app.schemas import (
    ModelCourseFields,
    ParsePreview,
)


TERM_DIGITS = {
    "WINTER": "1",
    "SPRING": "5",
    "FALL": "9",
}


def _term_code(
    season: str | None,
    year: int | None,
) -> str | None:
    if season is None or year is None:
        return None

    return f"1{year % 100:02d}{TERM_DIGITS[season]}"


def _feedback(error: Exception) -> str:
    if isinstance(error, ValidationError):
        messages = []

        for item in error.errors(include_input=False):
            location = ".".join(
                str(part) for part in item["loc"]
            )
            messages.append(
                f"{location}: {item['msg']}"
            )

        return "; ".join(messages)[:500]

    return "The previous response did not contain parsed fields."


def _preview(fields: ModelCourseFields) -> ParsePreview:
    if fields.subject is None or fields.catalog is None:
        raise ParseInputError(
            "Text must identify exactly one course."
        )

    return ParsePreview(
        subject=fields.subject,
        catalog=fields.catalog,
        component=fields.component,
        term_code=_term_code(
            fields.term_season,
            fields.term_year,
        ),
    )


def parse_course_request(
    parser: CourseRequestParser,
    text: str,
) -> ParsePreview:
    feedback = None

    for attempt in range(2):
        try:
            raw_fields = parser.parse(
                text,
                feedback=feedback,
            )
            fields = ModelCourseFields.model_validate(
                raw_fields
            )
            return _preview(fields)

        except ParseInputError:
            raise

        except (
            ModelResponseInvalidError,
            ValidationError,
        ) as error:
            if attempt == 1:
                raise ModelOutputError(
                    "The model returned invalid course data."
                ) from error

            feedback = _feedback(error)

    raise AssertionError("Parse retry loop did not return or raise.")
