# app/errors.py


class CourseWatcherError(Exception):
    """Base class for expected Course Watcher errors."""


class WatchNotFoundError(CourseWatcherError):
    """Raised when a requested Watch does not exist."""


class DuplicateWatchError(CourseWatcherError):
    """Raised when an identical Watch already exists."""


class CourseNotFoundError(CourseWatcherError):
    """Raised when UW has no scheduled course for the request."""


class NoMatchingSectionsError(CourseWatcherError):
    """Raised when no section matches the Watch component."""


class UWAPIError(CourseWatcherError):
    """Raised when the UW API cannot provide valid data."""


class ParseInputError(CourseWatcherError):
    """Raised when text cannot safely identify one course."""


class ModelServiceError(CourseWatcherError):
    """Raised when OpenAI cannot complete a parse request."""


class ModelResponseInvalidError(CourseWatcherError):
    """Raised for one absent, refused, or invalid model response."""


class ModelOutputError(CourseWatcherError):
    """Raised after both model responses are invalid."""


class ConfigurationError(CourseWatcherError):
    """Raised when parse configuration is missing."""
