import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cr4te.config_manager import apply_cli_overrides, load_config
from cr4te.build_issues import IssueCode
from cr4te.html_context import HtmlBuildContext
from cr4te.enums.creator_type import CreatorType
from cr4te.enums.domain import Domain
from cr4te.enums.image_visibility import ImageVisibility
from cr4te.enums.thumb_type import ThumbType
from cr4te.enums.visible_fields import ProjectField
from cr4te.library_index import CreatorSummary, ProjectSummary
from cr4te.media_counts import MediaCounts
from cr4te.output_preparation import prepare_output_dirs
from cr4te.overview_contexts import build_project_overview_entry_from_index
from cr4te.page_contexts import (
    build_creator_page_context,
    build_project_page_context,
    compute_creator_stats,
)
from cr4te.render_assets import prepare_default_thumbnails, resolve_thumbnail_or_default
from cr4te.render_models import CreatorPageContext, ProjectCardContext, ProjectPageContext
from cr4te.schemas.library_schema import Creator, Project


def write_image(path: Path, size: tuple[int, int] = (120, 90)) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color=(120, 80, 160)).save(path)


def context_for(
    input_dir: Path,
    output_dir: Path,
    domain: Domain = Domain.ART,
    configure=None,
) -> HtmlBuildContext:
    config = apply_cli_overrides(load_config(), domain=domain)
    if configure:
        configure(config)
    ctx = HtmlBuildContext(input_dir, output_dir, config.site_labels, config.site_rendering)
    prepare_output_dirs(ctx)
    prepare_default_thumbnails(ctx)
    return ctx


def project(**overrides) -> Project:
    data = {
        "title": "Landscapes",
        "display_title": "Displayed Landscapes",
        "release_date": "2024-03-12",
        "cover": "Landscapes/cover.jpg",
        "info": "",
        "tags": {"Mood": ["Calm"]},
        "facets": {ProjectField.MEDIUMS: ["Photography"]},
        "media_groups": [],
    }
    data.update(overrides)
    return Project(**data)


def person(name: str = "Noomi", **overrides) -> Creator:
    data = {
        "name": name,
        "display_name": name,
        "type": CreatorType.PERSON,
        "active_since": "2020",
        "date_of_birth": "1990-04",
        "place_of_birth": "Berlin",
        "portrait": f"{name}/portrait.jpg",
        "info": "",
        "nationalities": ["German"],
        "aliases": ["N."],
        "tags": {"Role": ["Photographer"]},
        "projects": [],
        "media_groups": [],
    }
    data.update(overrides)
    return Creator(**data)


