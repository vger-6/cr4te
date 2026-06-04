import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cr4te.config_manager import apply_cli_overrides, load_config
from cr4te.enums.domain import Domain
from cr4te.enums.visible_fields import CollaborationField, CreatorField, ProjectField
from cr4te.metadata_fields import CORE_META_FIELD_SPECS, MetadataLabelKey, get_core_meta_field
from cr4te.schemas.config_schema import MetadataLabels
from cr4te.taxonomy import PROJECT_FACETS, get_project_facet


class MetadataFieldsTests(unittest.TestCase):
    def test_metadata_label_keys_are_site_label_fields(self):
        label_fields = set(MetadataLabels.model_fields)

        for key in MetadataLabelKey:
            self.assertIn(key.value, label_fields, key)

    def test_metadata_registries_use_typed_label_keys(self):
        for spec in CORE_META_FIELD_SPECS:
            self.assertIsInstance(spec.labels.singular, MetadataLabelKey)
            self.assertIsInstance(spec.labels.plural, MetadataLabelKey)

    def test_project_facet_labels_are_configured_by_project_field(self):
        config = apply_cli_overrides(load_config(), domain=Domain.FILM)

        for facet in PROJECT_FACETS:
            configured_labels = config.site_labels.project_facets[facet.field]

            self.assertTrue(configured_labels.resolve(1))
            self.assertTrue(configured_labels.resolve(2))

    def test_core_creator_and_collaboration_fields_have_registered_labels(self):
        config = apply_cli_overrides(load_config(), domain=Domain.ART)

        for field in CreatorField:
            spec = get_core_meta_field(field)
            self.assertIsNotNone(spec, field)
            self.assertTrue(spec.resolve_label(config.site_labels, 2))

        for field in CollaborationField:
            spec = get_core_meta_field(field)
            self.assertIsNotNone(spec, field)
            self.assertTrue(spec.resolve_label(config.site_labels, 2))

    def test_project_fields_are_covered_by_core_labels_or_facet_registry(self):
        config = apply_cli_overrides(load_config(), domain=Domain.FILM)

        for field in ProjectField:
            core_spec = get_core_meta_field(field)
            facet_spec = get_project_facet(field)
            self.assertTrue(core_spec or facet_spec, field)

            if core_spec:
                self.assertTrue(core_spec.resolve_label(config.site_labels, 2))
            if facet_spec:
                self.assertTrue(config.site_labels.project_facets[facet_spec.field].resolve(2))


if __name__ == "__main__":
    unittest.main()
