from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from pydantic import ValidationError

from .build_issues import BuildIssue, BuildIssueError, IssueCode, IssueScope, IssueSeverity
from .library_metadata import MetadataLoadError

__all__ = [
    "BuildIssuePolicy",
    "invalid_collaboration_reference_issue",
    "issue_from_exception",
]

@dataclass
class BuildIssuePolicy:
    strict: bool
    issues: list[BuildIssue] = field(default_factory=list)

    def handle(self, issue: BuildIssue, exc: Exception | None = None) -> None:
        if self.strict and issue.severity == IssueSeverity.ERROR:
            raise BuildIssueError(issue) from exc
        self.issues.append(issue)


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
