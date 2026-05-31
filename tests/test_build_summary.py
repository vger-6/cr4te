import logging
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cr4te.build_issues import BuildIssue, IssueCode, IssueScope, IssueSeverity
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
                                release_date="",
                                cover="",
                                tags={},
                                facets={},
                                media_counts=MediaCounts(),
                            ),
                            ProjectSummary(
                                title="Two",
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

        self.assertEqual(clean_logs.output, ["INFO:cr4te.tests.build_summary:Build summary: creators=1, projects=2, errors=0, warnings=0"])

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


if __name__ == "__main__":
    unittest.main()
