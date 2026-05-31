import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cr4te.html_paths import HTML_PATH_TO_ROOT, build_rel_creator_html_path, build_rel_project_html_path
from cr4te.utils import path_utils


class HtmlPathTests(unittest.TestCase):
    def test_creator_path_is_stable_and_sanitized(self):
        creator = SimpleNamespace(name="Ada Lovelace")

        self.assertEqual(
            build_rel_creator_html_path(creator),
            path_utils.build_unique_path(Path("creator", "Ada Lovelace").with_suffix(".html"), 4),
        )

    def test_project_path_includes_creator_namespace(self):
        creator = SimpleNamespace(name="Ada")
        project = SimpleNamespace(title="First Notes")

        self.assertEqual(
            build_rel_project_html_path(creator, project),
            path_utils.build_unique_path(Path("project", "Ada", "First Notes").with_suffix(".html"), 4),
        )

    def test_path_to_root_matches_html_depth(self):
        self.assertEqual(HTML_PATH_TO_ROOT, "../../../../../")


if __name__ == "__main__":
    unittest.main()
