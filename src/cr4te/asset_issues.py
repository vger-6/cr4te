from __future__ import annotations

from pathlib import Path

from .build_issues import BuildIssue, IssueCode, IssueScope, IssueSeverity

__all__ = [
    "media_inspection_failure_issue",
    "media_read_failure_issue",
    "media_staging_failure_issue",
    "missing_media_issue",
    "thumbnail_failure_issue",
]


def missing_media_issue(path: Path) -> BuildIssue:
    return BuildIssue(
        path=path,
        scope=IssueScope.ASSET,
        code=IssueCode.MISSING_MEDIA,
        message="Source media file does not exist",
    )


def thumbnail_failure_issue(path: Path, exc: Exception) -> BuildIssue:
    return BuildIssue(
        path=path,
        scope=IssueScope.ASSET,
        code=IssueCode.THUMBNAIL_FAILURE,
        message=f"Could not generate or refresh thumbnail: {exc}",
    )


def media_read_failure_issue(path: Path, exc: Exception) -> BuildIssue:
    return BuildIssue(
        path=path,
        scope=IssueScope.ASSET,
        code=IssueCode.MEDIA_READ_FAILURE,
        message=f"Could not read media file: {exc}",
    )


def media_inspection_failure_issue(path: Path, exc: Exception) -> BuildIssue:
    return BuildIssue(
        path=path,
        scope=IssueScope.ASSET,
        code=IssueCode.MEDIA_INSPECTION_FAILURE,
        severity=IssueSeverity.WARNING,
        message=f"Could not inspect media file: {exc}",
    )


def media_staging_failure_issue(path: Path, message: str) -> BuildIssue:
    return BuildIssue(
        path=path,
        scope=IssueScope.ASSET,
        code=IssueCode.MEDIA_STAGING_FAILURE,
        message=message,
    )
