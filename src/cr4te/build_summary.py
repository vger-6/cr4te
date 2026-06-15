from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from .build_issues import BuildIssue, IssueSeverity, deduplicate_issues
from .build_metrics import AssetStatistics, BuildTimings
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
    timings: BuildTimings = field(default_factory=BuildTimings)
    asset_statistics: AssetStatistics = field(default_factory=AssetStatistics)

    @classmethod
    def from_library_index(
        cls,
        index: LibraryIndex,
        additional_issues: tuple[BuildIssue, ...] = (),
        timings: BuildTimings | None = None,
        asset_statistics: AssetStatistics | None = None,
    ) -> "BuildSummary":
        return cls(
            input_dir=index.input_dir,
            creator_count=len(index.creators),
            project_count=index.project_count,
            issues=deduplicate_issues((*index.issues, *additional_issues)),
            timings=timings or BuildTimings(),
            asset_statistics=asset_statistics or AssetStatistics(),
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

    def timing_line(self) -> str:
        timings = self.timings
        return (
            "Build timings: "
            f"themes={timings.theme_discovery_seconds:.3f}s, "
            f"output={timings.output_preparation_seconds:.3f}s, "
            f"metadata={timings.metadata_reconciliation_seconds:.3f}s, "
            f"indexing={timings.library_indexing_seconds:.3f}s, "
            f"rendering={timings.html_rendering_seconds:.3f}s, "
            f"total={timings.total_seconds:.3f}s"
        )

    def asset_statistic_lines(self) -> tuple[str, str]:
        stats = self.asset_statistics
        return (
            (
                "Asset links: "
                f"symbolic={stats.symbolic_links_created}, "
                f"hard={stats.hard_links_created}, "
                f"reused={stats.media_links_reused}"
            ),
            (
                "Source thumbnails: "
                f"generated={stats.source_thumbnails_generated}, "
                f"reused={stats.source_thumbnails_reused}, "
                f"default_uses={stats.default_thumbnail_uses}, "
                f"hash_checks={stats.source_hash_checks}"
            ),
        )

    def lines(self) -> tuple[str, ...]:
        return (self.headline(), self.timing_line(), *self.asset_statistic_lines(), *self.issue_lines())

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
        logger.info(summary.timing_line())
        for line in summary.asset_statistic_lines():
            logger.info(line)
        for line in summary.issue_lines():
            logger.warning(line)
        return

    for line in summary.lines():
        logger.info(line)
