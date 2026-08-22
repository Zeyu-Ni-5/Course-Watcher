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