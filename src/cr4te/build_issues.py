from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

__all__ = [
    "BuildIssue",
    "BuildIssueError",
    "IssueCode",
    "IssueScope",
    "IssueSeverity",
]


class IssueScope(str, Enum):
    CREATOR = "creator"
    PROJECT = "project"


class IssueSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"


class IssueCode(str, Enum):
    DUPLICATE_CREATOR = "duplicate_creator"
    INVALID_COLLABORATION_REFERENCE = "invalid_collaboration_reference"
    INVALID_JSON = "invalid_json"
    INVALID_METADATA = "invalid_metadata"
    INVALID_METADATA_SHAPE = "invalid_metadata_shape"
    IO_ERROR = "io_error"
    MISSING_REFERENCE = "missing_reference"


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
