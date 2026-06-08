import sys
import tempfile
import unittest
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
from cr4te.render_models import (
    CreatorProfileContext,
    DocumentContext,
    GalleryImageContext,
    MediaGroupContext,
    MediaSectionContext,
    NavigationItem,
    PageShellContext,
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


def context_for(input_dir: Path, output_dir: Path) -> HtmlBuildContext:
    config = apply_cli_overrides(load_config(), domain=Domain.ART)
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


class TemplateRendererTests(unittest.TestCase):
    def test_gallery_class_macro_supports_justified_strategy(self):
        macro = env.get_template("partials/_utils.html.j2").module.get_image_gallery_class

        rendered = macro(ImageGalleryBuildingStrategy, ImageGalleryBuildingStrategy.JUSTIFIED)

        self.assertEqual(rendered.strip(), "image-gallery--justified")

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

    def test_overview_template_renders_registry_stylesheets_and_visible_default_body(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = context_for(Path(tmp) / "input", Path(tmp) / "site")
            rendered = env.get_template("creator_overview.html.j2").render(
                site_labels=ctx.site_labels,
                site_rendering=ctx.site_rendering,
                creator_entries=[],
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

            self.assertIn('<body class="theme-frozen-aurora" data-default-theme="theme-frozen-aurora">', rendered)
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
            self.assertIn('aria-haspopup="menu"', rendered)
            self.assertIn('role="menuitemradio"', rendered)
            self.assertNotIn("body { display: none; }", rendered)

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
                self.assertIn('{% include "partials/_document_head.html.j2" %}', source)
                self.assertIn('{% include "partials/_page_header.html.j2" %}', source)
                self.assertNotIn('<div class="page-header">', source)


if __name__ == "__main__":
    unittest.main()
