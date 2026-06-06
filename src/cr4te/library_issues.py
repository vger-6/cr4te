from __future__ import annotations

from pathlib import Path

from pydantic import ValidationError

from .build_issues import BuildIssue, IssueCode, IssueScope, IssueSeverity
from .library_metadata import MetadataLoadError

__all__ = [
    "invalid_collaboration_reference_issue",
    "issue_from_exception",
]


def issue_from_exception(path: Path, scope: IssueScope, exc: Exception) -> BuildIssue:
    if isinstance(exc, MetadataLoadError):
        return BuildIssue(
            path=path,
            scope=scope,
            code=exc.issue_code,
            message=str(exc),
        )

    if isinstance(exc, ValidationError):
        return BuildIssue(
            path=path,
            scope=scope,
            code=IssueCode.INVALID_METADATA,
            message=str(exc),
        )

    if isinstance(exc, OSError):
        return BuildIssue(
            path=path,
            scope=scope,
            code=IssueCode.IO_ERROR,
            message=str(exc),
        )

    return BuildIssue(
        path=path,
        scope=scope,
        code=IssueCode.INVALID_METADATA,
        message=str(exc),
    )


def invalid_collaboration_reference_issue(path: Path, invalid_references: list[str]) -> BuildIssue:
    return BuildIssue(
        path=path,
        scope=IssueScope.CREATOR,
        code=IssueCode.INVALID_COLLABORATION_REFERENCE,
        severity=IssueSeverity.WARNING,
        message=f"Ignoring unknown collaboration references: {invalid_references}",
    )
