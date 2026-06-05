import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

ASSET_JS_DIR = ROOT / "src" / "cr4te" / "assets" / "js"
TEMPLATE_DIR = ROOT / "src" / "cr4te" / "templates"

LEGACY_GLOBAL_PATTERNS = (
    r"window\.toggleMute\b",
    r"window\.togglePlay\b",
    r"window\.playSelectedTrack\b",
    r"window\.stopAudio\b",
    r"window\.prevTrack\b",
    r"window\.nextTrack\b",
    r"window\.seekAudio\b",
    r"window\.setVolume\b",
    r"window\.playNextTrack\b",
    r"window\.toggleVideoPlay\b",
    r"window\.seekVideo\b",
    r"window\.setVideoVolume\b",
    r"window\.toggleFullscreen\b",
    r"window\.paginateGallery\b",
    r"window\.rebuildAspectImageGallery\b",
    r"window\.rebuildJustifiedImageGallery\b",
    r"window\.rebindLightbox\b",
    r"window\.rebindSingleLightbox\b",
)


def read_all(paths):
    return "\n".join(path.read_text(encoding="utf-8") for path in paths)


class JavaScriptContractTests(unittest.TestCase):
    def test_templates_do_not_use_inline_javascript_handlers(self):
        templates = sorted(TEMPLATE_DIR.rglob("*.j2"))
        source = read_all(templates)

        for handler in ("onclick=", "oninput=", "onchange="):
            with self.subTest(handler=handler):
                self.assertNotIn(handler, source)

    def test_media_templates_use_data_action_hooks(self):
        source = read_all(
            [
                TEMPLATE_DIR / "partials" / "_media_sections.html.j2",
                TEMPLATE_DIR / "partials" / "_video_player.html.j2",
            ]
        )

        for hook in ("data-audio-action", "data-video-action", "data-media-action"):
            with self.subTest(hook=hook):
                self.assertIn(hook, source)

    def test_only_utils_owns_dom_ready_listener(self):
        owners = []
        for path in sorted(ASSET_JS_DIR.glob("*.js")):
            if "DOMContentLoaded" in path.read_text(encoding="utf-8"):
                owners.append(path.name)

        self.assertEqual(owners, ["utils.js"])

    def test_feature_scripts_register_with_cr4te_on_ready(self):
        feature_scripts = [
            "aspect_gallery_builder.js",
            "audio_player.js",
            "image_captions_toggle.js",
            "justified_gallery_builder.js",
            "lightbox.js",
            "pagination.js",
            "responsive_content_mover.js",
            "search_filter.js",
            "theme_selector.js",
            "video_player.js",
        ]

        for script_name in feature_scripts:
            with self.subTest(script_name=script_name):
                source = (ASSET_JS_DIR / script_name).read_text(encoding="utf-8")
                self.assertIn("cr4te.onReady", source)

    def test_legacy_window_function_aliases_are_not_reintroduced(self):
        source = read_all(sorted(ASSET_JS_DIR.glob("*.js")))

        for pattern in LEGACY_GLOBAL_PATTERNS:
            with self.subTest(pattern=pattern):
                self.assertIsNone(re.search(pattern, source))

    def test_shared_media_helpers_are_used_by_audio_and_video_players(self):
        audio = (ASSET_JS_DIR / "audio_player.js").read_text(encoding="utf-8")
        video = (ASSET_JS_DIR / "video_player.js").read_text(encoding="utf-8")

        for source in (audio, video):
            self.assertIn("cr4te.media.updateProgress", source)
            self.assertIn("cr4te.media.bindSeekSlider", source)

    def test_templates_load_utils_before_cr4te_feature_scripts(self):
        script_pattern = re.compile(r'<script\s+src="[^"]*assets/js/([^"]+)"[^>]*></script>')
        cr4te_feature_scripts = {
            "aspect_gallery_builder.js",
            "audio_player.js",
            "image_captions_toggle.js",
            "justified_gallery_builder.js",
            "lightbox.js",
            "pagination.js",
            "responsive_content_mover.js",
            "search_filter.js",
            "theme_selector.js",
            "video_player.js",
        }

        for template in sorted(TEMPLATE_DIR.rglob("*.j2")):
            with self.subTest(template=template.relative_to(ROOT)):
                scripts = script_pattern.findall(template.read_text(encoding="utf-8"))
                feature_positions = [
                    index for index, script in enumerate(scripts) if script in cr4te_feature_scripts
                ]

                if feature_positions:
                    self.assertIn("utils.js", scripts)
                    utils_position = scripts.index("utils.js")
                    self.assertLess(utils_position, min(feature_positions))

    def test_search_filter_loads_after_pagination(self):
        script_pattern = re.compile(r'<script\s+src="[^"]*assets/js/([^"]+)"[^>]*></script>')

        for template_name in ("creator_overview.html.j2", "project_overview.html.j2"):
            with self.subTest(template_name=template_name):
                scripts = script_pattern.findall((TEMPLATE_DIR / template_name).read_text(encoding="utf-8"))

                self.assertLess(scripts.index("pagination.js"), scripts.index("search_filter.js"))

    def test_pagination_reuses_per_gallery_instance_and_can_remove_resize_listener(self):
        source = (ASSET_JS_DIR / "pagination.js").read_text(encoding="utf-8")

        self.assertIn("const instances = new WeakMap()", source)
        self.assertIn("instance.update(allWrappers, pageSize)", source)
        self.assertIn("window.addEventListener('resize', handleResize)", source)
        self.assertIn("window.removeEventListener('resize', handleResize)", source)

    def test_theme_selector_uses_rendered_registry_and_handles_restricted_storage(self):
        source = (ASSET_JS_DIR / "theme_selector.js").read_text(encoding="utf-8")

        self.assertIn("document.body.dataset.defaultTheme", source)
        self.assertIn("try {", source)
        self.assertNotIn('const DEFAULT_THEME', source)
        for theme_class in (
            "theme-amber-terminal",
            "theme-forest-night",
            "theme-frozen-aurora",
            "theme-mono-terminal",
        ):
            with self.subTest(theme_class=theme_class):
                self.assertNotIn(theme_class, source)

    def test_templates_do_not_hide_body_until_theme_javascript_runs(self):
        source = read_all(sorted(TEMPLATE_DIR.glob("*.j2")))

        self.assertNotIn("body { display: none; }", source)


if __name__ == "__main__":
    unittest.main()
