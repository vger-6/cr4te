import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cr4te.config_manager import apply_cli_overrides, load_config
from cr4te.html_context import HtmlBuildContext
from cr4te.enums.creator_type import CreatorType
from cr4te.enums.domain import Domain
from cr4te.enums.portrait_visibility import PortraitVisibility
from cr4te.enums.visible_fields import ProjectField
from cr4te.library_index import CreatorSummary, ProjectSummary
from cr4te.media_counts import MediaCounts
from cr4te.output_preparation import prepare_output_dirs
from cr4te.overview_contexts import build_creator_overview_entry_from_index, sort_project_summary
from cr4te.render_assets import prepare_default_thumbnails


def context_for(
    input_dir: Path,
    output_dir: Path,
    portrait_visibility: PortraitVisibility = PortraitVisibility.ALL,
) -> HtmlBuildContext:
    config = apply_cli_overrides(load_config(), domain=Domain.ART, portrait_visibility=portrait_visibility)
    ctx = HtmlBuildContext(input_dir, output_dir, config.site_labels, config.site_rendering)
    prepare_output_dirs(ctx)
    prepare_default_thumbnails(ctx)
    return ctx


class OverviewContextTests(unittest.TestCase):
    def test_disabled_portraits_build_text_summary_without_thumbnail_work(self):
        """Covers SITE-014 and SITE-029."""
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp) / "input"
            output_dir = Path(tmp) / "site"
            ctx = context_for(input_dir, output_dir, PortraitVisibility.DISABLED)
            creator = CreatorSummary(
                path=input_dir / "Noomi",
                name="Noomi",
                display_name="Displayed Noomi",
                type=CreatorType.PERSON,
                portrait="Noomi/portrait.jpg",
                aliases=(),
                collaborations=(),
                tags={},
                active_since="",
                nationalities=(),
                info="",
                media_counts=MediaCounts(audio=1, image=2),
                projects=(
                    ProjectSummary(
                        title="Landscapes",
                        display_title="Landscapes",
                        release_date="",
                        cover="",
                        tags={},
                        facets={},
                        media_counts=MediaCounts(),
                    ),
                ),
            )

            with patch("cr4te.overview_contexts.build_thumbnail_context") as build_thumbnail:
                entry = build_creator_overview_entry_from_index(ctx, creator)

            build_thumbnail.assert_not_called()
            self.assertEqual(entry.rel_thumbnail_path, "")
            self.assertEqual(entry.image_wrapper_width, 0)
            self.assertEqual(entry.image_wrapper_height, 0)
            self.assertEqual(entry.project_count_summary, "1 work")
            self.assertEqual(entry.media_count_summary, "1 audio track | 2 images")

            empty_creator = CreatorSummary(
                path=input_dir / "Ada",
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
            )
            empty_entry = build_creator_overview_entry_from_index(ctx, empty_creator)
            self.assertEqual(empty_entry.project_count_summary, "")
            self.assertEqual(empty_entry.media_count_summary, "")

    def test_details_portraits_use_text_overview_without_thumbnail_work(self):
        """Covers SITE-028."""
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp) / "input"
            output_dir = Path(tmp) / "site"
            ctx = context_for(input_dir, output_dir, PortraitVisibility.DETAILS)
            creator = CreatorSummary(
                path=input_dir / "Noomi",
                name="Noomi",
                display_name="Noomi",
                type=CreatorType.PERSON,
                portrait="Noomi/portrait.jpg",
                aliases=(),
                collaborations=(),
                tags={},
                active_since="",
                nationalities=(),
                info="",
            )

            with patch("cr4te.overview_contexts.build_thumbnail_context") as build_thumbnail:
                entry = build_creator_overview_entry_from_index(ctx, creator)

            build_thumbnail.assert_not_called()
            self.assertEqual(entry.rel_thumbnail_path, "")

    def test_all_portraits_use_image_overview_default_when_discovery_is_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp) / "input"
            output_dir = Path(tmp) / "site"
            ctx = context_for(input_dir, output_dir, PortraitVisibility.ALL)
            creator = CreatorSummary(
                path=input_dir / "Noomi",
                name="Noomi",
                display_name="Noomi",
                type=CreatorType.PERSON,
                portrait="",
                aliases=(),
                collaborations=(),
                tags={},
                active_since="",
                nationalities=(),
                info="",
            )

            entry = build_creator_overview_entry_from_index(ctx, creator)

            self.assertEqual(entry.rel_thumbnail_path, "assets/defaults/creator-overview.png")
            self.assertGreater(entry.image_wrapper_width, 0)
            self.assertGreater(entry.image_wrapper_height, 0)

    def test_creator_overview_search_text_uses_summary_tags_and_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp) / "input"
            output_dir = Path(tmp) / "site"
            ctx = context_for(input_dir, output_dir)
            project = ProjectSummary(
                title="Canonical Project",
                display_title="Displayed Landscapes",
                release_date="",
                cover="",
                tags={"Mood": ["Calm"]},
                facets={ProjectField.MEDIUMS: ["Photography"]},
                media_counts=MediaCounts(),
            )
            creator = CreatorSummary(
                path=input_dir / "Noomi",
                name="Canonical Creator",
                display_name="Displayed Noomi",
                type=CreatorType.PERSON,
                portrait="",
                aliases=("N.",),
                collaborations=(),
                tags={"Role": ["Photographer"]},
                active_since="",
                nationalities=("German",),
                info="",
                projects=(project,),
            )

            entry = build_creator_overview_entry_from_index(ctx, creator)

            self.assertIn("displayed noomi", entry.search_text)
            self.assertIn("displayed landscapes", entry.search_text)
            self.assertNotIn("canonical creator", entry.search_text)
            self.assertNotIn("canonical project", entry.search_text)
            self.assertIn("n.", entry.search_text)
            self.assertIn("role:photographer", entry.search_text)
            self.assertIn("mood:calm", entry.search_text)
            self.assertIn("mediums:photography", entry.search_text)
            self.assertIn("nationalities:german", entry.search_text)

    def test_sort_project_summary_orders_dated_projects_before_undated(self):
        dated = ProjectSummary(
            title="B",
            display_title="Z",
            release_date="2024",
            cover="",
            tags={},
            facets={},
            media_counts=MediaCounts(),
        )
        undated = ProjectSummary(
            title="A",
            display_title="A",
            release_date="",
            cover="",
            tags={},
            facets={},
            media_counts=MediaCounts(),
        )

        self.assertEqual(sorted([undated, dated], key=sort_project_summary), [dated, undated])

    def test_sort_project_summary_uses_display_title(self):
        first = ProjectSummary(
            title="Z Folder",
            display_title="A Display",
            release_date="",
            cover="",
            tags={},
            facets={},
            media_counts=MediaCounts(),
        )
        second = ProjectSummary(
            title="A Folder",
            display_title="Z Display",
            release_date="",
            cover="",
            tags={},
            facets={},
            media_counts=MediaCounts(),
        )

        self.assertEqual(sorted([second, first], key=sort_project_summary), [first, second])


if __name__ == "__main__":
    unittest.main()
