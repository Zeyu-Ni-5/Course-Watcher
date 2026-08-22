# app/uw_client.py

import os
from typing import Any
from urllib.parse import quote

import httpx

from app.errors import CourseNotFoundError, UWAPIError


API_BASE_URL = "https://openapi.data.uwaterloo.ca"


class UWClient:
    def __init__(
        self,
        api_key: str | None = None,
        timeout: float = 10.0,
        transport: httpx.BaseTransport | None = None,
    ):
        self.api_key = api_key
        self.timeout = timeout
        self.transport = transport

    def _get_api_key(self) -> str:
        api_key = self.api_key or os.getenv(
            "UW_API_KEY"
        )

        if not api_key:
            raise UWAPIError(
                "UW_API_KEY is not set."
            )

        return api_key

    def _get(self, path: str) -> Any:
        headers = {
            "x-api-key": self._get_api_key(),
            "Accept": "application/json",
            "User-Agent": "course-watcher-v1",
        }

        try:
            with httpx.Client(
                base_url=API_BASE_URL,
                headers=headers,
                timeout=self.timeout,
                transport=self.transport,
            ) as client:
                response = client.get(path)

        except httpx.TimeoutException as error:
            raise UWAPIError(
                "The UW API request timed out."
            ) from error

        except httpx.RequestError as error:
            raise UWAPIError(
                "Could not connect to the UW API."
            ) from error

        if response.status_code in (401, 403):
            raise UWAPIError(
                "The UW API key was rejected."
            )

        if response.status_code == 404:
            raise CourseNotFoundError(
                "The requested UW API resource was not found."
            )

        if response.status_code >= 400:
            raise UWAPIError(
                f"The UW API returned HTTP "
                f"{response.status_code}."
            )

        try:
            return response.json()
        except ValueError as error:
            raise UWAPIError(
                "The UW API returned invalid JSON."
            ) from error

    def get_current_term(self) -> str:
        data = self._get("/v3/Terms/current")

        if not isinstance(data, dict):
            raise UWAPIError(
                "The UW API returned an invalid current term."
            )

        term_code = data.get("termCode")

        if not isinstance(term_code, str):
            raise UWAPIError(
                "The UW API returned an invalid current term."
            )

        normalized_term_code = term_code.strip()

        if (
            len(normalized_term_code) != 4
            or not normalized_term_code.isdigit()
        ):
            raise UWAPIError(
                "The UW API returned an invalid current term."
            )

        return normalized_term_code

    def get_course_sections(
        self,
        term_code: str,
        subject: str,
        catalog: str,
    ) -> list[dict]:
        encoded_term = quote(term_code, safe="")
        encoded_subject = quote(subject, safe="")
        encoded_catalog = quote(catalog, safe="")

        path = (
            f"/v3/ClassSchedules/{encoded_term}/"
            f"{encoded_subject}/{encoded_catalog}"
        )

        data = self._get(path)

        if not isinstance(data, list):
            raise UWAPIError(
                "The UW API returned unexpected course data."
            )

        if not data:
            raise CourseNotFoundError(
                f"No scheduled course found for "
                f"{subject} {catalog} in term {term_code}."
            )

        if not all(
            isinstance(section, dict)
            for section in data
        ):
            raise UWAPIError(
                "The UW API returned unexpected section data."
            )

        return data


uw_client = UWClient()