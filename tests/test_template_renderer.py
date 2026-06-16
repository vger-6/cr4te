import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cr4te.config_manager import apply_cli_overrides, load_config
from cr4te.html_context import HtmlBuildContext
from cr4te.enums.creator_type import CreatorType
from cr4te.enums.domain import Domain
from cr4te.enums.image_gallery_building_strategy import ImageGalleryBuildingStrategy
from cr4te.enums.orientation import Orientation
from cr4te.enums.portrait_visibility import PortraitVisibility
from cr4te.media_counts import MediaCounts
from cr4te.render_models import (
    CollaborationProjectsContext,
    CreatorOverviewEntry,
    CreatorPageContext,
    CreatorProfileContext,
    CreatorStats,
    DocumentContext,
    GalleryImageContext,
    MediaGroupContext,
    MediaSectionContext,
    MetaEntry,
    NavigationItem,
    PageShellContext,
    ProjectCardContext,
    ProjectOverviewEntry,
    ProjectPageContext,
    TagCollection,
    TrackContext,
    VideoContext,
)
from cr4te.enums.media_type import MediaType
from cr4te.schemas.library_schema import Creator, Project
from cr4te.template_renderer import env, render_project_page, render_tags_page


class FakeTemplate:
    def __init__(self, name: str, calls: list[tuple[str, dict]]):
        self.name = name
        self.calls = calls

    def render(self, **kwargs) -> str:
        self.calls.append((self.name, kwargs))
        return f"rendered:{self.name}"


class FakeEnvironment:
    def __init__(self):
        self.calls: list[tuple[str, dict]] = []

    def get_template(self, name: str) -> FakeTemplate:
        return FakeTemplate(name, self.calls)


def context_for(
    input_dir: Path,
    output_dir: Path,
    portrait_visibility: PortraitVisibility = PortraitVisibility.ALL,
) -> HtmlBuildContext:
    config = apply_cli_overrides(
        load_config(),
        domain=Domain.ART,
        portrait_visibility=portrait_visibility,
    )
    return HtmlBuildContext(input_dir, output_dir, config.site_labels, config.site_rendering)


def creator() -> Creator:
    return Creator(
        name="Noomi",
        display_name="Displayed Noomi",
        type=CreatorType.PERSON,
        active_since="2020",
        portrait="",
        info="",
        projects=[],
        media_groups=[],
    )


def project() -> Project:
    return Project(
        title="Landscapes",
        display_title="Displayed Landscapes",
        release_date="",
        cover="",
        info="",
        tags={},
        facets={},
        media_groups=[],
    )


def project_card() -> ProjectCardContext:
    return ProjectCardContext(
        title="Displayed Landscapes",
        rel_html_path="html/landscapes.html",
        rel_thumbnail_path="thumb.jpg",
        image_wrapper_width=120,
        image_wrapper_height=80,
        media_counts=MediaCounts(image=1),
    )


def overview_shell(ctx: HtmlBuildContext, title: str) -> PageShellContext:
    return PageShellContext(
        title=title,
        layout_stylesheet="overview-layout.css",
        navigation_items=(
            NavigationItem(
                ctx.site_labels.entity.creators,
                "index.html",
                current=title == ctx.site_labels.entity.creators,
            ),
            NavigationItem(
                ctx.site_labels.entity.projects,
                "projects.html",
                current=title == ctx.site_labels.entity.projects,
            ),
            NavigationItem(ctx.site_labels.entity.tags, "tags.html", current=title == ctx.site_labels.entity.tags),
        ),
    )


