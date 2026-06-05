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
from cr4te.render_models import ProjectPageContext, TagCollection
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
            )

            self.assertIn('<body class="theme-frozen-aurora" data-default-theme="theme-frozen-aurora">', rendered)
            self.assertIn('assets/css/themes/frozen-aurora.css', rendered)
            self.assertIn('data-theme="theme-forest-night"', rendered)
            self.assertNotIn("body { display: none; }", rendered)


if __name__ == "__main__":
    unittest.main()
