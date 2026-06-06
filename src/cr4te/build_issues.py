from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

__all__ = [
    "BuildIssue",
    "BuildIssueError",
    "BuildIssuePolicy",
    "IssueCode",
    "IssueScope",
    "IssueSeverity",
]


class IssueScope(str, Enum):
    ASSET = "asset"
    CREATOR = "creator"
    PROJECT = "project"
    THEME = "theme"


class IssueSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"


class IssueCode(str, Enum):
    DUPLICATE_THEME = "duplicate_theme"
    INVALID_COLLABORATION_REFERENCE = "invalid_collaboration_reference"
    INVALID_JSON = "invalid_json"
    INVALID_METADATA = "invalid_metadata"
    INVALID_METADATA_SHAPE = "invalid_metadata_shape"
    INVALID_THEME = "invalid_theme"
    IO_ERROR = "io_error"
    MEDIA_INSPECTION_FAILURE = "media_inspection_failure"
    MEDIA_READ_FAILURE = "media_read_failure"
    MEDIA_STAGING_FAILURE = "media_staging_failure"
    MISSING_MEDIA = "missing_media"
    MISSING_REFERENCE = "missing_reference"
    THUMBNAIL_FAILURE = "thumbnail_failure"


@dataclass(frozen=True)
class BuildIssue:
    path: Path
    message: str
    scope: IssueScope
    code: IssueCode
    severity: IssueSeverity = IssueSeverity.ERROR


class BuildIssueError(ValueError):
    def __init__(self, issue: BuildIssue):
        self.issue = issue
        super().__init__(f"{issue.scope.value} {issue.path} [{issue.code.value}]: {issue.message}")


@dataclass
class BuildIssuePolicy:
    strict: bool
    issues: list[BuildIssue] = field(default_factory=list)
    _keys: set[tuple[IssueScope, IssueCode, str]] = field(default_factory=set, init=False)

    def handle(self, issue: BuildIssue, exc: Exception | None = None) -> None:
        if self.strict and issue.severity == IssueSeverity.ERROR:
            raise BuildIssueError(issue) from exc

        key = (issue.scope, issue.code, str(issue.path.resolve(strict=False)))
        if key in self._keys:
            return

        self._keys.add(key)
        self.issues.append(issue)
