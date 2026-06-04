import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cr4te.config_manager import apply_cli_overrides, load_config
from cr4te.html_context import HtmlBuildContext
from cr4te.enums.creator_type import CreatorType
from cr4te.enums.domain import Domain
from cr4te.enums.visible_fields import ProjectField
from cr4te.library_index import CreatorSummary, ProjectSummary
from cr4te.media_counts import MediaCounts
from cr4te.output_preparation import prepare_output_dirs
from cr4te.overview_contexts import build_creator_overview_entry_from_index, sort_project_summary
from cr4te.render_assets import prepare_default_thumbnails


def context_for(input_dir: Path, output_dir: Path) -> HtmlBuildContext:
    config = apply_cli_overrides(load_config(), domain=Domain.ART)
    ctx = HtmlBuildContext(input_dir, output_dir, config.site_labels, config.site_rendering)
    prepare_output_dirs(ctx)
    prepare_default_thumbnails(ctx)
    return ctx


class OverviewContextTests(unittest.TestCase):
    def test_creator_overview_search_text_uses_summary_tags_and_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp) / "input"
            output_dir = Path(tmp) / "site"
            ctx = context_for(input_dir, output_dir)
            project = ProjectSummary(
                title="Landscapes",
                release_date="",
                cover="",
                tags={"Mood": ["Calm"]},
                facets={ProjectField.MEDIUMS: ["Photography"]},
                media_counts=MediaCounts(),
            )
            creator = CreatorSummary(
                path=input_dir / "Noomi",
                name="Noomi",
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

            self.assertIn("noomi", entry.search_text)
            self.assertIn("n.", entry.search_text)
            self.assertIn("role:photographer", entry.search_text)
            self.assertIn("mood:calm", entry.search_text)
            self.assertIn("mediums:photography", entry.search_text)
            self.assertIn("nationalities:german", entry.search_text)

    def test_sort_project_summary_orders_dated_projects_before_undated(self):
        dated = ProjectSummary(
            title="B",
            release_date="2024",
            cover="",
            tags={},
            facets={},
            media_counts=MediaCounts(),
        )
        undated = ProjectSummary(
            title="A",
            release_date="",
            cover="",
            tags={},
            facets={},
            media_counts=MediaCounts(),
        )

        self.assertEqual(sorted([undated, dated], key=sort_project_summary), [dated, undated])


if __name__ == "__main__":
    unittest.main()
