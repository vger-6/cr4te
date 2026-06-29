import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

ASSET_JS_DIR = ROOT / "src" / "cr4te" / "assets" / "js"
ASSET_CSS_DIR = ROOT / "src" / "cr4te" / "assets" / "css"
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

    def test_interactive_template_controls_use_native_elements(self):
        creator_source = (TEMPLATE_DIR / "creator.html.j2").read_text(encoding="utf-8")
        media_source = (TEMPLATE_DIR / "partials" / "_media_sections.html.j2").read_text(encoding="utf-8")
        project_source = (TEMPLATE_DIR / "project.html.j2").read_text(encoding="utf-8")
        search_source = (TEMPLATE_DIR / "partials" / "_search_bar.html.j2").read_text(encoding="utf-8")
        theme_source = (TEMPLATE_DIR / "partials" / "_theme_dropdown.html.j2").read_text(encoding="utf-8")

        self.assertIn('data-expandable-text-toggle', creator_source)
        self.assertIn('data-expandable-text-toggle', project_source)
        self.assertIn('<button type="button"', media_source)
        self.assertIn('data-audio-action="select-track"', media_source)
        self.assertIn('<button type="button" id="clear-search"', search_source)
        self.assertIn('role="menu"', theme_source)
        self.assertIn('role="menuitemradio"', theme_source)

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
            "expandable_text.js",
            "image_captions_toggle.js",
            "justified_gallery_builder.js",
            "lightbox.js",
            "overflow_tooltips.js",
            "pagination.js",
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

    def test_playback_coordinator_uses_captured_native_media_events_and_only_pauses(self):
        source = (ASSET_JS_DIR / "playback_coordinator.js").read_text(encoding="utf-8")

        self.assertIn('document.addEventListener("play"', source)
        self.assertIn('document.addEventListener("pause"', source)
        self.assertIn('document.addEventListener("ended"', source)
        self.assertIn("activeMedia.pause()", source)
        self.assertNotIn("currentTime", source)
        self.assertNotIn("removeAttribute", source)
        self.assertNotIn(".load()", source)

    def test_detail_pages_load_playback_coordinator_after_utils(self):
        script_pattern = re.compile(r'<script\s+src="[^"]*assets/js/([^"]+)"[^>]*></script>')

        for template_name in ("creator.html.j2", "project.html.j2"):
            with self.subTest(template_name=template_name):
                scripts = script_pattern.findall((TEMPLATE_DIR / template_name).read_text(encoding="utf-8"))

                self.assertIn("playback_coordinator.js", scripts)
                self.assertLess(scripts.index("utils.js"), scripts.index("playback_coordinator.js"))

    def test_templates_load_utils_before_cr4te_feature_scripts(self):
        script_pattern = re.compile(r'<script\s+src="[^"]*assets/js/([^"]+)"[^>]*></script>')
        cr4te_feature_scripts = {
            "aspect_gallery_builder.js",
            "audio_player.js",
            "expandable_text.js",
            "image_captions_toggle.js",
            "justified_gallery_builder.js",
            "lightbox.js",
            "overflow_tooltips.js",
            "pagination.js",
            "playback_coordinator.js",
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

    def test_overflow_tooltips_are_added_only_for_overflowing_items(self):
        source = (ASSET_JS_DIR / "overflow_tooltips.js").read_text(encoding="utf-8")

        for selector in (
            ".breadcrumb-section [data-overflow-title]",
            ".section-title",
            ".tag-category-label",
            ".tag",
            ".track-title-text",
            ".image-caption",
            ".creator-text-card__name",
            ".creator-text-card__summary",
        ):
            with self.subTest(selector=selector):
                self.assertIn(f'"{selector}"', source)
        self.assertIn("function sectionTitleTextElement", source)
        self.assertIn("function normalizedText", source)
        self.assertIn("element.classList.contains(\"section-title\")", source)
        self.assertIn("measured.scrollWidth > measured.clientWidth", source)
        self.assertIn("measured.scrollHeight > measured.clientHeight", source)
        self.assertIn('measured.setAttribute("title", title)', source)
        self.assertIn('measured.removeAttribute("title")', source)
        self.assertIn("ResizeObserver", source)
        self.assertIn("window.cr4te.overflowTooltips.resizeObserver = observer", source)
        self.assertIn("window.addEventListener(\"resize\", updateTooltips)", source)
        self.assertIn("document.fonts.ready.then(updateTooltips)", source)
        self.assertIn("cr4te.onReady(initOverflowTooltips)", source)

    def test_expandable_text_collapses_only_overflowing_detail_prose(self):
        source = (ASSET_JS_DIR / "expandable_text.js").read_text(encoding="utf-8")
        base = (ASSET_CSS_DIR / "base.css").read_text(encoding="utf-8")

        self.assertIn('const SELECTOR = "[data-expandable-text]"', source)
        self.assertIn("[data-expandable-text-content]", source)
        self.assertIn("[data-expandable-text-toggle]", source)
        self.assertIn("content.scrollHeight > content.clientHeight", source)
        self.assertIn("button.hidden = !isCollapsible", source)
        self.assertIn('button.setAttribute("aria-expanded"', source)
        self.assertIn("button.dataset.showMoreLabel", source)
        self.assertIn("button.dataset.showLessLabel", source)
        self.assertIn("ResizeObserver", source)
        self.assertIn("document.fonts.ready.then(updateAllExpandableText)", source)
        self.assertIn("cr4te.onReady(initExpandableText)", source)
        self.assertRegex(
            base,
            r"\.expandable-text\.is-collapsible\.is-collapsed \.expandable-text__content\s*\{[^}]*"
            r"-webkit-line-clamp:\s*var\(--expandable-text-current-lines\)",
        )
        self.assertRegex(base, r"\.expandable-text__content\s*\{[^}]*hyphens:\s*auto")
        self.assertRegex(base, r"\.expandable-text__content\s*\{[^}]*overflow-wrap:\s*break-word")
        self.assertRegex(base, r"@media \(max-width:\s*48rem\)\s*\{[\s\S]*--expandable-text-current-lines")

    def test_pagination_reuses_per_gallery_instance_and_can_remove_resize_listener(self):
        source = (ASSET_JS_DIR / "pagination.js").read_text(encoding="utf-8")

        self.assertIn("const instances = new WeakMap()", source)
        self.assertIn("instance.update(allWrappers, pageSize)", source)
        self.assertIn("window.addEventListener('resize', handleResize)", source)
        self.assertIn("window.removeEventListener('resize', handleResize)", source)

    def test_aspect_gallery_and_pagination_use_shared_defensive_aspect_ratio_parser(self):
        utils = (ASSET_JS_DIR / "utils.js").read_text(encoding="utf-8")
        aspect_gallery = (ASSET_JS_DIR / "aspect_gallery_builder.js").read_text(encoding="utf-8")
        pagination = (ASSET_JS_DIR / "pagination.js").read_text(encoding="utf-8")

        self.assertIn("window.utils.parseAspectRatio = function", utils)
        self.assertIn("window.utils.parseAspectRatio(gallery.dataset.aspectRatio)", aspect_gallery)
        self.assertIn("window.utils.parseAspectRatio(gallery.dataset.aspectRatio)", pagination)
        self.assertNotIn("function parseAspectRatio", aspect_gallery)
        self.assertNotIn("aspectRatio.split('/')", pagination)

    def test_pagination_auto_scroll_respects_reduced_motion_preference(self):
        source = (ASSET_JS_DIR / "pagination.js").read_text(encoding="utf-8")

        self.assertIn("window.utils.prefersReducedMotion()", source)
        self.assertIn("behavior: window.utils.prefersReducedMotion() ? 'auto' : 'smooth'", source)

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

    def test_caption_toggle_handles_restricted_storage(self):
        source = (ASSET_JS_DIR / "image_captions_toggle.js").read_text(encoding="utf-8")

        self.assertIn("try {", source)
        self.assertIn("localStorage.getItem", source)
        self.assertIn("localStorage.setItem", source)

    def test_toggle_scripts_expose_pressed_state(self):
        caption_source = (ASSET_JS_DIR / "image_captions_toggle.js").read_text(encoding="utf-8")
        utils_source = (ASSET_JS_DIR / "utils.js").read_text(encoding="utf-8")

        self.assertIn('setAttribute("aria-pressed"', caption_source)
        self.assertIn("setAttribute('aria-pressed'", utils_source)

    def test_theme_selector_supports_keyboard_menu_navigation(self):
        source = (ASSET_JS_DIR / "theme_selector.js").read_text(encoding="utf-8")

        for key in ("ArrowDown", "ArrowUp", "Home", "End", "Escape"):
            with self.subTest(key=key):
                self.assertIn(key, source)
        self.assertIn("aria-expanded", source)
        self.assertIn("aria-checked", source)

    def test_media_players_support_scoped_keyboard_shortcuts(self):
        audio_source = (ASSET_JS_DIR / "audio_player.js").read_text(encoding="utf-8")
        video_source = (ASSET_JS_DIR / "video_player.js").read_text(encoding="utf-8")

        for key in ("ArrowDown", "ArrowUp", "Home", "End"):
            with self.subTest(player="audio", key=key):
                self.assertIn(key, audio_source)
        for key in ("Space", "Enter"):
            with self.subTest(player="video", key=key):
                self.assertIn(key, video_source)

    def test_shared_focus_tokens_and_focus_visible_styles_are_defined(self):
        tokens = (ASSET_CSS_DIR / "tokens.css").read_text(encoding="utf-8")
        base = (ASSET_CSS_DIR / "base.css").read_text(encoding="utf-8")

        self.assertIn("--theme-focus-outline:", tokens)
        self.assertIn("--theme-focus-outline-width:", tokens)
        self.assertIn("--theme-slider-focus-ring:", tokens)
        self.assertIn(":focus-visible", base)
        self.assertRegex(
            base,
            r"\.media-slider:focus-visible\s*\{[^}]*"
            r"box-shadow:\s*0 0 0 var\(--theme-focus-outline-width\) var\(--theme-slider-focus-ring\)",
        )

    def test_shared_design_tokens_cover_motion_metadata_icons_and_scrollbars(self):
        tokens = (ASSET_CSS_DIR / "tokens.css").read_text(encoding="utf-8")

        for token in (
            "--space-xs:",
            "--space-sm:",
            "--space-md:",
            "--icon-size:",
            "--icon-size-compact:",
            "--motion-interaction:",
            "--motion-visibility:",
            "--meta-label-value-gap:",
            "--meta-entry-gap:",
            "--data-label-size:",
            "--scrollbar-width:",
            "--scrollbar-radius:",
            "--scrollbar-border-width:",
        ):
            with self.subTest(token=token):
                self.assertIn(token, tokens)

        self.assertNotIn("--layout-mobile-breakpoint:", tokens)

    def test_typography_tokens_keep_content_first_hierarchy(self):
        """Covers SITE-026 by protecting shared typography-token ownership."""
        tokens = (ASSET_CSS_DIR / "tokens.css").read_text(encoding="utf-8")
        base = (ASSET_CSS_DIR / "base.css").read_text(encoding="utf-8")

        for token in (
            "--type-body-size",
            "--type-section-title-size",
            "--type-markdown-heading-size",
            "--type-label-size",
            "--type-prose-line-height",
        ):
            with self.subTest(token=token):
                self.assertRegex(tokens, rf"{token}:\s*[^;]+;")

        self.assertNotRegex(tokens, r"--type-h[1-6]-size:")
        self.assertNotIn("--type-page-title-size", tokens)
        self.assertNotRegex(base, r"\.page-title\s*\{")
        self.assertRegex(base, r"\.section-title\s*\{[^}]*font-size:\s*var\(--type-section-title-size\)")
        self.assertRegex(base, r"\.section-title\s*\{[^}]*text-overflow:\s*ellipsis")
        self.assertRegex(base, r"\.section-title\s*\{[^}]*white-space:\s*nowrap")
        self.assertRegex(base, r"\.track-title-text\s*\{[^}]*text-overflow:\s*ellipsis")
        self.assertRegex(base, r"\.tag\s*\{[^}]*text-overflow:\s*ellipsis")
        self.assertRegex(base, r"\.creator-text-card__name,\s*[\s\S]*?\.creator-text-card__summary\s*\{[^}]*-webkit-line-clamp:\s*2")
        self.assertRegex(base, r"\.image-caption\s*\{[^}]*-webkit-line-clamp:\s*2")
        self.assertNotRegex(base, r"\.meta-value\s*\{[^}]*text-overflow:\s*ellipsis")
        self.assertRegex(
            base,
            r"\.markdown :is\(h1, h2, h3, h4, h5, h6\)\s*\{[^}]*"
            r"font-size:\s*var\(--type-markdown-heading-size\)",
        )

    def test_layout_tokens_define_search_and_content_spacing(self):
        """Covers SITE-025 and SITE-027 by protecting shared layout-token ownership."""
        tokens = (ASSET_CSS_DIR / "tokens.css").read_text(encoding="utf-8")
        base = (ASSET_CSS_DIR / "base.css").read_text(encoding="utf-8")

        for token in (
            "--layout-navigation-padding-block",
            "--layout-navigation-padding-inline",
            "--layout-content-padding-top",
            "--layout-content-padding-bottom",
            "--layout-content-padding-inline",
            "--layout-search-height",
            "--layout-gallery-gap",
            "--layout-card-gap",
            "--theme-section-content-padding-top",
        ):
            with self.subTest(token=token):
                self.assertRegex(tokens, rf"{token}:\s*[^;]+;")

        for token in (
            "--layout-body-padding-top",
            "--layout-body-padding-bottom",
            "--layout-body-padding-inline",
            "--layout-title-search-height",
            "--theme-title-bg",
            "--theme-title-text",
            "--theme-title-border",
            "--theme-title-border-width",
            "--theme-title-margin",
            "--theme-title-radius",
        ):
            with self.subTest(stale_token=token):
                self.assertNotIn(token, tokens)

        self.assertRegex(
            base,
            r"\.page-content\s*\{[^}]*padding:\s*var\(--layout-content-padding-top\)"
            r" var\(--layout-content-padding-inline\)[^;]*var\(--layout-content-padding-bottom\)",
        )
        self.assertNotRegex(base, r"\.page-title\s*\{")
        self.assertRegex(base, r"\.search-box\s*\{[^}]*height:\s*var\(--layout-search-height\)")
        self.assertRegex(base, r"\.image-gallery--aspect\s*\{[^}]*gap:\s*var\(--layout-gallery-gap\)")
        self.assertRegex(base, r"\.image-gallery--justified\s*\{[^}]*gap:\s*var\(--layout-gallery-gap\)")
        self.assertRegex(base, r"\.card-gallery\s*\{[^}]*gap:\s*var\(--layout-card-gap\)")

    def test_public_theme_tokens_cover_navigation_pagination_and_track_separators(self):
        """Covers THEME-008."""
        tokens = (ASSET_CSS_DIR / "tokens.css").read_text(encoding="utf-8")
        base = (ASSET_CSS_DIR / "base.css").read_text(encoding="utf-8")
        forest = (ROOT / "src" / "cr4te" / "assets" / "themes" / "forest-night.css").read_text(encoding="utf-8")
        frozen = (ROOT / "src" / "cr4te" / "assets" / "themes" / "frozen-aurora.css").read_text(encoding="utf-8")

        for token in (
            "--theme-navigation-bg",
            "--theme-navigation-border",
            "--theme-navigation-border-width",
            "--theme-pagination-button-radius",
            "--theme-track-separator",
            "--theme-track-separator-width",
        ):
            with self.subTest(token=token):
                self.assertRegex(tokens, rf"{token}:\s*[^;]+;")

        self.assertRegex(tokens, r"--theme-pagination-button-radius:\s*0;")
        self.assertRegex(tokens, r"--theme-track-separator-width:\s*0;")
        self.assertIn("background-color: var(--theme-navigation-bg)", base)
        self.assertIn("border-radius: var(--theme-pagination-button-radius)", base)
        self.assertIn(
            "border-bottom: var(--theme-track-separator-width) solid var(--theme-track-separator)",
            base,
        )
        self.assertRegex(forest, r"--theme-pagination-button-radius:\s*[^;]+;")
        self.assertRegex(forest, r"--theme-track-bg-odd:\s*transparent;")
        self.assertRegex(forest, r"--theme-track-bg-even:\s*transparent;")
        self.assertNotIn("--theme-track-separator:", forest)
        self.assertNotIn("--theme-track-separator-width:", forest)
        self.assertRegex(frozen, r"--theme-pagination-button-radius:\s*[^;]+;")

    def test_css_transitions_use_shared_motion_tokens_and_explicit_properties(self):
        source = read_all(sorted(ASSET_CSS_DIR.glob("*.css")))

        self.assertNotRegex(source, r"transition:\s*all\b")
        self.assertNotRegex(source, r"transition:[^;]*(?:0\.2s|0\.3s)")
        self.assertIn("transition: opacity var(--motion-visibility)", source)
        self.assertIn("transition: color var(--motion-interaction)", source)

    def test_css_reduced_motion_preference_disables_shared_motion_tokens(self):
        tokens = (ASSET_CSS_DIR / "tokens.css").read_text(encoding="utf-8")

        self.assertIn("@media (prefers-reduced-motion: reduce)", tokens)
        self.assertRegex(
            tokens,
            r"@media \(prefers-reduced-motion: reduce\)\s*\{\s*:root\s*\{[^}]*"
            r"--motion-interaction:\s*0s !important;[^}]*--motion-visibility:\s*0s !important;",
        )

    def test_scrollbar_styles_are_shared_by_base_css(self):
        base = (ASSET_CSS_DIR / "base.css").read_text(encoding="utf-8")
        overview = (ASSET_CSS_DIR / "overview-layout.css").read_text(encoding="utf-8")
        two_column = (ASSET_CSS_DIR / "two-column-layout.css").read_text(encoding="utf-8")

        self.assertIn(".overview-layout::-webkit-scrollbar,", base)
        self.assertIn(".detail-content::-webkit-scrollbar", base)
        self.assertIn("width: var(--scrollbar-width)", base)
        self.assertNotIn("::-webkit-scrollbar", overview)
        self.assertNotIn("::-webkit-scrollbar", two_column)

    def test_base_css_does_not_import_separately_linked_tokens(self):
        source = (ASSET_CSS_DIR / "base.css").read_text(encoding="utf-8")

        self.assertNotIn('@import url("tokens.css")', source)

    def test_templates_do_not_hide_body_until_theme_javascript_runs(self):
        source = read_all(sorted(TEMPLATE_DIR.glob("*.j2")))

        self.assertNotIn("body { display: none; }", source)

    def test_detail_pages_do_not_move_responsive_content_with_javascript(self):
        for template_name in ("creator.html.j2", "project.html.j2"):
            with self.subTest(template_name=template_name):
                source = (TEMPLATE_DIR / template_name).read_text(encoding="utf-8")

                self.assertNotIn("responsive_content_mover.js", source)
                self.assertNotIn("original-placeholder", source)
                self.assertNotIn("mobile-placeholder", source)
                self.assertLess(source.index('class="left-column"'), source.index('class="right-column"'))

        self.assertFalse((ASSET_JS_DIR / "responsive_content_mover.js").exists())

    def test_lightbox_uses_modal_dialog_semantics_and_native_controls(self):
        source = (ASSET_JS_DIR / "lightbox.js").read_text(encoding="utf-8")

        self.assertIn("overlay.setAttribute('role', 'dialog')", source)
        self.assertIn("overlay.setAttribute('aria-modal', 'true')", source)
        self.assertIn("overlay.tabIndex = -1", source)
        self.assertIn("document.createElement('button')", source)
        self.assertNotIn("document.createElement('div');\n    closeBtn.id = 'lightbox-close'", source)
        self.assertIn("previouslyFocusedElement", source)
        self.assertIn("event.key === 'Tab'", source)
        self.assertIn("elements.overlay.focus()", source)


if __name__ == "__main__":
    unittest.main()
