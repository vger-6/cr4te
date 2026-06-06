import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cr4te.enums.creator_type import CreatorType
from cr4te.enums.visible_fields import ProjectField
from cr4te.library_index import ProjectSummary
from cr4te.media_counts import MediaCounts
from cr4te.schemas.library_schema import Creator, Project
from cr4te.tag_contexts import (
    build_tag_search_terms,
    collect_tags_from_creator,
    merge_tag_maps,
    project_summary_values,
)


class TagContextTests(unittest.TestCase):
    def test_merge_tag_maps_normalizes_sorts_and_deduplicates(self):
        tags = merge_tag_maps(
            {"Mood": ["Calm", "  Bright  ", "Calm"], " ": ["Ignored"]},
            {"Mood": ["Quiet"], "Role": ["Photographer"]},
        )

        self.assertEqual(
            tags.as_dict(),
            {
                "Mood": ["Bright", "Calm", "Quiet"],
                "Role": ["Photographer"],
            },
        )

    def test_collect_tags_from_creator_includes_project_tags(self):
        project = Project(
            title="Landscapes",
            display_title="Displayed Landscapes",
            release_date="",
            cover="",
            info="",
            tags={"Mood": ["Calm"]},
            facets={},
            media_groups=[],
        )
        creator = Creator(
            name="Noomi",
            display_name="Displayed Noomi",
            type=CreatorType.PERSON,
            active_since="",
            portrait="",
            info="",
            tags={"Role": ["Photographer"]},
            projects=[project],
            media_groups=[],
        )

        self.assertEqual(
            collect_tags_from_creator(creator).as_dict(),
            {
                "Mood": ["Calm"],
                "Role": ["Photographer"],
            },
        )

    def test_build_tag_search_terms_uses_canonical_tag_collection(self):
        self.assertEqual(
            build_tag_search_terms({"Mood": ["Calm", "Bright"]}),
            ["Mood:Bright", "Mood:Calm"],
        )

    def test_project_summary_values_ignores_string_facet_keys(self):
        summary = ProjectSummary(
            title="Landscapes",
            display_title="Displayed Landscapes",
            release_date="",
            cover="",
            tags={},
            facets={ProjectField.MEDIUMS: ["Photography"], "materials": ["Paper"]},
            media_counts=MediaCounts(),
        )

        self.assertEqual(project_summary_values(summary, ProjectField.MEDIUMS), ["Photography"])
        self.assertEqual(project_summary_values(summary, ProjectField.MATERIALS), [])


if __name__ == "__main__":
    unittest.main()
