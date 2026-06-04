import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cr4te.config_manager import apply_cli_overrides, load_config
from cr4te.html_context import HtmlBuildContext
from cr4te.enums.domain import Domain
from cr4te.enums.visible_fields import ProjectField
from cr4te.taxonomy import get_domain_project_metadata_fields, get_domain_project_visible_metadata


class TaxonomyTests(unittest.TestCase):
    def test_domain_fields_come_from_single_registry(self):
        self.assertEqual(
            get_domain_project_metadata_fields(Domain.ART),
            (
                ProjectField.MEDIUMS,
                ProjectField.MATERIALS,
                ProjectField.EXHIBITIONS,
                ProjectField.PERIODS,
            ),
        )
        self.assertIn(ProjectField.ACTORS, get_domain_project_metadata_fields(Domain.FILM))
        self.assertNotIn(ProjectField.ACTORS, get_domain_project_metadata_fields(Domain.ART))
        self.assertIn(ProjectField.COMPOSERS, get_domain_project_metadata_fields(Domain.MUSIC))
        self.assertNotIn(ProjectField.COMPOSERS, get_domain_project_metadata_fields(Domain.FILM))

    def test_domain_visible_metadata_uses_registry_rendering(self):
        visible = get_domain_project_visible_metadata(Domain.FILM)

        self.assertEqual(visible[ProjectField.ACTORS]["separator"], "<br>")
        self.assertTrue(visible[ProjectField.ACTORS]["searchable"])
        self.assertTrue(visible[ProjectField.ACTORS]["clickable"])
        self.assertTrue(visible[ProjectField.ACTORS]["tags"])
        self.assertFalse(visible[ProjectField.COSTUME_DESIGNERS]["searchable"])

    def test_project_facet_labels_are_resolved_from_registry(self):
        config = apply_cli_overrides(load_config(), domain=Domain.FILM)
        ctx = HtmlBuildContext(
            input_dir=Path("input"),
            output_dir=Path("output"),
            site_labels=config.site_labels,
            site_rendering=config.site_rendering,
        )

        self.assertEqual(ctx.meta_label(ProjectField.ACTORS, 1), "Actor")
        self.assertEqual(ctx.meta_label(ProjectField.ACTORS, 2), "Actors")
        self.assertEqual(ctx.meta_filter_label(ProjectField.GENRES), "Genres")
        self.assertEqual(ctx.meta_label(ProjectField.COMPOSERS, 1), "Composer")
        self.assertEqual(ctx.meta_filter_label(ProjectField.COMPOSERS), "Composers")

    def test_project_facet_label_overrides_flow_into_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "site_labels": {
                            "project_facets": {
                                "actors": {
                                    "singular": "Cast Member",
                                    "plural": "Cast",
                                }
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )

            config = apply_cli_overrides(load_config(config_path), domain=Domain.FILM)
            ctx = HtmlBuildContext(
                input_dir=Path("input"),
                output_dir=Path("output"),
                site_labels=config.site_labels,
                site_rendering=config.site_rendering,
            )

            self.assertEqual(ctx.meta_label(ProjectField.ACTORS, 1), "Cast Member")
            self.assertEqual(ctx.meta_filter_label(ProjectField.ACTORS), "Cast")


if __name__ == "__main__":
    unittest.main()
