import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cr4te.build_issues import BuildIssue, BuildIssueError, BuildIssuePolicy, IssueCode, IssueScope
from cr4te.library_issues import (
    invalid_collaboration_reference_issue,
    issue_from_exception,
)
from cr4te.library_metadata import MetadataValidationError


class LibraryIssuesTests(unittest.TestCase):
    def test_strict_policy_raises_on_errors(self):
        issue = BuildIssue(
            path=Path("Ada"),
            scope=IssueScope.CREATOR,
            code=IssueCode.INVALID_METADATA,
            message="Invalid",
        )
        policy = BuildIssuePolicy(strict=True)

        with self.assertRaises(BuildIssueError) as caught:
            policy.handle(issue, ValueError("cause"))

        self.assertEqual(caught.exception.issue, issue)
        self.assertEqual(policy.issues, [])

    def test_non_strict_policy_collects_errors(self):
        issue = BuildIssue(
            path=Path("Ada"),
            scope=IssueScope.CREATOR,
            code=IssueCode.INVALID_METADATA,
            message="Invalid",
        )
        policy = BuildIssuePolicy(strict=False)

        policy.handle(issue)

        self.assertEqual(policy.issues, [issue])

    def test_non_strict_policy_deduplicates_scope_code_and_path(self):
        issue = BuildIssue(
            path=Path("Ada"),
            scope=IssueScope.ASSET,
            code=IssueCode.MISSING_MEDIA,
            message="Missing",
        )
        policy = BuildIssuePolicy(strict=False)

        policy.handle(issue)
        policy.handle(issue)

        self.assertEqual(policy.issues, [issue])

    def test_issue_from_metadata_exception_preserves_code(self):
        issue = issue_from_exception(
            Path("Ada"),
            IssueScope.CREATOR,
            MetadataValidationError("invalid metadata"),
        )

        self.assertEqual(issue.code, IssueCode.INVALID_METADATA)
        self.assertEqual(issue.scope, IssueScope.CREATOR)

    def test_invalid_collaboration_reference_is_warning(self):
        issue = invalid_collaboration_reference_issue(Path("Ada"), ["Missing Band"])

        self.assertEqual(issue.code, IssueCode.INVALID_COLLABORATION_REFERENCE)
        self.assertEqual(issue.message, "Ignoring unknown collaboration references: ['Missing Band']")


if __name__ == "__main__":
    unittest.main()
