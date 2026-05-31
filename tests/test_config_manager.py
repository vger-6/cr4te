import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cr4te.config_manager import apply_cli_overrides, load_config
from cr4te.config_presets import DEFAULT_CONFIG, get_domain_preset
from cr4te.enums.domain import Domain
from cr4te.enums.visible_fields import ProjectField


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


class ConfigManagerTests(unittest.TestCase):
    def test_default_config_and_domain_presets_validate(self):
        base = load_config()

        self.assertTrue(DEFAULT_CONFIG["site_labels"]["entity"]["creator"])

        for domain in Domain:
            config = apply_cli_overrides(base, domain=domain)
            preset_sections = get_domain_preset(domain).sections()

            self.assertTrue(config.site_labels.entity.creator)
            self.assertEqual(set(preset_sections), {"site_labels", "site_rendering", "media_rules"})

    def test_domain_preset_sections_are_copies(self):
        sections = get_domain_preset(Domain.FILM).sections()
        sections["site_labels"]["entity"]["creator"] = "Changed"
        sections["site_rendering"]["galleries"]["project_cards"]["aspect_ratio"] = "1/1"

        fresh_sections = get_domain_preset(Domain.FILM).sections()

        self.assertEqual(fresh_sections["site_labels"]["entity"]["creator"], "Director")
        self.assertEqual(fresh_sections["site_rendering"]["galleries"]["project_cards"]["aspect_ratio"], "2/3")

    def test_load_config_accepts_partial_current_config_sections(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            write_json(config_path, {"site_labels": {"entity": {"creators": "Artists"}}})

            config = load_config(config_path)

            self.assertEqual(config.site_labels.entity.creators, "Artists")
            self.assertEqual(config.site_labels.entity.creator, "Creator")
            self.assertEqual(config.site_labels.controls.play, "Play")

    def test_load_config_accepts_project_facet_label_overrides(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            write_json(
                config_path,
                {
                    "site_labels": {
                        "project_facets": {
                            "actors": {
                                "singular": "Cast Member",
                                "plural": "Cast",
                            }
                        }
                    }
                },
            )

            config = load_config(config_path)

            self.assertEqual(config.site_labels.project_facets[ProjectField.ACTORS].resolve(1), "Cast Member")
            self.assertEqual(config.site_labels.project_facets[ProjectField.ACTORS].resolve(2), "Cast")
            self.assertEqual(config.site_labels.project_facets[ProjectField.GENRES].resolve(2), "Genres")

    def test_load_config_accepts_partial_nested_rendering_sections(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            write_json(
                config_path,
                {
                    "site_rendering": {
                        "galleries": {
                            "project_cards": {
                                "aspect_ratio": "4/5",
                                "page_size": 25,
                            }
                        }
                    }
                },
            )

            config = load_config(config_path)

            self.assertEqual(config.site_rendering.galleries.project_cards.aspect_ratio, "4/5")
            self.assertEqual(config.site_rendering.galleries.project_cards.page_size, 25)
            self.assertEqual(config.site_rendering.galleries.project_cards.image_max_height, 350)

    def test_project_metadata_rendering_resolves_defaults_and_field_overrides(self):
        config = apply_cli_overrides(load_config(), domain=Domain.FILM)
        project_metadata = config.site_rendering.project_metadata

        actors = project_metadata.rendering_for(ProjectField.ACTORS)
        unknown = project_metadata.rendering_for(ProjectField.MEDIUMS)

        self.assertEqual(project_metadata.configured_fields()[0], ProjectField.STUDIOS)
        self.assertEqual(actors.separator, "<br>")
        self.assertTrue(actors.searchable)
        self.assertTrue(actors.clickable)
        self.assertTrue(actors.tags)
        self.assertEqual(unknown.separator, ", ")
        self.assertFalse(unknown.searchable)

    def test_domain_override_replaces_active_project_metadata_fields(self):
        music_config = apply_cli_overrides(load_config(), domain=Domain.MUSIC)

        art_config = apply_cli_overrides(music_config, domain=Domain.ART)
        creator_config = apply_cli_overrides(music_config, domain=Domain.CREATOR)

        self.assertEqual(
            art_config.site_rendering.project_metadata.configured_fields(),
            [ProjectField.MEDIUMS, ProjectField.MATERIALS, ProjectField.EXHIBITIONS, ProjectField.PERIODS],
        )
        self.assertEqual(creator_config.site_rendering.project_metadata.configured_fields(), [])

    def test_load_config_rejects_unknown_top_level_sections(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            write_json(config_path, {"unknown_section": {}})

            with self.assertRaises(ValueError) as caught:
                load_config(config_path)

            self.assertIn("Unknown config section", str(caught.exception))
            self.assertIn("unknown_section", str(caught.exception))

    def test_load_config_rejects_unknown_nested_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            write_json(config_path, {"media_rules": {"unknown_media_rule": True}})

            with self.assertRaises(ValueError) as caught:
                load_config(config_path)

            self.assertIn("unknown_media_rule", str(caught.exception))
            self.assertIn("Extra inputs", str(caught.exception))

    def test_load_config_rejects_unknown_nested_label_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            write_json(config_path, {"site_labels": {"entity": {"unknown_label": "nope"}}})

            with self.assertRaises(ValueError) as caught:
                load_config(config_path)

            self.assertIn("site_labels > entity > unknown_label", str(caught.exception))
            self.assertIn("Extra inputs", str(caught.exception))

    def test_load_config_rejects_old_flat_rendering_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            write_json(config_path, {"site_rendering": {"project_gallery_aspect_ratio": "1/1"}})

            with self.assertRaises(ValueError) as caught:
                load_config(config_path)

            self.assertIn("site_rendering > project_gallery_aspect_ratio", str(caught.exception))
            self.assertIn("Extra inputs", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
