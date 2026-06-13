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
from cr4te.enums.visible_fields import CollaborationField, CreatorField, ProjectField
from cr4te.render_metadata import (
    build_collaboration_meta_entries,
    build_creator_meta_entries,
    build_project_creator_meta_entries,
    build_project_meta_entries,
)
from cr4te.schemas.library_schema import Creator, Project


def context_for(domain: Domain = Domain.ART, config_path: Path | None = None) -> HtmlBuildContext:
    config = apply_cli_overrides(load_config(config_path), domain=domain)
    return HtmlBuildContext(
        input_dir=Path("input"),
        output_dir=Path("output"),
        site_labels=config.site_labels,
        site_rendering=config.site_rendering,
    )


def project(**overrides) -> Project:
    data = {
        "title": "Landscapes",
        "display_title": "Displayed Landscapes",
        "release_date": "2024-03-12",
        "cover": "",
        "info": "",
        "tags": {},
        "facets": {},
        "media_groups": [],
    }
    data.update(overrides)
    return Project(**data)


def creator(**overrides) -> Creator:
    data = {
        "name": "Noomi",
        "display_name": "Displayed Noomi",
        "type": CreatorType.PERSON,
        "active_since": "2020",
        "date_of_birth": "1990-04",
        "place_of_birth": "Berlin",
        "portrait": "",
        "info": "",
        "nationalities": ["German"],
        "aliases": ["N."],
        "projects": [],
        "media_groups": [],
    }
    data.update(overrides)
    return Creator(**data)


class RenderMetadataTests(unittest.TestCase):
    def test_creator_meta_entries_use_field_specs(self):
        entries = build_creator_meta_entries(
            context_for(),
            creator(),
            [
                CreatorField.NAME,
                CreatorField.BIRTH,
                CreatorField.NATIONALITIES,
                CreatorField.ALIASES,
                CreatorField.DEBUT_AGE,
            ],
            "html/noomi.html",
            "index.html",
        )

        self.assertEqual([entry.label for entry in entries], ["Name", "Born", "Nationality", "Alias", "Debut Age"])
        self.assertEqual(entries[0].values, ["Displayed Noomi"])
        self.assertEqual(entries[0].hrefs, ["html/noomi.html"])
        self.assertEqual(entries[1].values, ["April 1990 in Berlin"])
        self.assertEqual(entries[2].hrefs, ["index.html?tag=Nationalities%3AGerman"])
        self.assertEqual(entries[3].separator, "<br>")
        self.assertEqual(entries[4].values, ["29 y.o."])

    def test_creator_event_entries_combine_visible_date_and_place(self):
        entries = build_creator_meta_entries(
            context_for(),
            creator(
                date_of_death="2024-03-12",
                place_of_death="Paris",
            ),
            [
                CreatorField.BIRTH,
                CreatorField.DEATH,
            ],
            "",
            "index.html",
        )

        self.assertEqual([entry.label for entry in entries], ["Born", "Died"])
        self.assertEqual(entries[0].values, ["April 1990 in Berlin"])
        self.assertEqual(entries[1].values, ["March 12, 2024 in Paris"])

    def test_creator_event_entries_fall_back_to_available_values(self):
        date_only = build_creator_meta_entries(
            context_for(),
            creator(place_of_birth=""),
            [CreatorField.BIRTH],
            "",
            "index.html",
        )
        place_only = build_creator_meta_entries(
            context_for(),
            creator(date_of_birth="", place_of_birth="Berlin"),
            [CreatorField.BIRTH],
            "",
            "index.html",
        )

        self.assertEqual(date_only[0].values, ["April 1990"])
        self.assertEqual(place_only[0].label, "Born")
        self.assertEqual(place_only[0].values, ["Berlin"])

    def test_creator_event_entries_use_configured_named_placeholder_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            config_path.write_text(
                '{"site_labels":{"metadata":{"date_and_place_format":"{place}, {date}"}}}',
                encoding="utf-8",
            )

            entries = build_creator_meta_entries(
                context_for(config_path=config_path),
                creator(),
                [CreatorField.BIRTH],
                "",
                "index.html",
            )

        self.assertEqual(entries[0].values, ["Berlin, April 1990"])

    def test_project_creator_meta_entries_can_use_project_date(self):
        entries = build_project_creator_meta_entries(
            context_for(),
            creator(),
            [CreatorField.AGE_AT_TIME],
            project(),
            "html/noomi.html",
            "index.html",
        )

        self.assertEqual(entries[0].label, "Age at Time")
        self.assertEqual(entries[0].values, ["33 y.o."])

    def test_collaboration_meta_entries_use_field_specs(self):
        collab = Creator(
            name="Noomi & Ada",
            display_name="The Duo",
            type=CreatorType.COLLABORATION,
            active_since="",
            members=["Noomi", "Ada"],
            founding_date="2021",
            founding_location="Paris",
            portrait="",
            info="",
            nationalities=["French", "German"],
            aliases=["NA"],
            projects=[],
            media_groups=[],
        )

        entries = build_collaboration_meta_entries(
            context_for(),
            collab,
            [
                CollaborationField.NAME,
                CollaborationField.NATIONALITIES,
                CollaborationField.ALIASES,
                CollaborationField.MEMBERS,
                CollaborationField.FOUNDING,
            ],
            "html/noomi-ada.html",
            "index.html",
            ["Displayed Noomi", "Ada"],
        )

        self.assertEqual([entry.label for entry in entries], ["Name", "Nationalities", "Alias", "Members", "Founded"])
        self.assertEqual(entries[0].hrefs, ["html/noomi-ada.html"])
        self.assertEqual(entries[0].values, ["The Duo"])
        self.assertEqual(entries[1].hrefs[0], "index.html?tag=Nationalities%3AFrench")
        self.assertEqual(entries[3].separator, "<br>")
        self.assertEqual(entries[3].values, ["Displayed Noomi", "Ada"])
        self.assertEqual(entries[4].values, ["2021 in Paris"])

    def test_project_meta_entries_use_core_and_facet_specs(self):
        entries = build_project_meta_entries(
            context_for(Domain.ART),
            project(facets={ProjectField.MEDIUMS: ["Photography"], ProjectField.PERIODS: ["Contemporary"]}),
        )

        labels = [entry.label for entry in entries]
        self.assertEqual(labels, ["Title", "Release Date", "Medium", "Period"])
        self.assertEqual(entries[0].values, ["Displayed Landscapes"])
        self.assertEqual(entries[1].values, ["March 12, 2024"])
        self.assertEqual(entries[2].hrefs, ["projects.html?tag=Mediums%3APhotography"])


if __name__ == "__main__":
    unittest.main()
