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
from cr4te.enums.image_visibility import ImageVisibility
from cr4te.enums.overview_card_display_mode import OverviewCardDisplayMode
from cr4te.enums.portrait_discovery import PortraitDiscovery
from cr4te.enums.visible_fields import CollaborationField, CreatorField, ProjectField
from cr4te.schemas.config_schema import GalleryLayoutRendering


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


class ConfigManagerTests(unittest.TestCase):
    def assert_image_rendering_defaults(
        self,
        config,
        *,
        creator_overview,
        creator_profile,
        creator_members,
        project_cover,
        project_creator,
        project_collaboration,
        project_participants,
    ):
        self.assertEqual(config.site_rendering.galleries.creator_cards.display_mode, creator_overview)
        self.assertEqual(config.site_rendering.creator_page.show_profile_image, creator_profile)
        self.assertEqual(config.site_rendering.creator_page.show_member_profile_images, creator_members)
        self.assertEqual(config.site_rendering.project_page.show_cover_image, project_cover)
        self.assertEqual(config.site_rendering.project_page.show_creator_profile_image, project_creator)
        self.assertEqual(config.site_rendering.project_page.show_collaboration_profile_image, project_collaboration)
        self.assertEqual(config.site_rendering.project_page.show_participant_profile_images, project_participants)

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
            self.assertEqual(config.site_labels.controls.show_more, "Show more")
            self.assertEqual(config.site_labels.empty_states.no_media, "No media available")
            self.assertEqual(config.site_rendering.document_language, "en-US")
            self.assertEqual(config.site_rendering.creator_page.project_card_gallery_page_rows, 2)
            self.assertEqual(config.site_rendering.creator_page.about_collapsed_lines, 8)
            self.assertEqual(config.site_rendering.creator_page.about_collapsed_lines_mobile, 2)
            self.assertEqual(config.site_rendering.project_page.description_collapsed_lines, 8)
            self.assertEqual(config.site_rendering.project_page.description_collapsed_lines_mobile, 2)

    def test_expandable_text_labels_and_thresholds_are_configurable_independently(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            write_json(
                config_path,
                {
                    "site_labels": {
                        "controls": {
                            "show_more": "Read more",
                            "show_less": "Read less",
                        }
                    },
                    "site_rendering": {
                        "document_language": "de-DE",
                        "creator_page": {
                            "about_collapsed_lines": 6,
                            "about_collapsed_lines_mobile": 3,
                        },
                        "project_page": {
                            "description_collapsed_lines": 10,
                            "description_collapsed_lines_mobile": 4,
                        },
                    },
                },
            )

            config = load_config(config_path)

            self.assertEqual(config.site_rendering.document_language, "de-DE")
            self.assertEqual(config.site_labels.controls.show_more, "Read more")
            self.assertEqual(config.site_labels.controls.show_less, "Read less")
            self.assertEqual(config.site_rendering.creator_page.about_collapsed_lines, 6)
            self.assertEqual(config.site_rendering.creator_page.about_collapsed_lines_mobile, 3)
            self.assertEqual(config.site_rendering.project_page.description_collapsed_lines, 10)
            self.assertEqual(config.site_rendering.project_page.description_collapsed_lines_mobile, 4)

    def test_document_language_must_not_be_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            write_json(config_path, {"site_rendering": {"document_language": "  "}})

            with self.assertRaises(ValueError) as caught:
                load_config(config_path)

            self.assertIn("document_language", str(caught.exception))

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

    def test_portrait_discovery_and_rendering_resolve_in_owned_sections(self):
        config = load_config()

        self.assertEqual(config.media_rules.portrait_discovery, PortraitDiscovery.NAMED)
        self.assertEqual(config.media_rules.portrait_basename, "portrait")
        self.assertEqual(config.site_rendering.galleries.creator_cards.display_mode, OverviewCardDisplayMode.IMAGE)
        self.assertEqual(config.site_rendering.creator_page.show_profile_image, ImageVisibility.SHOW)
        self.assertEqual(config.site_rendering.creator_page.show_member_profile_images, ImageVisibility.SHOW)
        self.assertEqual(config.site_rendering.project_page.show_cover_image, ImageVisibility.SHOW)
        self.assertEqual(config.site_rendering.project_page.show_creator_profile_image, ImageVisibility.SHOW)
        self.assertEqual(config.site_rendering.project_page.show_collaboration_profile_image, ImageVisibility.SHOW)
        self.assertEqual(config.site_rendering.project_page.show_participant_profile_images, ImageVisibility.SHOW)

    def test_domain_presets_resolve_image_rendering_defaults(self):
        base = load_config()

        self.assert_image_rendering_defaults(
            apply_cli_overrides(base, domain=Domain.CREATOR),
            creator_overview=OverviewCardDisplayMode.IMAGE,
            creator_profile=ImageVisibility.SHOW,
            creator_members=ImageVisibility.SHOW,
            project_cover=ImageVisibility.SHOW,
            project_creator=ImageVisibility.SHOW,
            project_collaboration=ImageVisibility.SHOW,
            project_participants=ImageVisibility.SHOW,
        )
        self.assert_image_rendering_defaults(
            apply_cli_overrides(base, domain=Domain.ART),
            creator_overview=OverviewCardDisplayMode.IMAGE,
            creator_profile=ImageVisibility.SHOW,
            creator_members=ImageVisibility.SHOW,
            project_cover=ImageVisibility.SHOW,
            project_creator=ImageVisibility.SHOW,
            project_collaboration=ImageVisibility.SHOW,
            project_participants=ImageVisibility.SHOW,
        )
        self.assert_image_rendering_defaults(
            apply_cli_overrides(base, domain=Domain.MUSIC),
            creator_overview=OverviewCardDisplayMode.IMAGE,
            creator_profile=ImageVisibility.SHOW,
            creator_members=ImageVisibility.SHOW,
            project_cover=ImageVisibility.SHOW,
            project_creator=ImageVisibility.SHOW,
            project_collaboration=ImageVisibility.SHOW,
            project_participants=ImageVisibility.SHOW,
        )
        self.assert_image_rendering_defaults(
            apply_cli_overrides(base, domain=Domain.FILM),
            creator_overview=OverviewCardDisplayMode.TEXT,
            creator_profile=ImageVisibility.IF_AVAILABLE,
            creator_members=ImageVisibility.IF_AVAILABLE,
            project_cover=ImageVisibility.SHOW,
            project_creator=ImageVisibility.IF_AVAILABLE,
            project_collaboration=ImageVisibility.IF_AVAILABLE,
            project_participants=ImageVisibility.IF_AVAILABLE,
        )
        self.assert_image_rendering_defaults(
            apply_cli_overrides(base, domain=Domain.BOOK),
            creator_overview=OverviewCardDisplayMode.TEXT,
            creator_profile=ImageVisibility.IF_AVAILABLE,
            creator_members=ImageVisibility.IF_AVAILABLE,
            project_cover=ImageVisibility.SHOW,
            project_creator=ImageVisibility.IF_AVAILABLE,
            project_collaboration=ImageVisibility.IF_AVAILABLE,
            project_participants=ImageVisibility.IF_AVAILABLE,
        )
        self.assert_image_rendering_defaults(
            apply_cli_overrides(base, domain=Domain.MODEL),
            creator_overview=OverviewCardDisplayMode.IMAGE,
            creator_profile=ImageVisibility.SHOW,
            creator_members=ImageVisibility.SHOW,
            project_cover=ImageVisibility.HIDE,
            project_creator=ImageVisibility.SHOW,
            project_collaboration=ImageVisibility.SHOW,
            project_participants=ImageVisibility.SHOW,
        )

    def test_portrait_discovery_cli_override_preserves_configured_rendering(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            write_json(
                config_path,
                {
                    "media_rules": {"portrait_discovery": "auto"},
                    "site_rendering": {
                        "galleries": {"creator_cards": {"display_mode": "text"}},
                        "creator_page": {
                            "show_profile_image": "hide",
                            "show_member_profile_images": "if_available",
                        },
                        "project_page": {
                            "show_cover_image": "hide",
                            "show_creator_profile_image": "hide",
                            "show_collaboration_profile_image": "if_available",
                            "show_participant_profile_images": "show",
                        },
                    },
                },
            )

            configured = load_config(config_path)
            preserved = apply_cli_overrides(configured, domain=Domain.ART)
            overridden = apply_cli_overrides(
                configured,
                portrait_discovery=PortraitDiscovery.NAMED,
            )

            self.assertEqual(preserved.media_rules.portrait_discovery, PortraitDiscovery.AUTO)
            self.assertEqual(preserved.site_rendering.galleries.creator_cards.display_mode, OverviewCardDisplayMode.TEXT)
            self.assertEqual(preserved.site_rendering.creator_page.show_profile_image, ImageVisibility.HIDE)
            self.assertEqual(preserved.site_rendering.creator_page.show_member_profile_images, ImageVisibility.IF_AVAILABLE)
            self.assertEqual(preserved.site_rendering.project_page.show_cover_image, ImageVisibility.HIDE)
            self.assertEqual(preserved.site_rendering.project_page.show_collaboration_profile_image, ImageVisibility.IF_AVAILABLE)
            self.assertEqual(preserved.site_rendering.project_page.show_participant_profile_images, ImageVisibility.SHOW)
            self.assertEqual(overridden.media_rules.portrait_discovery, PortraitDiscovery.NAMED)
            self.assertEqual(overridden.site_rendering.galleries.creator_cards.display_mode, OverviewCardDisplayMode.TEXT)
            self.assertEqual(overridden.site_rendering.creator_page.show_profile_image, ImageVisibility.HIDE)
            self.assertEqual(overridden.site_rendering.creator_page.show_member_profile_images, ImageVisibility.IF_AVAILABLE)
            self.assertEqual(overridden.site_rendering.project_page.show_cover_image, ImageVisibility.HIDE)
            self.assertEqual(overridden.site_rendering.project_page.show_collaboration_profile_image, ImageVisibility.IF_AVAILABLE)
            self.assertEqual(overridden.site_rendering.project_page.show_participant_profile_images, ImageVisibility.SHOW)

    def test_removed_portrait_configuration_fields_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            write_json(config_path, {"site_rendering": {"portraits": {"visibility": "details"}}})

            with self.assertRaises(ValueError) as caught:
                load_config(config_path)

            self.assertIn("portraits", str(caught.exception))

    def test_legacy_boolean_detail_image_visibility_values_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            write_json(config_path, {"site_rendering": {"creator_page": {"show_profile_image": True}}})

            with self.assertRaises(ValueError) as caught:
                load_config(config_path)

            self.assertIn("show_profile_image", str(caught.exception))

    def test_if_available_detail_image_visibility_value_is_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            write_json(config_path, {"site_rendering": {"creator_page": {"show_profile_image": "if_available"}}})

            config = load_config(config_path)

            self.assertEqual(config.site_rendering.creator_page.show_profile_image, ImageVisibility.IF_AVAILABLE)

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
                                "page_rows": 7,
                            }
                        },
                        "creator_page": {
                            "project_card_gallery_page_rows": 3,
                            "media_gallery_page_rows": 4,
                        },
                        "project_page": {"media_gallery_page_rows": 6},
                    }
                },
            )

            config = load_config(config_path)

            self.assertEqual(config.site_rendering.galleries.project_cards.aspect_ratio, "4/5")
            self.assertEqual(config.site_rendering.galleries.project_cards.page_rows, 7)
            self.assertEqual(config.site_rendering.galleries.project_cards.image_max_height, 300)
            self.assertEqual(config.site_rendering.galleries.project_cards.creator_page_image_max_height, 300)
            self.assertEqual(config.site_rendering.creator_page.project_card_gallery_page_rows, 3)
            self.assertEqual(config.site_rendering.creator_page.media_gallery_page_rows, 4)
            self.assertEqual(config.site_rendering.project_page.media_gallery_page_rows, 6)

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
                            "tag_actions_label_format": "Use {tag}",
                            "find_in_creators_format": "Browse {creators}",
                            "find_in_projects_format": "Browse {projects}",
                            "find_in_creator_projects_format": "{creator}: {projects}",
                        },
                        "pages": {
                            "creator_collaboration_project_subtitle_format": "together with {collaborator}",
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
            self.assertEqual(labels.controls.tag_actions_label_format.format(tag="Calm"), "Use Calm")
            self.assertEqual(labels.controls.find_in_creators_format.format(creators="artists"), "Browse artists")
            self.assertEqual(labels.controls.find_in_projects_format.format(projects="works"), "Browse works")
            self.assertEqual(
                labels.controls.find_in_creator_projects_format.format(creator="Ada", projects="works"),
                "Ada: works",
            )
            self.assertEqual(
                labels.pages.creator_collaboration_project_subtitle_format.format(
                    collaborator="Ada",
                ),
                "together with Ada",
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
            ("controls", "tag_actions_label_format", "Actions"),
            ("controls", "find_in_creators_format", "Find"),
            ("controls", "find_in_projects_format", "Find in {creators}"),
            ("controls", "find_in_creator_projects_format", "Find in {projects}"),
            ("pages", "creator_collaboration_project_subtitle_format", "{projects}"),
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
            film.pages.creator_collaboration_project_subtitle_format.format(
                collaborator="Ada",
            ),
            "with Ada",
        )
        self.assertEqual(
            model.pages.creator_collaboration_project_subtitle_format.format(
                collaborator="Ada",
            ),
            "with Ada",
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