class TemplateRendererTests(unittest.TestCase):
    def test_non_all_portrait_overview_renders_text_card_without_image_or_badges(self):
        with tempfile.TemporaryDirectory() as tmp:
            entry = CreatorOverviewEntry(
                name="Displayed Noomi",
                rel_html_path="html/noomi.html",
                search_text="displayed noomi",
                rel_thumbnail_path="",
                image_wrapper_width=0,
                image_wrapper_height=0,
                project_count=1,
                media_counts=MediaCounts(image=2),
                project_count_summary="1 work",
                media_count_summary="2 images",
            )

            for visibility in (PortraitVisibility.DISABLED, PortraitVisibility.DETAILS):
                with self.subTest(visibility=visibility):
                    ctx = context_for(Path(tmp) / "input", Path(tmp) / "site", visibility)
                    render_data = {
                        "site_labels": ctx.site_labels,
                        "site_rendering": ctx.site_rendering,
                        "gallery_image_max_height": 450,
                        "ImageGalleryBuildingStrategy": ImageGalleryBuildingStrategy,
                        "themes": ctx.themes,
                        "default_theme": ctx.default_theme,
                        "page_shell": PageShellContext(
                            title=ctx.site_labels.entity.creators,
                            layout_stylesheet="overview-layout.css",
                            navigation_items=(
                                NavigationItem(ctx.site_labels.entity.creators, "index.html", current=True),
                            ),
                        ),
                    }

                    rendered = env.get_template("creator_overview.html.j2").render(
                        creator_entries=[entry],
                        **render_data,
                    )

                    self.assertIn('class="creator-card-grid"', rendered)
                    self.assertIn('class="image-wrapper image-card creator-text-card"', rendered)
                    self.assertIn('class="creator-text-card__summary creator-text-card__project-summary">1 work</small>', rendered)
                    self.assertIn('class="creator-text-card__summary creator-text-card__media-summary">2 images</small>', rendered)
                    self.assertNotIn("1 work | 2 images", rendered)
                    self.assertNotIn('class="card-image"', rendered)
                    self.assertNotIn("media-type-badges", rendered)

                    empty_summary_rendered = env.get_template("creator_overview.html.j2").render(
                        creator_entries=[replace(entry, project_count_summary="", media_count_summary="")],
                        **render_data,
                    )
                    self.assertNotIn("creator-text-card__counts", empty_summary_rendered)

                    project_only_rendered = env.get_template("creator_overview.html.j2").render(
                        creator_entries=[replace(entry, media_count_summary="")],
                        **render_data,
                    )
                    self.assertIn("creator-text-card__project-summary", project_only_rendered)
                    self.assertNotIn("creator-text-card__media-summary", project_only_rendered)

                    media_only_rendered = env.get_template("creator_overview.html.j2").render(
                        creator_entries=[replace(entry, project_count_summary="")],
                        **render_data,
                    )
                    self.assertNotIn("creator-text-card__project-summary", media_only_rendered)
                    self.assertIn("creator-text-card__media-summary", media_only_rendered)

    def test_enabled_portrait_overview_preserves_image_card_and_badges(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = context_for(Path(tmp) / "input", Path(tmp) / "site")
            entry = CreatorOverviewEntry(
                name="Displayed Noomi",
                rel_html_path="html/noomi.html",
                search_text="displayed noomi",
                rel_thumbnail_path="thumb.jpg",
                image_wrapper_width=80,
                image_wrapper_height=160,
                project_count=1,
                media_counts=MediaCounts(image=2),
                project_count_summary="1 work",
                media_count_summary="2 images",
            )

            rendered = env.get_template("creator_overview.html.j2").render(
                site_labels=ctx.site_labels,
                site_rendering=ctx.site_rendering,
                creator_entries=[entry],
                gallery_image_max_height=450,
                ImageGalleryBuildingStrategy=ImageGalleryBuildingStrategy,
                themes=ctx.themes,
                default_theme=ctx.default_theme,
                page_shell=PageShellContext(
                    title=ctx.site_labels.entity.creators,
                    layout_stylesheet="overview-layout.css",
                    navigation_items=(NavigationItem(ctx.site_labels.entity.creators, "index.html", current=True),),
                ),
            )

            self.assertIn('class="card-image"', rendered)
            self.assertIn('alt="Thumbnail for Displayed Noomi"', rendered)
            self.assertIn("media-type-badges", rendered)
            self.assertIn('title="1 work"', rendered)
            self.assertIn('aria-label="1 work"', rendered)
            self.assertNotIn('title="1 Work"', rendered)
            self.assertNotIn("creator-text-card", rendered)

    def test_empty_overview_templates_render_static_empty_state_without_search_or_cards(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = context_for(Path(tmp) / "input", Path(tmp) / "site")

            creator_rendered = env.get_template("creator_overview.html.j2").render(
                site_labels=ctx.site_labels,
                site_rendering=ctx.site_rendering,
                creator_entries=[],
                gallery_image_max_height=450,
                ImageGalleryBuildingStrategy=ImageGalleryBuildingStrategy,
                themes=ctx.themes,
                default_theme=ctx.default_theme,
                page_shell=overview_shell(ctx, ctx.site_labels.entity.creators),
            )

            self.assertIn("No Artists available", creator_rendered)
            self.assertIn('class="empty-state"', creator_rendered)
            self.assertNotIn('id="search-input"', creator_rendered)
            self.assertNotIn('id="imageGallery"', creator_rendered)
            self.assertNotIn("image-card", creator_rendered)

            project_rendered = env.get_template("project_overview.html.j2").render(
                site_labels=ctx.site_labels,
                site_rendering=ctx.site_rendering,
                projects=[],
                gallery_image_max_height=450,
                ImageGalleryBuildingStrategy=ImageGalleryBuildingStrategy,
                themes=ctx.themes,
                default_theme=ctx.default_theme,
                page_shell=overview_shell(ctx, ctx.site_labels.entity.projects),
            )

            self.assertIn("No Works available", project_rendered)
            self.assertIn('class="empty-state"', project_rendered)
            self.assertNotIn('id="search-input"', project_rendered)
            self.assertNotIn('id="imageGallery"', project_rendered)
            self.assertNotIn("image-card", project_rendered)

    def test_populated_overview_templates_render_hidden_dynamic_search_empty_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = context_for(Path(tmp) / "input", Path(tmp) / "site")
            creator_entry = CreatorOverviewEntry(
                name="Displayed Noomi",
                rel_html_path="html/noomi.html",
                search_text="displayed noomi",
                rel_thumbnail_path="thumb.jpg",
                image_wrapper_width=80,
                image_wrapper_height=160,
                project_count=1,
                media_counts=MediaCounts(image=2),
                project_count_summary="1 work",
                media_count_summary="2 images",
            )
            project_entry = ProjectOverviewEntry(
                title="Displayed Landscapes",
                rel_html_path="html/landscapes.html",
                rel_thumbnail_path="thumb.jpg",
                image_wrapper_width=120,
                image_wrapper_height=80,
                creator_name="Displayed Noomi",
                search_text="displayed landscapes",
                media_counts=MediaCounts(image=1),
            )

            creator_rendered = env.get_template("creator_overview.html.j2").render(
                site_labels=ctx.site_labels,
                site_rendering=ctx.site_rendering,
                creator_entries=[creator_entry],
                gallery_image_max_height=450,
                ImageGalleryBuildingStrategy=ImageGalleryBuildingStrategy,
                themes=ctx.themes,
                default_theme=ctx.default_theme,
                page_shell=overview_shell(ctx, ctx.site_labels.entity.creators),
            )
            project_rendered = env.get_template("project_overview.html.j2").render(
                site_labels=ctx.site_labels,
                site_rendering=ctx.site_rendering,
                projects=[project_entry],
                gallery_image_max_height=450,
                ImageGalleryBuildingStrategy=ImageGalleryBuildingStrategy,
                themes=ctx.themes,
                default_theme=ctx.default_theme,
                page_shell=overview_shell(ctx, ctx.site_labels.entity.projects),
            )

            for rendered in (creator_rendered, project_rendered):
                with self.subTest():
                    self.assertIn('id="search-input"', rendered)
                    self.assertIn('id="imageGallery"', rendered)
                    self.assertIn(
                        '<div class="empty-state empty-state--search" role="status" aria-live="polite" hidden>',
                        rendered,
                    )
                    self.assertIn("No results match your search", rendered)
                    self.assertNotIn("No Artists available", rendered)
                    self.assertNotIn("No Works available", rendered)

    def test_gallery_class_macro_supports_justified_strategy(self):
        macro = env.get_template("partials/_utils.html.j2").module.get_image_gallery_class

        rendered = macro(ImageGalleryBuildingStrategy, ImageGalleryBuildingStrategy.JUSTIFIED)

        self.assertEqual(rendered.strip(), "image-gallery--justified")

    def test_metadata_macro_renders_grouped_stacked_entries_without_colons(self):
        macro = env.get_template("partials/_utils.html.j2").module.render_meta_entries
        entries = [
            MetaEntry(
                label="Genres",
                values=["Ambient", "Electronic"],
                separator=" | ",
                hrefs=["projects.html?tag=Genres%3AAmbient", ""],
            ),
            MetaEntry(label="Release Date", values=["2001"]),
        ]

        rendered = str(macro(entries, "../"))

        self.assertIn('<dl class="meta-list info-block__meta">', rendered)
        self.assertEqual(rendered.count('<div class="meta-entry">'), 2)
        self.assertIn('<dt class="meta-label data-label">Genres</dt>', rendered)
        self.assertIn('<dd class="meta-value">', rendered)
        self.assertIn('<a href="../projects.html?tag=Genres%3AAmbient">Ambient</a> | Electronic', rendered)
        self.assertNotIn("Genres:", rendered)
        self.assertNotIn("Release Date:", rendered)

    def test_gallery_image_alt_text_uses_available_image_metadata(self):
        site_labels = load_config().site_labels
        macro = env.get_template("partials/_media_sections.html.j2").module.render_media_groups
        group = MediaGroupContext(
            audio_section_title="Audio",
            image_section_title="Gallery",
            sections=[
                MediaSectionContext(
                    type=MediaType.IMAGE,
                    images=[
                        GalleryImageContext(
                            rel_thumbnail_path="thumb.jpg",
                            image_wrapper_width=120,
                            image_wrapper_height=80,
                            rel_path="photo.jpg",
                            caption="Sunset over water",
                        )
                    ],
                )
            ],
        )

        rendered = str(macro("", [group], 450, 24, site_labels))

        self.assertIn('alt="Sunset over water"', rendered)
        self.assertNotIn('alt="Image for "', rendered)

    def test_video_source_does_not_claim_an_incorrect_media_type(self):
        site_labels = load_config().site_labels
        macro = env.get_template("partials/_media_sections.html.j2").module.render_media_groups
        group = MediaGroupContext(
            audio_section_title="Audio",
            image_section_title="Gallery",
            sections=[
                MediaSectionContext(
                    type=MediaType.VIDEO,
                    videos=[VideoContext(rel_path="clip.webm", title="Clip")],
                )
            ],
        )

        rendered = str(macro("", [group], 450, 24, site_labels))

        self.assertIn('<source src="clip.webm">', rendered)
        self.assertIn('<video preload="metadata" tabindex="0" aria-label="Clip"', rendered)
        self.assertNotIn('type="video/mp4"', rendered)

    def test_media_controls_render_native_semantics_and_accessible_names(self):
        site_labels = load_config().site_labels
        macro = env.get_template("partials/_media_sections.html.j2").module.render_media_groups
        group = MediaGroupContext(
            audio_section_title="Audio",
            image_section_title="Gallery",
            sections=[
                MediaSectionContext(
                    type=MediaType.AUDIO,
                    tracks=[TrackContext(rel_path="song.mp3", title="Song", duration_seconds=10)],
                ),
                MediaSectionContext(
                    type=MediaType.IMAGE,
                    images=[
                        GalleryImageContext(
                            rel_thumbnail_path="thumb.jpg",
                            image_wrapper_width=120,
                            image_wrapper_height=80,
                            rel_path="photo.jpg",
                            caption="Photo",
                        )
                    ],
                ),
                MediaSectionContext(
                    type=MediaType.DOCUMENT,
                    documents=[DocumentContext(rel_path="book.pdf", title="Book")],
                ),
            ],
        )

        rendered = str(macro("", [group], 450, 24, site_labels))

        self.assertIn('<button type="button"', rendered)
        self.assertIn('data-audio-action="select-track"', rendered)
        self.assertIn('data-audio-action="select-track"\n                        class="track-title"\n                        tabindex="0"', rendered)
        self.assertIn('aria-label="Seek"', rendered)
        self.assertIn('aria-label="Volume"', rendered)
        self.assertIn('aria-pressed="false"', rendered)
        self.assertIn('<iframe class="auto-height-iframe" title="Book"', rendered)

    def test_project_page_renderer_writes_unique_html_path_and_common_template_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = context_for(Path(tmp) / "input", Path(tmp) / "site")
            fake_env = FakeEnvironment()
            page_context = ProjectPageContext(
                title="Landscapes",
                release_date="",
                meta_entries=[],
                rel_thumbnail_path="",
                thumbnail_orientation=Orientation.LANDSCAPE,
                info_html="",
                tags=TagCollection(),
                media_groups=[],
                creator=CreatorProfileContext(
                    name="Displayed Noomi",
                    rel_html_path="creator.html",
                    rel_portrait_path="",
                ),
            )

            custom_rel_path = Path("custom") / "depth" / "project.html"
            with (
                patch("cr4te.template_renderer.env", fake_env),
                patch("cr4te.template_renderer.build_rel_project_html_path", return_value=custom_rel_path),
            ):
                render_project_page(ctx, creator(), project(), page_context)

            rendered_path = next(ctx.html_dir.rglob("*.html"))
            self.assertEqual(rendered_path, ctx.html_dir / custom_rel_path)
            self.assertEqual(rendered_path.read_text(encoding="utf-8"), "rendered:project.html.j2")
            self.assertEqual(fake_env.calls[0][0], "project.html.j2")
            self.assertIs(fake_env.calls[0][1]["project"], page_context)
            self.assertEqual(fake_env.calls[0][1]["path_to_root"], "../../../")
            page_shell = fake_env.calls[0][1]["page_shell"]
            self.assertEqual(page_shell.title, "Landscapes")
            self.assertEqual(page_shell.layout_stylesheet, "two-column-layout.css")
            self.assertEqual(
                [(item.label, item.href, item.current) for item in page_shell.navigation_items],
                [
                    (ctx.site_labels.entity.creators, "../../../index.html", False),
                    (ctx.site_labels.entity.projects, "../../../projects.html", False),
                    (ctx.site_labels.entity.tags, "../../../tags.html", False),
                    ("Displayed Noomi", "../../../creator.html", False),
                ],
            )
            self.assertEqual(fake_env.calls[0][1]["default_theme"].id, "frozen-aurora")
            self.assertEqual({theme.id for theme in fake_env.calls[0][1]["themes"]}, {
                "forest-night",
                "frozen-aurora",
                "mono-terminal",
            })

    def test_tags_renderer_merges_tag_maps_at_boundary(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = context_for(Path(tmp) / "input", Path(tmp) / "site")
            ctx.output_dir.mkdir(parents=True)
            fake_env = FakeEnvironment()

            with patch("cr4te.template_renderer.env", fake_env):
                render_tags_page(ctx, {"Theme": ["Night", "Night"], "": ["ignored"]})

            self.assertEqual(ctx.tags_html_path.read_text(encoding="utf-8"), "rendered:tags.html.j2")
            self.assertEqual(fake_env.calls[0][0], "tags.html.j2")
            self.assertEqual(fake_env.calls[0][1]["tags"].as_dict(), {"Theme": ["Night"]})
            page_shell = fake_env.calls[0][1]["page_shell"]
            self.assertEqual(page_shell.layout_stylesheet, "overview-layout.css")
            self.assertEqual([item.current for item in page_shell.navigation_items], [False, False, True])

    def test_empty_tags_template_renders_static_empty_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = context_for(Path(tmp) / "input", Path(tmp) / "site")

            rendered = env.get_template("tags.html.j2").render(
                site_labels=ctx.site_labels,
                site_rendering=ctx.site_rendering,
                tags=TagCollection(),
                themes=ctx.themes,
                default_theme=ctx.default_theme,
                page_shell=overview_shell(ctx, ctx.site_labels.entity.tags),
            )

            self.assertIn("No Tags available", rendered)
            self.assertIn('class="empty-state"', rendered)
            self.assertNotIn("tag-list", rendered)
            self.assertNotIn("tag-category", rendered)

    def test_overview_template_renders_registry_stylesheets_and_visible_default_body(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = context_for(Path(tmp) / "input", Path(tmp) / "site")
            entry = CreatorOverviewEntry(
                name="Displayed Noomi",
                rel_html_path="html/noomi.html",
                search_text="displayed noomi",
                rel_thumbnail_path="thumb.jpg",
                image_wrapper_width=80,
                image_wrapper_height=160,
                project_count=1,
                media_counts=MediaCounts(image=2),
                project_count_summary="1 work",
                media_count_summary="2 images",
            )
            rendered = env.get_template("creator_overview.html.j2").render(
                site_labels=ctx.site_labels,
                site_rendering=ctx.site_rendering,
                creator_entries=[entry],
                gallery_image_max_height=450,
                ImageGalleryBuildingStrategy=ImageGalleryBuildingStrategy,
                themes=ctx.themes,
                default_theme=ctx.default_theme,
                page_shell=PageShellContext(
                    title=ctx.site_labels.entity.creators,
                    layout_stylesheet="overview-layout.css",
                    navigation_items=(
                        NavigationItem(ctx.site_labels.entity.creators, "index.html", current=True),
                        NavigationItem(ctx.site_labels.entity.projects, "projects.html"),
                        NavigationItem(ctx.site_labels.entity.tags, "tags.html"),
                    ),
                ),
            )

            self.assertIn('class="theme-frozen-aurora"', rendered)
            self.assertIn('data-default-theme="theme-frozen-aurora"', rendered)
            self.assertIn('data-theme-classes="', rendered)
            self.assertIn('theme-forest-night', rendered)
            self.assertIn('theme-mono-terminal', rendered)
            self.assertIn('<body data-default-theme="theme-frozen-aurora">', rendered)
            self.assertLess(rendered.index("assets/js/theme_bootstrap.js"), rendered.index("assets/css/tokens.css"))
            self.assertIn('assets/css/themes/frozen-aurora.css', rendered)
            self.assertIn('data-theme="theme-forest-night"', rendered)
            self.assertIn('<nav class="top-link" aria-label="Primary">', rendered)
            self.assertIn('class="site-logo-link"', rendered)
            self.assertIn('<div class="breadcrumb-list">', rendered)
            self.assertIn('class="breadcrumb-separator" aria-hidden="true"', rendered)
            self.assertIn('<div class="theme-dropdown-container">', rendered)
            self.assertIn('href="index.html"\n       aria-label="cr4te Artists overview"', rendered)
            self.assertIn('src="assets/favicon.svg"\n           alt=""\n           width="24"\n           height="24"', rendered)
            self.assertIn('<span class="nav-current" aria-current="page">Artists</span>', rendered)
            self.assertIn('<button type="button" id="clear-search"', rendered)
            self.assertIn('placeholder="Search Artists, Works, Tags..."', rendered)
            self.assertIn('aria-haspopup="menu"', rendered)
            self.assertIn('role="menuitemradio"', rendered)
            self.assertNotIn("body { display: none; }", rendered)

    def test_detail_templates_render_region_empty_states_only_when_whole_region_is_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = context_for(Path(tmp) / "input", Path(tmp) / "site")
            creator_page = CreatorPageContext(
                type=CreatorType.PERSON.value,
                name="Noomi",
                rel_portrait_path="",
                portrait_orientation=None,
                info_html="",
                tags=TagCollection(),
                projects=[],
                media_groups=[],
                collaborations=[],
                creator_stats=CreatorStats(project_count=0, media_counts=MediaCounts()),
                meta_entries=[],
            )
            creator_render_data = {
                "site_labels": ctx.site_labels,
                "site_rendering": ctx.site_rendering,
                "project_image_max_height": 450,
                "gallery_image_max_height": 450,
                "ImageGalleryBuildingStrategy": ImageGalleryBuildingStrategy,
                "themes": ctx.themes,
                "default_theme": ctx.default_theme,
                "path_to_root": "../",
                "page_shell": PageShellContext(
                    title=creator_page.name,
                    layout_stylesheet="two-column-layout.css",
                    navigation_items=(NavigationItem(ctx.site_labels.entity.creators, "../index.html"),),
                ),
            }

            creator_empty = env.get_template("creator.html.j2").render(
                creator=creator_page,
                **creator_render_data,
            )
            creator_with_project = env.get_template("creator.html.j2").render(
                creator=replace(creator_page, projects=[project_card()]),
                **creator_render_data,
            )
            creator_with_empty_collaboration = env.get_template("creator.html.j2").render(
                creator=replace(
                    creator_page,
                    collaborations=[CollaborationProjectsContext(label="Ada", projects=[])],
                ),
                **creator_render_data,
            )
            empty_media_group = MediaGroupContext(
                audio_section_title="Audio",
                image_section_title="Images",
                sections=[MediaSectionContext(type=MediaType.IMAGE)],
            )
            creator_with_empty_media_group = env.get_template("creator.html.j2").render(
                creator=replace(creator_page, media_groups=[empty_media_group]),
                **creator_render_data,
            )

            self.assertIn("No Works or media available", creator_empty)
            self.assertNotIn("No Works or media available", creator_with_project)
            self.assertIn("No Works or media available", creator_with_empty_collaboration)
            self.assertNotIn('<div class="section-title">Works with Ada</div>', creator_with_empty_collaboration)
            self.assertIn("No Works or media available", creator_with_empty_media_group)

            project_page = ProjectPageContext(
                title="Landscapes",
                release_date="",
                meta_entries=[],
                rel_thumbnail_path="cover.jpg",
                thumbnail_orientation=Orientation.LANDSCAPE,
                info_html="",
                tags=TagCollection(),
                media_groups=[],
                creator=CreatorProfileContext(
                    name="Displayed Noomi",
                    rel_html_path="creator.html",
                    rel_portrait_path="",
                ),
            )
            project_render_data = {
                "site_labels": ctx.site_labels,
                "site_rendering": ctx.site_rendering,
                "gallery_image_max_height": 450,
                "themes": ctx.themes,
                "default_theme": ctx.default_theme,
                "path_to_root": "../",
                "page_shell": PageShellContext(
                    title=project_page.title,
                    layout_stylesheet="two-column-layout.css",
                    navigation_items=(NavigationItem(ctx.site_labels.entity.creators, "../index.html"),),
                ),
            }
            media_group = MediaGroupContext(
                audio_section_title="Audio",
                image_section_title="Images",
                sections=[
                    MediaSectionContext(
                        type=MediaType.AUDIO,
                        tracks=[TrackContext(rel_path="song.mp3", title="Song", duration_seconds=10)],
                    )
                ],
            )

            project_empty = env.get_template("project.html.j2").render(
                project=project_page,
                **project_render_data,
            )
            project_with_empty_media_group = env.get_template("project.html.j2").render(
                project=replace(project_page, media_groups=[empty_media_group]),
                **project_render_data,
            )
            project_with_media = env.get_template("project.html.j2").render(
                project=replace(project_page, media_groups=[media_group]),
                **project_render_data,
            )

            self.assertIn("No media available", project_empty)
            self.assertIn("No media available", project_with_empty_media_group)
            self.assertNotIn("No media available", project_with_media)
            self.assertIn("audio-gallery", project_with_media)

    def test_creator_template_resolves_domain_specific_collaboration_title_format(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = apply_cli_overrides(load_config(), domain=Domain.FILM)
            ctx = HtmlBuildContext(Path(tmp) / "input", Path(tmp) / "site", config.site_labels, config.site_rendering)
            page = CreatorPageContext(
                type=CreatorType.PERSON.value,
                name="Noomi",
                rel_portrait_path="",
                portrait_orientation=None,
                info_html="",
                tags=TagCollection(),
                projects=[],
                media_groups=[],
                collaborations=[CollaborationProjectsContext(label="Ada", projects=[project_card()])],
                creator_stats=CreatorStats(project_count=0, media_counts=MediaCounts()),
                meta_entries=[],
            )

            rendered = env.get_template("creator.html.j2").render(
                site_labels=ctx.site_labels,
                site_rendering=ctx.site_rendering,
                creator=page,
                project_image_max_height=450,
                gallery_image_max_height=450,
                ImageGalleryBuildingStrategy=ImageGalleryBuildingStrategy,
                themes=ctx.themes,
                default_theme=ctx.default_theme,
                path_to_root="../",
                page_shell=PageShellContext(
                    title=page.name,
                    layout_stylesheet="two-column-layout.css",
                    navigation_items=(NavigationItem(ctx.site_labels.entity.creators, "../index.html"),),
                ),
            )

            self.assertIn('<div class="section-title">Codirected with Ada</div>', rendered)
            self.assertNotIn("Movies with Ada", rendered)

    def test_page_templates_use_shared_document_head_and_page_header(self):
        template_dir = ROOT / "src" / "cr4te" / "templates"

        for template_name in (
            "creator.html.j2",
            "creator_overview.html.j2",
            "project.html.j2",
            "project_overview.html.j2",
            "tags.html.j2",
        ):
            with self.subTest(template_name=template_name):
                source = (template_dir / template_name).read_text(encoding="utf-8")
                self.assertIn('{% include "partials/_document_open.html.j2" %}', source)
                self.assertIn('{% include "partials/_document_head.html.j2" %}', source)
                self.assertIn('{% include "partials/_page_header.html.j2" %}', source)
                self.assertNotIn('<html lang="en">', source)
                self.assertNotIn('<div class="page-header">', source)

    def test_detail_templates_use_shared_metadata_renderer_and_shared_tag_label_style(self):
        template_dir = ROOT / "src" / "cr4te" / "templates"
        creator_source = (template_dir / "creator.html.j2").read_text(encoding="utf-8")
        project_source = (template_dir / "project.html.j2").read_text(encoding="utf-8")
        tags_source = (template_dir / "tags.html.j2").read_text(encoding="utf-8")

        self.assertIn("utils.render_meta_entries(member.meta_entries, path_to_root)", creator_source)
        self.assertIn("creator_collaboration_projects_title_format | format_phrase", creator_source)
        self.assertNotIn("site_labels.entity.projects }} with {{ collab.label", creator_source)
        self.assertNotIn('<div class="info-block__meta">', creator_source)
        for source in (creator_source, project_source, tags_source):
            self.assertIn('<span class="tag-category-label data-label">{{ group.category }}</span>', source)
            self.assertNotIn("<strong>{{ group.category }}:</strong>", source)


if __name__ == "__main__":
    unittest.main()
