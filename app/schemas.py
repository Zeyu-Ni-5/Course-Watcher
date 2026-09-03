# app/schemas.py

from datetime import datetime
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictInt,
    field_validator,
    model_validator,
)


class WatchCreate(BaseModel):
    subject: str
    catalog: str
    component: str | None = None
    term_code: str | None = None

    @field_validator("subject")
    @classmethod
    def validate_subject(cls, value: str) -> str:
        normalized = value.strip().upper()

        if not normalized.isalpha():
            raise ValueError(
                "Subject must contain letters only."
            )

        return normalized

    @field_validator("catalog")
    @classmethod
    def validate_catalog(cls, value: str) -> str:
        normalized = value.strip().upper()

        if not normalized:
            raise ValueError(
                "Catalog must not be empty."
            )

        if any(
            character.isspace()
            for character in normalized
        ):
            raise ValueError(
                "Catalog must not contain spaces."
            )

        return normalized

    @field_validator("component")
    @classmethod
    def validate_component(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        normalized = value.strip().upper()

        if not normalized.isalpha():
            raise ValueError(
                "Component must contain letters only."
            )

        return normalized

    @field_validator("term_code")
    @classmethod
    def validate_term_code(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        normalized = value.strip()

        if (
            len(normalized) != 4
            or not normalized.isdigit()
        ):
            raise ValueError(
                "Term code must contain exactly four digits."
            )

        return normalized


class WatchUpdate(BaseModel):
    active: bool


class WatchRead(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int
    subject: str
    catalog: str
    component: str | None
    term_code: str
    active: bool
    created_at: datetime


class SectionStatus(BaseModel):
    section: str
    component: str
    enrolled_total: int
    capacity: int
    status: Literal["OPEN", "FULL"]


class WatchStatusRead(BaseModel):
    watch_id: int
    term_code: str
    checked_at: datetime
    sections: list[SectionStatus]


class ParseRequest(BaseModel):
    text: str

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        normalized = value.strip()

        if not 1 <= len(normalized) <= 500:
            raise ValueError(
                "Text must contain between 1 and 500 characters."
            )

        return normalized


class ModelCourseFields(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject: str | None
    catalog: str | None
    component: str | None
    term_season: Literal["WINTER", "SPRING", "FALL"] | None
    term_year: StrictInt | None = Field(ge=2000, le=2099)

    @model_validator(mode="after")
    def validate_term_pair(self):
        if (self.term_season is None) != (self.term_year is None):
            raise ValueError(
                "Term season and year must be provided together."
            )

        return self


class ParsePreview(WatchCreate):
    pass