class PageContextTests(unittest.TestCase):
    def test_creator_page_profile_image_flag_omits_thumbnail_work(self):
        """Covers SITE-015."""
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp) / "input"
            output_dir = Path(tmp) / "site"
            creator = person(portrait="Noomi/portrait.jpg")
            ctx = context_for(
                input_dir,
                output_dir,
                configure=lambda config: setattr(
                    config.site_rendering.creator_page,
                    "show_profile_image",
                    ImageVisibility.HIDE,
                ),
            )

            with (
                patch("cr4te.page_contexts.build_source_thumbnail_context") as build_source_thumbnail,
                patch("cr4te.page_contexts.build_thumbnail_context") as build_thumbnail,
            ):
                page = build_creator_page_context(ctx, creator, lambda name: None, compute_creator_stats(creator))

            build_source_thumbnail.assert_not_called()
            build_thumbnail.assert_not_called()
            self.assertEqual(page.rel_portrait_path, "")
            self.assertIsNone(page.portrait_orientation)

    def test_if_available_detail_profile_images_use_source_thumbnails_only(self):
        """Covers SITE-015 and SITE-028."""
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp) / "input"
            output_dir = Path(tmp) / "site"
            write_image(input_dir / "Noomi" / "portrait.jpg", (80, 160))
            ctx = context_for(
                input_dir,
                output_dir,
                configure=lambda config: setattr(
                    config.site_rendering.creator_page,
                    "show_profile_image",
                    ImageVisibility.IF_AVAILABLE,
                ),
            )

            discovered_page = build_creator_page_context(
                ctx,
                person(portrait="Noomi/portrait.jpg"),
                lambda name: None,
                compute_creator_stats(person()),
            )
            missing_page = build_creator_page_context(
                ctx,
                person(name="Ada", portrait=""),
                lambda name: None,
                compute_creator_stats(person(name="Ada", portrait="")),
            )

            self.assertTrue(discovered_page.rel_portrait_path)
            self.assertEqual(missing_page.rel_portrait_path, "")
            self.assertIsNone(missing_page.portrait_orientation)
            self.assertEqual(ctx.asset_statistics.default_thumbnail_uses, 0)

    def test_show_detail_profile_image_uses_default_when_source_is_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp) / "input"
            output_dir = Path(tmp) / "site"
            creator = person(portrait="Noomi/missing.jpg")
            ctx = context_for(input_dir, output_dir)

            page = build_creator_page_context(ctx, creator, lambda name: None, compute_creator_stats(creator))

            self.assertEqual(page.rel_portrait_path, "assets/defaults/portrait.png")
            self.assertIsNotNone(page.portrait_orientation)
            self.assertEqual(ctx.asset_statistics.default_thumbnail_uses, 1)
            self.assertEqual(len(ctx.issues), 1)
            self.assertEqual(ctx.issues[0].code, IssueCode.MISSING_MEDIA)

    def test_if_available_detail_profile_image_omits_missing_source_without_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp) / "input"
            output_dir = Path(tmp) / "site"
            creator = person(portrait="Noomi/missing.jpg")
            ctx = context_for(
                input_dir,
                output_dir,
                configure=lambda config: setattr(
                    config.site_rendering.creator_page,
                    "show_profile_image",
                    ImageVisibility.IF_AVAILABLE,
                ),
            )

            page = build_creator_page_context(ctx, creator, lambda name: None, compute_creator_stats(creator))

            self.assertEqual(page.rel_portrait_path, "")
            self.assertIsNone(page.portrait_orientation)
            self.assertEqual(ctx.asset_statistics.default_thumbnail_uses, 0)
            self.assertEqual(len(ctx.issues), 1)
            self.assertEqual(ctx.issues[0].code, IssueCode.MISSING_MEDIA)

    def test_show_creator_page_profile_image_uses_default_for_empty_discovery(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp) / "input"
            output_dir = Path(tmp) / "site"
            creator = person(portrait="")
            ctx = context_for(input_dir, output_dir)

            page = build_creator_page_context(ctx, creator, lambda name: None, compute_creator_stats(creator))

            self.assertEqual(page.rel_portrait_path, "assets/defaults/portrait.png")
            self.assertIsNotNone(page.portrait_orientation)
            self.assertEqual(ctx.asset_statistics.default_thumbnail_uses, 1)

    def test_if_available_creator_page_profile_image_omits_empty_discovery(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp) / "input"
            output_dir = Path(tmp) / "site"
            creator = person(portrait="")
            ctx = context_for(
                input_dir,
                output_dir,
                configure=lambda config: setattr(
                    config.site_rendering.creator_page,
                    "show_profile_image",
                    ImageVisibility.IF_AVAILABLE,
                ),
            )

            page = build_creator_page_context(ctx, creator, lambda name: None, compute_creator_stats(creator))

            self.assertEqual(page.rel_portrait_path, "")
            self.assertIsNone(page.portrait_orientation)

    def test_project_page_image_flags_are_independent(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp) / "input"
            output_dir = Path(tmp) / "site"
            write_image(input_dir / "Noomi" / "portrait.jpg", (80, 160))
            write_image(input_dir / "Collab" / "portrait.jpg", (80, 160))
            write_image(input_dir / "Landscapes" / "cover.jpg")

            def configure(config):
                config.site_rendering.project_page.show_cover_image = ImageVisibility.HIDE
                config.site_rendering.project_page.show_creator_profile_image = ImageVisibility.HIDE
                config.site_rendering.project_page.show_collaboration_profile_image = ImageVisibility.HIDE
                config.site_rendering.project_page.show_participant_profile_images = ImageVisibility.SHOW

            member = person(display_name="Displayed Noomi", portrait="Noomi/portrait.jpg")
            collab_project = project()
            collaboration = Creator(
                name="Noomi & Ada",
                display_name="The Duo",
                type=CreatorType.COLLABORATION,
                active_since="2021",
                members=["Noomi"],
                portrait="Collab/portrait.jpg",
                info="",
                projects=[collab_project],
                media_groups=[],
            )
            ctx = context_for(input_dir, output_dir, configure=configure)

            collaboration_page = build_project_page_context(
                ctx,
                collaboration,
                collab_project,
                lambda name: member if name == "Noomi" else None,
            )
            creator_page = build_project_page_context(ctx, member, collab_project, lambda name: None)

            self.assertEqual(collaboration_page.rel_thumbnail_path, "")
            self.assertIsNone(collaboration_page.thumbnail_orientation)
            self.assertEqual(collaboration_page.collaboration.rel_portrait_path, "")
            self.assertTrue(collaboration_page.participants[0].rel_portrait_path)
            self.assertEqual(creator_page.creator.rel_portrait_path, "")

    def test_creator_page_context_uses_typed_project_cards_and_tags(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp) / "input"
            output_dir = Path(tmp) / "site"
            write_image(input_dir / "Noomi" / "portrait.jpg", (80, 160))
            write_image(input_dir / "Landscapes" / "cover.jpg")

            creator = person(portrait="Noomi/portrait.jpg", projects=[project()])
            ctx = context_for(input_dir, output_dir)

            page = build_creator_page_context(ctx, creator, lambda name: None, compute_creator_stats(creator))

            self.assertIsInstance(page, CreatorPageContext)
            self.assertEqual(page.name, "Noomi")
            self.assertEqual(page.tags.as_dict()["Mediums"], ["Photography"])
            self.assertIsInstance(page.projects[0], ProjectCardContext)
            self.assertEqual(page.projects[0].title, "Displayed Landscapes")
            self.assertEqual(page.projects[0].media_counts.values(), (0, 0, 0, 0, 0))

    def test_show_creator_page_uses_default_for_unreadable_cached_portrait_thumbnail(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp) / "input"
            output_dir = Path(tmp) / "site"
            write_image(input_dir / "Noomi" / "portrait.jpg", (80, 160))
            creator = person(portrait="Noomi/portrait.jpg")
            ctx = context_for(input_dir, output_dir)
            thumb_path = resolve_thumbnail_or_default(ctx, creator.portrait, ThumbType.PORTRAIT)
            thumb_path.write_bytes(b"not an image")

            page = build_creator_page_context(ctx, creator, lambda name: None, compute_creator_stats(creator))

            self.assertEqual(page.rel_portrait_path, "assets/defaults/portrait.png")
            self.assertEqual(ctx.asset_statistics.default_thumbnail_uses, 1)
            self.assertEqual(len(ctx.issues), 1)
            self.assertEqual(ctx.issues[0].code, IssueCode.MEDIA_INSPECTION_FAILURE)

    def test_if_available_creator_page_omits_unreadable_cached_portrait_thumbnail(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp) / "input"
            output_dir = Path(tmp) / "site"
            write_image(input_dir / "Noomi" / "portrait.jpg", (80, 160))
            creator = person(portrait="Noomi/portrait.jpg")
            ctx = context_for(
                input_dir,
                output_dir,
                configure=lambda config: setattr(
                    config.site_rendering.creator_page,
                    "show_profile_image",
                    ImageVisibility.IF_AVAILABLE,
                ),
            )
            thumb_path = resolve_thumbnail_or_default(ctx, creator.portrait, ThumbType.PORTRAIT)
            thumb_path.write_bytes(b"not an image")

            page = build_creator_page_context(ctx, creator, lambda name: None, compute_creator_stats(creator))

            self.assertEqual(page.rel_portrait_path, "")
            self.assertEqual(ctx.asset_statistics.default_thumbnail_uses, 0)
            self.assertEqual(len(ctx.issues), 1)
            self.assertEqual(ctx.issues[0].code, IssueCode.MEDIA_INSPECTION_FAILURE)

    def test_collaboration_creator_page_context_uses_typed_contexts(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp) / "input"
            output_dir = Path(tmp) / "site"
            write_image(input_dir / "Collab" / "portrait.jpg", (80, 160))
            write_image(input_dir / "Noomi" / "portrait.jpg", (80, 160))

            member = person(display_name="Displayed Noomi", portrait="Noomi/portrait.jpg")
            collaboration = Creator(
                name="Noomi & Ada",
                display_name="The Duo",
                type=CreatorType.COLLABORATION,
                active_since="2021",
                members=["Noomi", "Missing Member"],
                portrait="Collab/portrait.jpg",
                info="",
                tags={"Format": ["Duo"]},
                projects=[],
                media_groups=[],
            )
            ctx = context_for(input_dir, output_dir)

            page = build_creator_page_context(
                ctx,
                collaboration,
                lambda name: member if name == "Noomi" else None,
                compute_creator_stats(collaboration),
            )

            self.assertIsInstance(page, CreatorPageContext)
            self.assertEqual(page.type, CreatorType.COLLABORATION.value)
            self.assertEqual(page.tags.as_dict()["Format"], ["Duo"])
            self.assertEqual(page.name, "The Duo")
            self.assertEqual([member.name for member in page.members], ["Displayed Noomi"])
            self.assertEqual([entry.label for entry in page.members[0].meta_entries], ["Name"])
            self.assertEqual(page.members[0].meta_entries[0].values, ["Displayed Noomi"])
            self.assertTrue(page.members[0].meta_entries[0].hrefs[0].endswith(".html"))
            members_entry = next(entry for entry in page.meta_entries if entry.label == "Members")
            self.assertEqual(members_entry.values, ["Displayed Noomi", "Missing Member"])
            self.assertEqual([entry.label for entry in page.meta_entries], ["Name", "Active Since", "Members"])

    def test_project_page_context_splits_collaboration_and_participants(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp) / "input"
            output_dir = Path(tmp) / "site"
            write_image(input_dir / "Noomi" / "portrait.jpg", (80, 160))
            write_image(input_dir / "Collab" / "portrait.jpg", (80, 160))
            write_image(input_dir / "Landscapes" / "cover.jpg")

            member = person(display_name="Displayed Noomi", portrait="Noomi/portrait.jpg")
            collab_project = project()
            collaboration = Creator(
                name="Noomi & Ada",
                display_name="The Duo",
                type=CreatorType.COLLABORATION,
                active_since="2021",
                members=["Noomi"],
                portrait="Collab/portrait.jpg",
                info="",
                projects=[collab_project],
                media_groups=[],
            )
            ctx = context_for(input_dir, output_dir)

            page = build_project_page_context(ctx, collaboration, collab_project, lambda name: member if name == "Noomi" else None)

            self.assertIsInstance(page, ProjectPageContext)
            self.assertIsNone(page.creator)
            self.assertEqual(page.title, "Displayed Landscapes")
            self.assertEqual(page.collaboration.name, "The Duo")
            self.assertEqual([participant.name for participant in page.participants], ["Displayed Noomi"])
            self.assertEqual(page.tags.as_dict()["Mood"], ["Calm"])

    def test_collaboration_section_label_resolves_member_display_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp) / "input"
            output_dir = Path(tmp) / "site"
            creator = person(name="Ada", display_name="Displayed Ada", portrait="", collaborations=["Ada & Bob"])
            other_member = person(name="Bob", display_name="Displayed Bob", portrait="")
            collaboration = Creator(
                name="Ada & Bob",
                display_name="The Pair",
                type=CreatorType.COLLABORATION,
                active_since="",
                members=["Ada", "Bob", "Missing Member"],
                portrait="",
                info="",
                projects=[],
                media_groups=[],
            )
            creators = {
                other_member.name: other_member,
                collaboration.name: collaboration,
            }
            ctx = context_for(input_dir, output_dir)

            page = build_creator_page_context(
                ctx,
                creator,
                creators.get,
                compute_creator_stats(creator),
            )

            self.assertEqual(page.collaborations[0].label, "Displayed Bob & Missing Member")

    def test_collaboration_label_uses_single_name_when_there_are_no_other_members(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp) / "input"
            output_dir = Path(tmp) / "site"
            creator = person(name="Ada", display_name="Displayed Creator Ada", portrait="", collaborations=["Ada"])
            collaboration = Creator(
                name="Ada",
                display_name="Displayed Collaboration Ada",
                type=CreatorType.COLLABORATION,
                active_since="",
                members=["Ada"],
                portrait="",
                info="",
                projects=[],
                media_groups=[],
            )
            ctx = context_for(input_dir, output_dir)

            page = build_creator_page_context(
                ctx,
                creator,
                lambda name: collaboration if name == collaboration.name else None,
                compute_creator_stats(creator),
            )

            self.assertEqual(page.collaborations[0].label, "Displayed Collaboration Ada")

    def test_collaboration_label_uses_comma_and_ampersand_for_multiple_members(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp) / "input"
            output_dir = Path(tmp) / "site"
            creator = person(name="Ada", display_name="Displayed Ada", portrait="", collaborations=["Ada & Bob & Charlie & Dana"])
            bob = person(name="Bob", display_name="Displayed Bob", portrait="")
            charlie = person(name="Charlie", display_name="Displayed Charlie", portrait="")
            dana = person(name="Dana", display_name="Displayed Dana", portrait="")
            collaboration = Creator(
                name="Ada & Bob & Charlie & Dana",
                display_name="The Quartet",
                type=CreatorType.COLLABORATION,
                active_since="",
                members=["Ada", "Bob", "Charlie", "Dana"],
                portrait="",
                info="",
                projects=[],
                media_groups=[],
            )
            creators = {
                bob.name: bob,
                charlie.name: charlie,
                dana.name: dana,
                collaboration.name: collaboration,
            }
            ctx = context_for(input_dir, output_dir)

            page = build_creator_page_context(
                ctx,
                creator,
                creators.get,
                compute_creator_stats(creator),
            )

            self.assertEqual(page.collaborations[0].label, "Displayed Bob, Displayed Charlie & Displayed Dana")

    def test_missing_collaboration_reference_is_reported_as_structured_issue(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp) / "input"
            output_dir = Path(tmp) / "site"
            creator = person(name="Ada", portrait="", collaborations=["Missing Collaboration"])
            ctx = context_for(input_dir, output_dir)

            page = build_creator_page_context(
                ctx,
                creator,
                lambda name: None,
                compute_creator_stats(creator),
            )

            self.assertEqual(page.collaborations, [])
            self.assertEqual(len(ctx.issues), 1)
            self.assertEqual(ctx.issues[0].code, IssueCode.INVALID_COLLABORATION_REFERENCE)

    def test_project_summary_search_uses_enum_facet_keys_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp) / "input"
            output_dir = Path(tmp) / "site"
            ctx = context_for(input_dir, output_dir)
            creator = CreatorSummary(
                path=input_dir / "Noomi",
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
            )
            summary = ProjectSummary(
                title="Landscapes",
                display_title="Displayed Landscapes",
                release_date="",
                cover="",
                tags={},
                facets={ProjectField.MEDIUMS: ["Photography"], "materials": ["String Key"]},
                media_counts=MediaCounts(),
            )

            entry = build_project_overview_entry_from_index(ctx, creator, summary)

            self.assertIn("mediums:photography", entry.search_text)
            self.assertNotIn("materials:string key", entry.search_text)


if __name__ == "__main__":
    unittest.main()
