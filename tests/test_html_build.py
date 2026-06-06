import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from PIL import Image

from cr4te.config_manager import apply_cli_overrides, load_config
from cr4te.build_issues import BuildIssue, BuildIssueError, IssueCode, IssueScope
from cr4te.cr4te import _build_cmd_handler, _file_uri
from cr4te.enums.creator_type import CreatorType
from cr4te.enums.domain import Domain
from cr4te.html_builder import HtmlBuildResult, build_html_pages_streaming
from cr4te.library_builder import build_library_index, load_indexed_creator
from cr4te.library_index import CreatorSummary, LibraryIndex, ProjectSummary
from cr4te.media_counts import MediaCounts
from cr4te.schemas.library_schema import Creator, Project
from cr4te.themes import discover_themes


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def write_image(path: Path, size: tuple[int, int] = (120, 90)) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color=(120, 80, 160)).save(path)


class HtmlBuildTests(unittest.TestCase):
    def test_file_uri_uses_resolved_path_uri(self):
        with tempfile.TemporaryDirectory() as tmp:
            index_html = Path(tmp) / "site" / "index.html"

            self.assertEqual(_file_uri(index_html), index_html.resolve().as_uri())

    def test_build_command_reconciles_metadata_before_rendering(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "Artists"
            output_dir = Path(tmp) / "site"
            creator_dir = root / "Noomi"
            project_dir = creator_dir / "Landscapes"
            write_image(creator_dir / "portrait.jpg", (80, 160))
            write_image(project_dir / "cover.jpg")
            write_json(creator_dir / "cr4te.json", {"display_name": "Displayed Creator"})
            write_json(project_dir / "cr4te.json", {"display_title": "Displayed Project"})

            _build_cmd_handler(SimpleNamespace(
                config=None,
                input=str(root),
                output=str(output_dir),
                domain=Domain.ART.value,
                image_sample_strategy=None,
                portrait_strategy=None,
                open=False,
                force=True,
                clean=False,
                strict=True,
            ))

            metadata = json.loads((creator_dir / "cr4te.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["display_name"], "Displayed Creator")
            self.assertNotIn("info", metadata)
            self.assertNotIn("projects", metadata)
            project_metadata = json.loads((project_dir / "cr4te.json").read_text(encoding="utf-8"))
            self.assertEqual(project_metadata["display_title"], "Displayed Project")
            self.assertEqual(project_metadata["cover"], "")
            self.assertNotIn("info", project_metadata)
            self.assertTrue((output_dir / "index.html").exists())
            rendered_html = "\n".join(
                path.read_text(encoding="utf-8")
                for path in output_dir.rglob("*.html")
            )
            self.assertIn("Displayed Creator", rendered_html)
            self.assertIn("Displayed Project", rendered_html)

    def test_build_command_sorts_overviews_by_display_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "Artists"
            output_dir = Path(tmp) / "site"
            (root / "A Folder" / "A Project").mkdir(parents=True)
            (root / "Z Folder" / "Z Project").mkdir(parents=True)
            write_json(root / "A Folder" / "cr4te.json", {"display_name": "Z Display"})
            write_json(root / "A Folder" / "A Project" / "cr4te.json", {"display_title": "Z Project"})
            write_json(root / "Z Folder" / "cr4te.json", {"display_name": "A Display"})
            write_json(root / "Z Folder" / "Z Project" / "cr4te.json", {"display_title": "A Project"})

            _build_cmd_handler(SimpleNamespace(
                config=None,
                input=str(root),
                output=str(output_dir),
                domain=Domain.ART.value,
                image_sample_strategy=None,
                portrait_strategy=None,
                open=False,
                force=True,
                clean=False,
                strict=True,
            ))

            creator_overview = (output_dir / "index.html").read_text(encoding="utf-8")
            project_overview = (output_dir / "projects.html").read_text(encoding="utf-8")
            self.assertLess(creator_overview.index("A Display"), creator_overview.index("Z Display"))
            self.assertLess(project_overview.index("A Project"), project_overview.index("Z Project"))

    def test_build_command_aborts_when_media_cannot_be_linked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "Artists"
            output_dir = Path(tmp) / "site"
            project_dir = root / "Noomi" / "Landscapes"
            project_dir.mkdir(parents=True)
            (project_dir / "catalog.pdf").write_bytes(b"pdf")

            args = SimpleNamespace(
                config=None,
                input=str(root),
                output=str(output_dir),
                domain=Domain.ART.value,
                image_sample_strategy=None,
                portrait_strategy=None,
                open=False,
                force=True,
                clean=False,
                strict=True,
            )

            with (
                patch("cr4te.render_assets.os.symlink", side_effect=OSError("no symlink")),
                patch("cr4te.render_assets.os.link", side_effect=OSError("no hardlink")),
                self.assertLogs(level="ERROR") as logs,
            ):
                with self.assertRaises(SystemExit) as exit_context:
                    _build_cmd_handler(args)

            self.assertEqual(exit_context.exception.code, 1)
            self.assertIn("will not copy media files automatically", "\n".join(logs.output))

    def test_build_command_combines_theme_issues_into_final_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "Artists"
            output_dir = Path(tmp) / "site"
            themes_dir = Path(tmp) / "themes"
            invalid_theme = themes_dir / "invalid.css"
            root.mkdir()
            invalid_theme.parent.mkdir(parents=True)
            invalid_theme.write_text(".theme-other {}", encoding="utf-8")

            args = SimpleNamespace(
                config=None,
                input=str(root),
                output=str(output_dir),
                domain=Domain.ART.value,
                image_sample_strategy=None,
                portrait_strategy=None,
                open=False,
                force=True,
                clean=False,
                strict=False,
                themes_dir=str(themes_dir),
            )

            with patch("cr4te.cr4te.log_build_summary") as log_build_summary:
                _build_cmd_handler(args)

            summary = log_build_summary.call_args.args[0]
            self.assertEqual(len(summary.issues), 1)
            self.assertEqual(summary.issues[0].scope, IssueScope.THEME)
            self.assertEqual(summary.issues[0].path, invalid_theme)

    def test_build_command_combines_render_asset_issues_into_final_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "Artists"
            output_dir = Path(tmp) / "site"
            missing_media = root / "Noomi" / "missing.jpg"
            root.mkdir()
            issue = BuildIssue(
                path=missing_media,
                scope=IssueScope.ASSET,
                code=IssueCode.MISSING_MEDIA,
                message="Source media file does not exist",
            )
            args = SimpleNamespace(
                config=None,
                input=str(root),
                output=str(output_dir),
                domain=Domain.ART.value,
                image_sample_strategy=None,
                portrait_strategy=None,
                open=False,
                force=True,
                clean=False,
                strict=False,
                themes_dir=None,
            )

            with (
                patch(
                    "cr4te.cr4te.build_html_pages_streaming",
                    return_value=HtmlBuildResult(output_dir / "index.html", (issue,)),
                ),
                patch("cr4te.cr4te.log_build_summary") as log_build_summary,
            ):
                _build_cmd_handler(args)

            summary = log_build_summary.call_args.args[0]
            self.assertEqual(summary.issues, (issue,))

    def test_build_command_aborts_before_side_effects_for_missing_themes_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "Artists"
            output_dir = Path(tmp) / "site"
            missing_themes_dir = Path(tmp) / "missing-themes"
            root.mkdir()

            args = SimpleNamespace(
                config=None,
                input=str(root),
                output=str(output_dir),
                domain=Domain.ART.value,
                image_sample_strategy=None,
                portrait_strategy=None,
                open=False,
                force=True,
                clean=False,
                strict=False,
                themes_dir=str(missing_themes_dir),
            )

            with self.assertRaises(BuildIssueError) as caught:
                _build_cmd_handler(args)

            self.assertEqual(caught.exception.issue.path, missing_themes_dir.resolve())
            self.assertEqual(caught.exception.issue.code, IssueCode.MISSING_REFERENCE)
            self.assertFalse(output_dir.exists())

    def test_build_command_uses_configured_project_facets_without_domain_arg(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "Musicians"
            output_dir = Path(tmp) / "site"
            creator_dir = root / "Noomi"
            project_dir = creator_dir / "Album"
            config_path = Path(tmp) / "music_config.json"
            write_image(project_dir / "cover.jpg")
            write_json(config_path, apply_cli_overrides(load_config(), domain=Domain.MUSIC).model_dump(mode="json"))

            _build_cmd_handler(SimpleNamespace(
                config=str(config_path),
                input=str(root),
                output=str(output_dir),
                domain=None,
                image_sample_strategy=None,
                portrait_strategy=None,
                open=False,
                force=True,
                clean=False,
                strict=True,
            ))

            project_metadata = json.loads((project_dir / "cr4te.json").read_text(encoding="utf-8"))
            facets = project_metadata["facets"]
            self.assertEqual(
                list(facets),
                ["studios", "cover_artists", "genres", "producers", "composers", "musicians", "labels", "instruments"],
            )
            self.assertTrue(all(value == [] for value in facets.values()))
            self.assertTrue((output_dir / "index.html").exists())

    def test_build_domain_override_replaces_configured_project_facets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "Musicians"
            output_dir = Path(tmp) / "site"
            creator_dir = root / "Noomi"
            project_dir = creator_dir / "Album"
            config_path = Path(tmp) / "music_config.json"
            write_image(project_dir / "cover.jpg")
            write_json(config_path, apply_cli_overrides(load_config(), domain=Domain.MUSIC).model_dump(mode="json"))
            write_json(creator_dir / "cr4te.json", {})
            write_json(
                project_dir / "cr4te.json",
                {
                    "facets": {
                        "genres": ["Ambient"],
                        "labels": [],
                        "studios": [],
                    },
                },
            )

            _build_cmd_handler(SimpleNamespace(
                config=str(config_path),
                input=str(root),
                output=str(output_dir),
                domain=Domain.ART.value,
                image_sample_strategy=None,
                portrait_strategy=None,
                open=False,
                force=True,
                clean=False,
                strict=True,
            ))

            project_metadata = json.loads((project_dir / "cr4te.json").read_text(encoding="utf-8"))
            facets = project_metadata["facets"]
            self.assertEqual(set(facets), {"genres", "mediums", "materials", "exhibitions", "periods"})
            self.assertEqual(facets["genres"], ["Ambient"])
            self.assertEqual(facets["mediums"], [])
            self.assertNotIn("labels", facets)
            self.assertNotIn("studios", facets)

    def test_page_build_logs_happen_before_page_context_assembly(self):
        events = []
        project_summary = ProjectSummary(
            title="Landscapes",
            display_title="Displayed Landscapes",
            release_date="",
            cover="",
            tags={},
            facets={},
            media_counts=MediaCounts(),
        )
        index = LibraryIndex(
            input_dir=Path("input"),
            creators=(
                CreatorSummary(
                    path=Path("input") / "Noomi",
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
                    projects=(project_summary,),
                ),
            ),
        )
        creator = Creator(
            name="Noomi",
            display_name="Displayed Noomi",
            type=CreatorType.PERSON,
            active_since="",
            portrait="",
            info="",
            media_groups=[],
            projects=[
                Project(
                    title="Landscapes",
                    display_title="Displayed Landscapes",
                    release_date="",
                    cover="",
                    info="",
                    tags={},
                    facets={},
                    media_groups=[],
                )
            ],
        )
        config = apply_cli_overrides(load_config(), domain=Domain.ART)

        def creator_context(*args):
            events.append("creator-context")
            return object()

        def project_context(*args):
            events.append("project-context")
            return object()

        with (
            patch("cr4te.html_builder.prepare_output_dirs"),
            patch("cr4te.html_builder.copy_static_assets"),
            patch("cr4te.html_builder.prepare_default_thumbnails"),
            patch("cr4te.html_builder.render_creator_page"),
            patch("cr4te.html_builder.render_project_page"),
            patch("cr4te.html_builder.render_creator_overview_page"),
            patch("cr4te.html_builder.render_project_overview_page"),
            patch("cr4te.html_builder.render_tags_page"),
            patch("cr4te.html_builder.build_creator_overview_entry_from_index", return_value=SimpleNamespace(name="Noomi")),
            patch(
                "cr4te.html_builder.build_project_overview_entry_from_index",
                return_value=SimpleNamespace(title="Landscapes", creator_name="Noomi"),
            ),
            patch("cr4te.html_builder.build_creator_page_context", side_effect=creator_context),
            patch("cr4te.html_builder.build_project_page_context", side_effect=project_context),
            patch("cr4te.html_builder.logger.info", side_effect=lambda message: events.append(message)),
        ):
            build_html_pages_streaming(
                index,
                discover_themes(None),
                Path("site"),
                config.site_labels,
                config.site_rendering,
                lambda summary: creator,
            )

        self.assertLess(events.index("Building creator page: Noomi"), events.index("creator-context"))
        self.assertLess(events.index("Building project page: Noomi - Landscapes"), events.index("project-context"))

    def test_streaming_html_build_renders_from_lightweight_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "Artists"
            output_dir = Path(tmp) / "site"
            creator_dir = root / "Noomi"
            project_dir = creator_dir / "Landscapes"
            write_image(creator_dir / "portrait.jpg", (80, 160))
            write_image(project_dir / "cover.jpg")
            write_json(
                creator_dir / "cr4te.json",
                {
                    "portrait": "portrait.jpg",
                },
            )
            write_json(project_dir / "cr4te.json", {"cover": "cover.jpg"})

            config = apply_cli_overrides(load_config(), domain=Domain.ART)
            index = build_library_index(root, config.media_rules)
            loaded = []

            def load_creator(summary):
                loaded.append(summary.name)
                return load_indexed_creator(index, summary, config.media_rules)

            build_html_pages_streaming(
                index,
                discover_themes(None),
                output_dir,
                config.site_labels,
                config.site_rendering,
                load_creator,
            )

            self.assertEqual(loaded, ["Noomi"])
            self.assertTrue((output_dir / "index.html").exists())
            self.assertTrue((output_dir / "projects.html").exists())
            html_pages = list((output_dir / "html").rglob("*.html"))
            self.assertEqual(len(html_pages), 2)

    def test_streaming_html_build_copies_and_renders_custom_theme(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "Artists"
            output_dir = Path(tmp) / "site"
            themes_dir = Path(tmp) / "themes"
            custom_theme = themes_dir / "custom-night.css"
            root.mkdir()
            custom_theme.parent.mkdir(parents=True)
            custom_theme.write_text(
                ".theme-custom-night { --theme-page-bg: rgb(1, 2, 3); }",
                encoding="utf-8",
            )

            config = apply_cli_overrides(load_config(), domain=Domain.ART)
            index = build_library_index(root, config.media_rules)
            build_html_pages_streaming(
                index,
                discover_themes(themes_dir),
                output_dir,
                config.site_labels,
                config.site_rendering,
                lambda summary: load_indexed_creator(index, summary, config.media_rules),
            )

            self.assertEqual((output_dir / "assets" / "css" / "themes" / "custom-night.css").read_text(
                encoding="utf-8",
            ), custom_theme.read_text(encoding="utf-8"))
            rendered = (output_dir / "index.html").read_text(encoding="utf-8")
            self.assertIn('data-theme="theme-custom-night"', rendered)
            self.assertIn('assets/css/themes/custom-night.css', rendered)

    def test_streaming_html_build_keeps_best_effort_project_recovery(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "Artists"
            output_dir = Path(tmp) / "site"
            good_project = root / "Noomi" / "Good Project"
            bad_project = root / "Noomi" / "Bad Project"
            good_project.mkdir(parents=True)
            bad_project.mkdir(parents=True)
            write_json(good_project / "cr4te.json", {})
            write_json(bad_project / "cr4te.json", {"release_date": "Spring 2024"})

            config = apply_cli_overrides(load_config(), domain=Domain.ART)
            index = build_library_index(root, config.media_rules)

            self.assertEqual(len(index.issues), 1)
            self.assertEqual([project.title for project in index.creator_by_name["Noomi"].projects], ["Good Project"])

            build_html_pages_streaming(
                index,
                discover_themes(None),
                output_dir,
                config.site_labels,
                config.site_rendering,
                lambda summary: load_indexed_creator(index, summary, config.media_rules),
            )

            html_pages = list((output_dir / "html").rglob("*.html"))
            self.assertEqual(len(html_pages), 2)
            rendered = "\n".join(path.read_text(encoding="utf-8") for path in html_pages)
            self.assertIn("Good Project", rendered)
            self.assertNotIn("Bad Project", rendered)


if __name__ == "__main__":
    unittest.main()
