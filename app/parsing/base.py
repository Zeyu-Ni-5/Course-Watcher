from collections.abc import Mapping
from typing import Protocol


class CourseRequestParser(Protocol):
    def parse(
        self,
        text: str,
        *,
        feedback: str | None = None,
    ) -> Mapping[str, object]:
        ...
