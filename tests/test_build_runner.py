import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cr4te.build_issues import BuildIssue, IssueCode, IssueScope
from cr4te.build_runner import BuildPhase, BuildPhaseError, BuildRequest, run_build
from cr4te.config_manager import apply_cli_overrides, load_config
from cr4te.enums.domain import Domain
from cr4te.html_builder import HtmlBuildResult
from cr4te.library_index import LibraryIndex
from cr4te.metadata_manager import MetadataWriteResult
from cr4te.themes import ThemeRegistry, discover_builtin_themes


class BuildRunnerTests(unittest.TestCase):
    def request_for(self, root: Path, output_dir: Path) -> BuildRequest:
        return BuildRequest(
            input_dir=root,
            output_dir=output_dir,
            config=apply_cli_overrides(load_config(), domain=Domain.ART),
        )

    def test_runner_combines_and_deduplicates_phase_issues(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "Artists"
            output_dir = Path(tmp) / "site"
            root.mkdir()
            issue = BuildIssue(
                path=root / "Noomi",
                scope=IssueScope.CREATOR,
                code=IssueCode.INVALID_METADATA,
                message="invalid metadata",
            )
            metadata_result = MetadataWriteResult(issues=[issue])
            index = LibraryIndex(input_dir=root, creators=(), issues=(issue,))
            html_result = HtmlBuildResult(output_dir / "index.html")

            with (
                patch("cr4te.build_runner.discover_themes", return_value=ThemeRegistry(discover_builtin_themes())),
                patch("cr4te.build_runner.reconcile_metadata_files", return_value=metadata_result),
                patch("cr4te.build_runner.build_library_index", return_value=index),
                patch("cr4te.build_runner.build_html_pages_streaming", return_value=html_result),
                patch("cr4te.build_runner.perf_counter", side_effect=range(10)),
            ):
                result = run_build(self.request_for(root, output_dir))

            self.assertEqual(result.summary.issues, (issue,))
            self.assertEqual(result.summary.timings.total_seconds, 5)
            self.assertIs(result.metadata_result, metadata_result)

    def test_runner_adds_phase_context_to_expected_operational_failures(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "Artists"
            root.mkdir()

            with (
                patch("cr4te.build_runner.discover_themes", side_effect=OSError("unreadable themes")),
                self.assertRaises(BuildPhaseError) as caught,
            ):
                run_build(self.request_for(root, Path(tmp) / "site"))

            self.assertEqual(caught.exception.phase, BuildPhase.THEME_DISCOVERY)
            self.assertIn("unreadable themes", str(caught.exception))

    def test_runner_does_not_hide_unexpected_programming_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "Artists"
            root.mkdir()

            with (
                patch("cr4te.build_runner.discover_themes", side_effect=RuntimeError("bug")),
                self.assertRaisesRegex(RuntimeError, "bug"),
            ):
                run_build(self.request_for(root, Path(tmp) / "site"))


if __name__ == "__main__":
    unittest.main()
