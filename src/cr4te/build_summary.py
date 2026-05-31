from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from .build_issues import BuildIssue, IssueSeverity
from .library_index import LibraryIndex

__all__ = [
    "BuildSummary",
    "log_build_summary",
]


@dataclass(frozen=True)
class BuildSummary:
    input_dir: Path
    creator_count: int
    project_count: int
    issues: tuple[BuildIssue, ...] = ()

    @classmethod
    def from_library_index(cls, index: LibraryIndex) -> "BuildSummary":
        return cls(
            input_dir=index.input_dir,
            creator_count=len(index.creators),
            project_count=index.project_count,
            issues=index.issues,
        )

    @property
    def issue_count(self) -> int:
        return len(self.issues)

    @property
    def error_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == IssueSeverity.ERROR)

    @property
    def warning_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == IssueSeverity.WARNING)

    def headline(self) -> str:
        return (
            "Build summary: "
            f"creators={self.creator_count}, "
            f"projects={self.project_count}, "
            f"errors={self.error_count}, "
            f"warnings={self.warning_count}"
        )

    def issue_lines(self) -> tuple[str, ...]:
        return tuple(
            f"{issue.severity.value.upper()} {issue.scope.value} {self._display_path(issue.path)} [{issue.code.value}]: {issue.message}"
            for issue in self.issues
        )

    def lines(self) -> tuple[str, ...]:
        return (self.headline(), *self.issue_lines())

    def _display_path(self, path: Path) -> str:
        resolved_input_dir = self.input_dir.resolve()
        resolved_path = path.resolve()
        if resolved_path.is_relative_to(resolved_input_dir):
            return resolved_path.relative_to(resolved_input_dir).as_posix()
        return str(path)


def log_build_summary(summary: BuildSummary, logger: logging.Logger | None = None) -> None:
    logger = logger or logging.getLogger(__name__)
    if summary.issue_count:
        logger.warning(summary.headline())
        for line in summary.issue_lines():
            logger.warning(line)
        return

    logger.info(summary.headline())
