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
from cr4te.enums.portrait_discovery import PortraitDiscovery
from cr4te.enums.portrait_visibility import PortraitVisibility
from cr4te.enums.visible_fields import CollaborationField, CreatorField, ProjectField
from cr4te.schemas.config_schema import GalleryLayoutRendering


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
            self.assertEqual(config.site_labels.counts.project, config.site_labels.entity.project.lower())
            self.assertEqual(config.site_labels.counts.projects, config.site_labels.entity.projects.lower())
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
            self.assertEqual(config.site_labels.counts.project, "project")
            self.assertEqual(config.site_labels.controls.play, "Play")
            self.assertEqual(config.site_labels.empty_states.no_media, "No media available")

    def test_project_count_labels_are_configurable_independently_from_entity_labels(self):
        """Covers SITE-031."""
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            write_json(
                config_path,
                {
                    "site_labels": {
                        "entity": {"project": "Release", "projects": "Releases"},
                        "counts": {"project": "record", "projects": "records"},
                    }
                },
            )

            config = load_config(config_path)

            self.assertEqual(config.site_labels.entity.project, "Release")
            self.assertEqual(config.site_labels.entity.projects, "Releases")
            self.assertEqual(config.site_labels.counts.project, "record")
            self.assertEqual(config.site_labels.counts.projects, "records")

    def test_portrait_discovery_and_visibility_resolve_in_owned_sections(self):
        config = load_config()

        self.assertEqual(config.media_rules.portrait_discovery, PortraitDiscovery.NAMED)
        self.assertEqual(config.media_rules.portrait_basename, "portrait")
        self.assertEqual(config.site_rendering.portraits.visibility, PortraitVisibility.ALL)

    def test_portrait_overrides_do_not_reset_when_omitted(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            write_json(
                config_path,
                {
                    "media_rules": {"portrait_discovery": "auto"},
                    "site_rendering": {"portraits": {"visibility": "details"}},
                },
            )

            configured = load_config(config_path)
            preserved = apply_cli_overrides(configured, domain=Domain.ART)
            overridden = apply_cli_overrides(
                configured,
                portrait_discovery=PortraitDiscovery.NAMED,
                portrait_visibility=PortraitVisibility.DISABLED,
            )

            self.assertEqual(preserved.media_rules.portrait_discovery, PortraitDiscovery.AUTO)
            self.assertEqual(preserved.site_rendering.portraits.visibility, PortraitVisibility.DETAILS)
            self.assertEqual(overridden.media_rules.portrait_discovery, PortraitDiscovery.NAMED)
            self.assertEqual(overridden.site_rendering.portraits.visibility, PortraitVisibility.DISABLED)

    def test_removed_portrait_configuration_fields_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            write_json(config_path, {"portraits": {"mode": "named"}})

            with self.assertRaises(ValueError) as caught:
                load_config(config_path)

            self.assertIn("portraits", str(caught.exception))

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

    def test_gallery_aspect_ratio_config_normalizes_supported_values(self):
        valid_ratios = {
            "3/2": "3/2",
            "2/3": "2/3",
            "1/1": "1/1",
            " 03 / 002 ": "3/2",
            "1000/1414": "1000/1414",
        }

        for value, expected in valid_ratios.items():
            with self.subTest(value=value):
                rendering = GalleryLayoutRendering(building_strategy="aspect", aspect_ratio=value)

                self.assertEqual(rendering.aspect_ratio, expected)

    def test_gallery_aspect_ratio_config_rejects_unsupported_values_with_clear_error(self):
        invalid_ratios = ("3", "3/2/1", "3.0/2", "3:2", "0/2", "-3/2", ["3", "2"])

        for value in invalid_ratios:
            with self.subTest(value=value), self.assertRaisesRegex(
                ValueError,
                r"Aspect ratio must use two positive integers in width/height format, for example 3/2\.",
            ):
                GalleryLayoutRendering(building_strategy="aspect", aspect_ratio=value)

    def test_metadata_date_and_place_format_is_configurable_as_a_label(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            write_json(
                config_path,
                {
                    "site_labels": {
                        "metadata": {
                            "date_and_place_format": "{place}, {date}",
                        }
                    }
                },
            )

            config = load_config(config_path)

            self.assertEqual(
                config.site_labels.metadata.date_and_place_format,
                "{place}, {date}",
            )

    def test_metadata_labels_reject_invalid_date_and_place_formats(self):
        for value in ("{0} in {1}", "{date}", "{date} in {location}", "{date!r} in {place}"):
            with self.subTest(value=value), tempfile.TemporaryDirectory() as tmp:
                config_path = Path(tmp) / "config.json"
                write_json(
                    config_path,
                    {
                        "site_labels": {
                            "metadata": {
                                "date_and_place_format": value,
                            }
                        }
                    },
                )

                with self.assertRaises(ValueError) as caught:
                    load_config(config_path)

                self.assertIn("date_and_place_format", str(caught.exception))

    def test_complete_phrase_formats_are_configurable_and_reorder_named_values(self):
        """Covers SITE-021."""
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            write_json(
                config_path,
                {
                    "site_labels": {
                        "controls": {
                            "search_placeholder_format": "{tags}; {projects}; {creators}: search",
                        },
                        "pages": {
                            "creator_collaboration_projects_title_format": "{collaborator}: {projects}",
                        },
                        "accessibility": {
                            "creator_portrait_description_format": "{creator}, portrait",
                            "project_preview_description_format": "{project}, preview",
                        },
                        "empty_states": {
                            "no_creators_format": "{creators}: none",
                            "no_projects_format": "{projects}: none",
                            "no_tags_format": "{tags}: none",
                            "no_projects_or_media_format": "No media or {projects}",
                        },
                    }
                },
            )

            labels = load_config(config_path).site_labels

            self.assertEqual(
                labels.controls.search_placeholder_format.format(
                    creators="Artists",
                    projects="Works",
                    tags="Tags",
                ),
                "Tags; Works; Artists: search",
            )
            self.assertEqual(
                labels.pages.creator_collaboration_projects_title_format.format(
                    collaborator="Ada",
                    projects="Works",
                ),
                "Ada: Works",
            )
            self.assertEqual(
                labels.accessibility.creator_portrait_description_format.format(creator="Ada"),
                "Ada, portrait",
            )
            self.assertEqual(
                labels.accessibility.project_preview_description_format.format(project="Notes"),
                "Notes, preview",
            )
            self.assertEqual(labels.empty_states.no_creators_format.format(creators="Artists"), "Artists: none")
            self.assertEqual(labels.empty_states.no_projects_format.format(projects="Works"), "Works: none")
            self.assertEqual(labels.empty_states.no_tags_format.format(tags="Keywords"), "Keywords: none")
            self.assertEqual(labels.empty_states.no_projects_or_media_format.format(projects="Works"), "No media or Works")

    def test_complete_phrase_formats_reject_missing_or_unknown_placeholders(self):
        invalid_formats = (
            ("controls", "search_placeholder_format", "Search {creators}"),
            ("pages", "creator_collaboration_projects_title_format", "{projects}"),
            ("accessibility", "creator_portrait_description_format", "Portrait"),
            ("accessibility", "project_preview_description_format", "Preview of {creator}"),
            ("empty_states", "no_creators_format", "No creators"),
            ("empty_states", "no_projects_format", "No {creators}"),
            ("empty_states", "no_tags_format", "No {projects}"),
            ("empty_states", "no_projects_or_media_format", "No media"),
        )

        for section, key, value in invalid_formats:
            with self.subTest(section=section, key=key, value=value), tempfile.TemporaryDirectory() as tmp:
                config_path = Path(tmp) / "config.json"
                write_json(config_path, {"site_labels": {section: {key: value}}})

                with self.assertRaises(ValueError) as caught:
                    load_config(config_path)

                self.assertIn(key, str(caught.exception))

    def test_domain_presets_resolve_complete_phrase_formats_from_domain_labels(self):
        film = apply_cli_overrides(load_config(), domain=Domain.FILM).site_labels
        model = apply_cli_overrides(load_config(), domain=Domain.MODEL).site_labels
        art = apply_cli_overrides(load_config(), domain=Domain.ART).site_labels

        self.assertEqual(
            film.pages.creator_collaboration_projects_title_format.format(
                projects=film.entity.projects,
                collaborator="Ada",
            ),
            "Codirected with Ada",
        )
        self.assertEqual(
            model.pages.creator_collaboration_projects_title_format.format(
                projects=model.entity.projects,
                collaborator="Ada",
            ),
            "Scenes with Ada",
        )
        self.assertEqual(
            art.controls.search_placeholder_format.format(
                creators=art.entity.creators,
                projects=art.entity.projects,
                tags=art.entity.tags,
            ),
            "Search Artists, Works, Tags...",
        )
        self.assertEqual(
            art.empty_states.no_projects_format.format(projects=art.entity.projects),
            "No Works available",
        )

    def test_selected_domain_presets_hide_only_collaboration_names(self):
        expected_members_labels = {
            Domain.BOOK: "Authors",
            Domain.FILM: "Directors'",
            Domain.MODEL: "Models",
        }

        for domain, members_label in expected_members_labels.items():
            with self.subTest(domain=domain):
                config = apply_cli_overrides(load_config(), domain=domain)

                self.assertNotIn(
                    CollaborationField.NAME,
                    config.site_rendering.creator_page.visible_collaboration_fields,
                )
                self.assertNotIn(
                    CollaborationField.NAME,
                    config.site_rendering.project_page.visible_collaboration_fields,
                )
                self.assertIn(
                    CreatorField.NAME,
                    config.site_rendering.creator_page.visible_creator_fields,
                )
                self.assertIn(
                    CreatorField.NAME,
                    config.site_rendering.project_page.visible_creator_fields,
                )
                self.assertEqual(config.site_labels.metadata.members, members_label)

        for domain in (Domain.CREATOR, Domain.MUSIC, Domain.ART):
            with self.subTest(domain=domain):
                config = apply_cli_overrides(load_config(), domain=domain)

                self.assertIn(
                    CollaborationField.NAME,
                    config.site_rendering.creator_page.visible_collaboration_fields,
                )
                self.assertIn(
                    CollaborationField.NAME,
                    config.site_rendering.project_page.visible_collaboration_fields,
                )

    def test_removed_fragment_label_fields_are_rejected(self):
        old_fields = (
            ("controls", "search_placeholder", "Search creators, projects, tags..."),
            ("pages", "creator_collabs_title_prefix", "With"),
        )

        for section, key, value in old_fields:
            with self.subTest(section=section, key=key), tempfile.TemporaryDirectory() as tmp:
                config_path = Path(tmp) / "config.json"
                write_json(config_path, {"site_labels": {section: {key: value}}})

                with self.assertRaises(ValueError) as caught:
                    load_config(config_path)

                self.assertIn(key, str(caught.exception))

    def test_removed_metadata_presentation_rendering_section_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            write_json(
                config_path,
                {
                    "site_rendering": {
                        "metadata_presentation": {
                            "date_and_place_format": "{date} in {place}",
                        }
                    }
                },
            )

            with self.assertRaises(ValueError) as caught:
                load_config(config_path)

            self.assertIn("metadata_presentation", str(caught.exception))

    def test_event_visibility_uses_semantic_fields(self):
        config = load_config()

        self.assertIn(CreatorField.BIRTH, config.site_rendering.creator_page.visible_creator_fields)
        self.assertIn(CreatorField.DEATH, config.site_rendering.creator_page.visible_creator_fields)
        self.assertIn(CollaborationField.FOUNDING, config.site_rendering.creator_page.visible_collaboration_fields)

    def test_removed_component_event_visibility_fields_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            write_json(
                config_path,
                {
                    "site_rendering": {
                        "creator_page": {
                            "visible_creator_fields": ["date_of_birth"],
                        }
                    }
                },
            )

            with self.assertRaises(ValueError) as caught:
                load_config(config_path)

            self.assertIn("visible_creator_fields", str(caught.exception))
            self.assertIn("'birth'", str(caught.exception))

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
