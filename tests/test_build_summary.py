import logging
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cr4te.build_issues import BuildIssue, IssueCode, IssueScope, IssueSeverity
from cr4te.build_metrics import AssetStatistics, BuildTimings
from cr4te.build_summary import BuildSummary, log_build_summary
from cr4te.enums.creator_type import CreatorType
from cr4te.library_index import CreatorSummary, LibraryIndex, ProjectSummary
from cr4te.media_counts import MediaCounts


class BuildSummaryTests(unittest.TestCase):
    def test_summary_counts_creators_projects_and_relative_issue_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "Artists"
            issue = BuildIssue(
                path=root / "Noomi" / "Bad Project",
                scope=IssueScope.PROJECT,
                code=IssueCode.INVALID_METADATA,
                message="broken metadata",
            )
            index = LibraryIndex(
                input_dir=root,
                creators=(
                    CreatorSummary(
                        path=root / "Noomi",
                        name="Noomi",
                        display_name="Displayed Noomi",
                        type=CreatorType.PERSON,
                        portrait="",
                        aliases=(),
                        collaborations=(),
                        tags={},
                        active_since="",
                        nationalities=(),
                        info="",
                        projects=(
                            ProjectSummary(
                                title="One",
                                display_title="One",
                                release_date="",
                                cover="",
                                tags={},
                                facets={},
                                media_counts=MediaCounts(),
                            ),
                            ProjectSummary(
                                title="Two",
                                display_title="Two",
                                release_date="",
                                cover="",
                                tags={},
                                facets={},
                                media_counts=MediaCounts(),
                            ),
                        ),
                    ),
                    CreatorSummary(
                        path=root / "Ada",
                        name="Ada",
                        display_name="Ada",
                        type=CreatorType.PERSON,
                        portrait="",
                        aliases=(),
                        collaborations=(),
                        tags={},
                        active_since="",
                        nationalities=(),
                        info="",
                    ),
                ),
                issues=(issue,),
            )

            summary = BuildSummary.from_library_index(index)

            self.assertEqual(summary.creator_count, 2)
            self.assertEqual(summary.project_count, 2)
            self.assertEqual(summary.issue_count, 1)
            self.assertEqual(summary.error_count, 1)
            self.assertEqual(summary.warning_count, 0)
            self.assertEqual(summary.headline(), "Build summary: creators=2, projects=2, errors=1, warnings=0")
            self.assertEqual(summary.issue_lines(), ("ERROR project Noomi/Bad Project [invalid_metadata]: broken metadata",))
            self.assertEqual(summary.lines()[0], summary.headline())

    def test_log_build_summary_uses_warning_only_when_issues_exist(self):
        logger = logging.getLogger("cr4te.tests.build_summary")
        clean_summary = BuildSummary(input_dir=Path("."), creator_count=1, project_count=2)
        dirty_summary = BuildSummary(
            input_dir=Path("."),
            creator_count=1,
            project_count=1,
            issues=(
                BuildIssue(
                    path=Path("Bad"),
                    scope=IssueScope.CREATOR,
                    code=IssueCode.INVALID_METADATA,
                    message="bad data",
                    severity=IssueSeverity.ERROR,
                ),
            ),
        )

        with self.assertLogs(logger, level="INFO") as clean_logs:
            log_build_summary(clean_summary, logger)

        self.assertEqual(
            clean_logs.output,
            [
                "INFO:cr4te.tests.build_summary:Build summary: creators=1, projects=2, errors=0, warnings=0",
                (
                    "INFO:cr4te.tests.build_summary:Build timings: themes=0.000s, output=0.000s, "
                    "metadata=0.000s, indexing=0.000s, rendering=0.000s, total=0.000s"
                ),
                "INFO:cr4te.tests.build_summary:Asset links: symbolic=0, hard=0, reused=0",
                (
                    "INFO:cr4te.tests.build_summary:Source thumbnails: "
                    "generated=0, reused=0, default_uses=0, freshness_checks=0"
                ),
            ],
        )

        with self.assertLogs(logger, level="WARNING") as dirty_logs:
            log_build_summary(dirty_summary, logger)

        self.assertEqual(dirty_logs.output[0], "WARNING:cr4te.tests.build_summary:Build summary: creators=1, projects=1, errors=1, warnings=0")
        self.assertIn("ERROR creator Bad [invalid_metadata]: bad data", dirty_logs.output[1])

    def test_summary_can_be_built_from_lightweight_index(self):
        index = LibraryIndex(
            input_dir=Path("."),
            creators=(
                CreatorSummary(
                    path=Path("Noomi"),
                    name="Noomi",
                    display_name="Displayed Noomi",
                    type=CreatorType.PERSON,
                    portrait="",
                    aliases=(),
                    collaborations=(),
                    tags={},
                    active_since="",
                    nationalities=(),
                    info="",
                    projects=(
                        ProjectSummary(
                            title="Landscapes",
                            display_title="Displayed Landscapes",
                            release_date="",
                            cover="",
                            tags={},
                            facets={},
                            media_counts=MediaCounts(),
                        ),
                    ),
                ),
            ),
        )

        summary = BuildSummary.from_library_index(index)

        self.assertEqual(summary.creator_count, 1)
        self.assertEqual(summary.project_count, 1)
        self.assertEqual(summary.headline(), "Build summary: creators=1, projects=1, errors=0, warnings=0")

    def test_summary_reports_timings_and_asset_statistics(self):
        summary = BuildSummary(
            input_dir=Path("."),
            creator_count=1,
            project_count=2,
            timings=BuildTimings(
                theme_discovery_seconds=0.1,
                output_preparation_seconds=0.2,
                metadata_reconciliation_seconds=0.3,
                library_indexing_seconds=0.4,
                html_rendering_seconds=0.5,
            ),
            asset_statistics=AssetStatistics(
                symbolic_links_created=1,
                hard_links_created=2,
                media_links_reused=3,
                source_thumbnails_generated=4,
                source_thumbnails_reused=5,
                default_thumbnail_uses=6,
                source_freshness_checks=7,
            ),
        )

        self.assertEqual(
            summary.timing_line(),
            "Build timings: themes=0.100s, output=0.200s, metadata=0.300s, indexing=0.400s, rendering=0.500s, total=1.500s",
        )
        self.assertEqual(
            summary.asset_statistic_lines(),
            (
                "Asset links: symbolic=1, hard=2, reused=3",
                "Source thumbnails: generated=4, reused=5, default_uses=6, freshness_checks=7",
            ),
        )
        self.assertEqual(summary.lines()[1:], (summary.timing_line(), *summary.asset_statistic_lines()))

    def test_summary_combines_explicit_non_library_issues(self):
        index = LibraryIndex(input_dir=Path("Artists"), creators=())
        theme_issue = BuildIssue(
            path=Path("themes") / "invalid.css",
            scope=IssueScope.THEME,
            code=IssueCode.INVALID_THEME,
            message="Invalid theme",
        )

        summary = BuildSummary.from_library_index(index, additional_issues=(theme_issue,))

        self.assertEqual(summary.issues, (theme_issue,))
        self.assertIn("ERROR theme", summary.issue_lines()[0])
        self.assertIn(str(Path("themes") / "invalid.css"), summary.issue_lines()[0])
        self.assertIn("[invalid_theme]", summary.issue_lines()[0])

    def test_summary_deduplicates_issues_from_separate_build_phases(self):
        issue = BuildIssue(
            path=Path("Artists") / "Noomi",
            scope=IssueScope.CREATOR,
            code=IssueCode.INVALID_METADATA,
            message="invalid metadata",
        )
        index = LibraryIndex(input_dir=Path("Artists"), creators=(), issues=(issue,))

        summary = BuildSummary.from_library_index(index, additional_issues=(issue,))

        self.assertEqual(summary.issues, (issue,))


if __name__ == "__main__":
    unittest.main()
