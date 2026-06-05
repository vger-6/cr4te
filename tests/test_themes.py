import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cr4te.build_issues import BuildIssueError, IssueCode, IssueScope
from cr4te.themes import DEFAULT_THEME_ID, discover_builtin_themes, discover_themes


def write_theme(themes_dir: Path, filename: str, selector: str | None = None) -> Path:
    path = themes_dir / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    expected_selector = selector or f".theme-{path.stem}"
    path.write_text(f"{expected_selector} {{ --theme-page-bg: #101014; }}", encoding="utf-8")
    return path


class ThemeTests(unittest.TestCase):
    def test_builtin_registry_uses_self_contained_theme_files_and_explicit_default(self):
        themes = discover_builtin_themes()

        self.assertEqual(
            {theme.id for theme in themes},
            {"forest-night", "frozen-aurora", "mono-terminal"},
        )
        self.assertTrue(all(theme.is_builtin for theme in themes))
        self.assertTrue(all(theme.css_class in theme.source_path.read_text(encoding="utf-8") for theme in themes))
        self.assertEqual(discover_themes(None).default_theme.id, DEFAULT_THEME_ID)

    def test_example_library_provides_amber_terminal_as_custom_theme(self):
        themes_dir = ROOT / "data" / "example" / "themes"
        registry = discover_themes(themes_dir)
        amber = next(theme for theme in registry.themes if theme.id == "amber-terminal")

        self.assertFalse(amber.is_builtin)
        self.assertEqual(amber.source_path, themes_dir / "amber-terminal.css")

    def test_custom_theme_is_discovered_from_explicit_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            themes_dir = Path(tmp) / "themes"
            custom_path = write_theme(themes_dir, "midnight-green.css")

            registry = discover_themes(themes_dir)
            custom = next(theme for theme in registry.themes if theme.id == "midnight-green")

            self.assertEqual(custom.display_name, "Midnight Green")
            self.assertEqual(custom.css_class, "theme-midnight-green")
            self.assertEqual(custom.source_path, custom_path)
            self.assertFalse(custom.is_builtin)
            self.assertEqual(registry.issues, ())

    def test_duplicate_custom_theme_is_reported_and_builtin_wins(self):
        with tempfile.TemporaryDirectory() as tmp:
            themes_dir = Path(tmp) / "themes"
            duplicate_path = write_theme(themes_dir, "frozen-aurora.css")

            registry = discover_themes(themes_dir)
            frozen = [theme for theme in registry.themes if theme.id == "frozen-aurora"]

            self.assertEqual(len(frozen), 1)
            self.assertTrue(frozen[0].is_builtin)
            self.assertEqual(len(registry.issues), 1)
            self.assertEqual(registry.issues[0].path, duplicate_path)
            self.assertEqual(registry.issues[0].scope, IssueScope.THEME)
            self.assertEqual(registry.issues[0].code, IssueCode.DUPLICATE_THEME)

    def test_invalid_custom_themes_are_reported_and_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            themes_dir = Path(tmp) / "themes"
            invalid_name = write_theme(themes_dir, "Bad Name.css", ".theme-bad-name")
            invalid_selector = write_theme(themes_dir, "valid-name.css", ".theme-other-name")
            non_css = write_theme(themes_dir, "notes.txt", ".theme-notes")

            registry = discover_themes(themes_dir)

            self.assertNotIn("valid-name", {theme.id for theme in registry.themes})
            self.assertEqual(
                {issue.path for issue in registry.issues},
                {invalid_name, invalid_selector, non_css},
            )
            self.assertTrue(all(issue.scope == IssueScope.THEME for issue in registry.issues))
            self.assertTrue(all(issue.code == IssueCode.INVALID_THEME for issue in registry.issues))

    def test_invalid_custom_theme_raises_in_strict_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            themes_dir = Path(tmp) / "themes"
            invalid_path = write_theme(themes_dir, "invalid.css", ".theme-other")

            with self.assertRaises(BuildIssueError) as caught:
                discover_themes(themes_dir, strict=True)

            self.assertEqual(caught.exception.issue.path, invalid_path)
            self.assertEqual(caught.exception.issue.code, IssueCode.INVALID_THEME)

    def test_missing_custom_theme_directory_always_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            themes_dir = Path(tmp) / "missing"

            with self.assertRaises(BuildIssueError) as caught:
                discover_themes(themes_dir)

            self.assertEqual(caught.exception.issue.path, themes_dir)
            self.assertEqual(caught.exception.issue.code, IssueCode.MISSING_REFERENCE)

    def test_custom_theme_path_must_be_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            themes_path = Path(tmp) / "themes.css"
            themes_path.write_text(".theme-custom {}", encoding="utf-8")

            with self.assertRaises(BuildIssueError) as caught:
                discover_themes(themes_path)

            self.assertEqual(caught.exception.issue.path, themes_path)
            self.assertEqual(caught.exception.issue.code, IssueCode.INVALID_THEME)


if __name__ == "__main__":
    unittest.main()
