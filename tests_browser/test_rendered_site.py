import functools
import http.server
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

try:
    from playwright.sync_api import Error as PlaywrightError
    from playwright.sync_api import sync_playwright
except ImportError:
    PlaywrightError = None
    sync_playwright = None


@unittest.skipIf(sync_playwright is None, "Playwright is not installed; see info/TODO.md for browser test setup.")
class RenderedSiteBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.input_dir = Path(cls._tmp.name) / "Musicians"
        shutil.copytree(ROOT / "data" / "example" / "Musicians", cls.input_dir)
        cls.themes_dir = Path(cls._tmp.name) / "themes"
        shutil.copytree(ROOT / "data" / "example" / "themes", cls.themes_dir)
        custom_theme = cls.themes_dir / "custom-night.css"
        custom_theme.write_text(
            ".theme-custom-night { --theme-page-bg: rgb(1, 2, 3); --theme-text: rgb(245, 245, 245); }",
            encoding="utf-8",
        )
        cls.site_dir = Path(cls._tmp.name) / "site"
        cls.paginated_site_dir = Path(cls._tmp.name) / "paginated-site"
        cls._build_example_site(cls.site_dir)
        cls._build_example_site(cls.paginated_site_dir, cls._write_paginated_config(), domain=None)
        cls.audio_project_path = cls._find_audio_project_page()
        cls._start_static_server()
        cls._start_browser()

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "browser"):
            cls.browser.close()
        if hasattr(cls, "playwright"):
            cls.playwright.stop()
        if hasattr(cls, "server"):
            cls.server.shutdown()
            cls.server.server_close()
        if hasattr(cls, "server_thread"):
            cls.server_thread.join(timeout=5)
        if hasattr(cls, "_tmp"):
            cls._tmp.cleanup()

    @classmethod
    def _build_example_site(cls, site_dir: Path, config_path: Path | None = None, domain: str | None = "music"):
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT / "src")
        command = [
            sys.executable,
            "-m",
            "cr4te.cr4te",
            "build",
            "-i",
            str(cls.input_dir),
            "-o",
            str(site_dir),
            "--force",
            "--themes-dir",
            str(cls.themes_dir),
        ]
        if domain:
            command.extend(["--domain", domain])
        if config_path:
            command.extend(["--config", str(config_path)])

        result = subprocess.run(
            command,
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise AssertionError(f"Example site build failed:\n{result.stdout}\n{result.stderr}")

    @classmethod
    def _write_paginated_config(cls):
        config_path = Path(cls._tmp.name) / "paginated_config.json"
        config_path.write_text(
            json.dumps(
                {
                    "site_rendering": {
                        "galleries": {
                            "creator_cards": {"page_size": 1, "image_max_height": 2000},
                            "project_cards": {"page_size": 1, "image_max_height": 2000},
                        }
                    }
                }
            ),
            encoding="utf-8",
        )
        return config_path

    @classmethod
    def _find_audio_project_page(cls):
        for path in sorted((cls.site_dir / "html").rglob("*.html")):
            if "audio-gallery" in path.read_text(encoding="utf-8"):
                return path.relative_to(cls.site_dir).as_posix()
        raise AssertionError("Generated example site does not contain an audio project page")

    @classmethod
    def _start_static_server(cls):
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=Path(cls._tmp.name))
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        cls.base_url = f"http://127.0.0.1:{cls.server.server_port}"
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()

    @classmethod
    def _start_browser(cls):
        cls.playwright = sync_playwright().start()
        try:
            cls.browser = cls.playwright.chromium.launch()
        except PlaywrightError as exc:
            cls.playwright.stop()
            raise unittest.SkipTest(
                "Playwright Chromium is not installed; run `python -m playwright install chromium`."
            ) from exc

    def setUp(self):
        self.console_errors = []
        self.page_errors = []
        self.page = self.browser.new_page()
        self.page.on("console", self._record_console_message)
        self.page.on("pageerror", lambda error: self.page_errors.append(str(error)))

    def tearDown(self):
        self.page.close()

    def _record_console_message(self, message):
        if message.type == "error":
            self.console_errors.append(message.text)

    def assertNoBrowserErrors(self):
        self.assertEqual(self.console_errors, [])
        self.assertEqual(self.page_errors, [])

    def open_page(self, rel_path: str):
        self.page.goto(f"{self.base_url}/site/{rel_path}")
        self.page.wait_for_load_state("load")
        self.page.wait_for_timeout(250)

    def open_paginated_page(self, rel_path: str):
        self.page.goto(f"{self.base_url}/paginated-site/{rel_path}")
        self.page.wait_for_load_state("load")
        self.page.wait_for_timeout(250)

    def assertAspectGalleryBuilt(self, selector="#imageGallery"):
        layout = self.page.evaluate(
            """
            selector => {
                const gallery = document.querySelector(selector);
                const wrappers = Array.from(gallery?.querySelectorAll('.image-wrapper') || []);
                const rects = wrappers.map(wrapper => {
                    const rect = wrapper.getBoundingClientRect();
                    return { left: rect.left, top: rect.top, width: rect.width, height: rect.height };
                });
                return {
                    wrapperCount: wrappers.length,
                    aspectBoxCount: gallery?.querySelectorAll('.aspect-ratio-box').length || 0,
                    firstTwoSameRow: rects.length < 2 ? true : Math.abs(rects[0].top - rects[1].top) < 4,
                    firstTwoSeparatedHorizontally: rects.length < 2 ? true : Math.abs(rects[0].left - rects[1].left) > 4,
                    positiveDimensions: rects.every(rect => rect.width > 0 && rect.height > 0),
                };
            }
            """,
            selector,
        )
        self.assertGreater(layout["wrapperCount"], 0)
        self.assertEqual(layout["aspectBoxCount"], layout["wrapperCount"])
        self.assertTrue(layout["positiveDimensions"])
        self.assertTrue(layout["firstTwoSameRow"])
        self.assertTrue(layout["firstTwoSeparatedHorizontally"])

    def test_creator_overview_search_filters_and_restores_cards(self):
        self.open_page("index.html")

        self.assertEqual(self.page.locator("#imageGallery .image-wrapper").count(), 3)
        self.assertAspectGalleryBuilt()

        self.page.fill("#search-input", "nia")
        self.page.wait_for_timeout(150)

        cards = self.page.locator("#imageGallery .image-wrapper")
        self.assertEqual(cards.count(), 1)
        self.assertIn("Nia Solen", self.page.locator("#imageGallery").inner_text())
        self.assertTrue(self.page.locator("#clear-search").is_visible())

        self.page.click("#clear-search")
        self.page.wait_for_timeout(150)

        self.assertEqual(self.page.locator("#imageGallery .image-wrapper").count(), 3)
        self.assertAspectGalleryBuilt()
        self.assertNoBrowserErrors()

    def test_search_updates_do_not_accumulate_resize_listeners(self):
        self.page.add_init_script(
            """
            (() => {
                const originalAddEventListener = window.addEventListener.bind(window);
                window.__resizeListenerRegistrations = 0;
                window.addEventListener = function(type, listener, options) {
                    if (type === 'resize') {
                        window.__resizeListenerRegistrations += 1;
                    }
                    return originalAddEventListener(type, listener, options);
                };
            })();
            """
        )
        self.open_page("index.html")
        initial_registrations = self.page.evaluate("window.__resizeListenerRegistrations")

        for query in ("n", "ni", "nia", ""):
            self.page.fill("#search-input", query)
            self.page.wait_for_timeout(50)

        self.assertEqual(
            self.page.evaluate("window.__resizeListenerRegistrations"),
            initial_registrations,
        )
        self.page.evaluate("window.dispatchEvent(new Event('resize'))")
        self.assertEqual(self.page.locator("#imageGallery .image-wrapper").count(), 3)
        self.assertAspectGalleryBuilt()
        self.assertNoBrowserErrors()

    def test_project_overview_tag_query_filters_and_clears_url(self):
        self.open_page("projects.html?tag=labels:orbit")

        cards = self.page.locator("#imageGallery .image-wrapper")
        self.assertEqual(cards.count(), 1)
        self.assertIn("Glass Circuit", self.page.locator("#imageGallery").inner_text())
        self.assertAspectGalleryBuilt()
        self.assertEqual(self.page.evaluate("window.location.search"), "")
        self.assertNoBrowserErrors()

    def test_gallery_builder_runs_before_images_load_and_prevents_vertical_stack(self):
        self.open_page("index.html")

        loading_modes = self.page.evaluate(
            "() => Array.from(document.querySelectorAll('#imageGallery img')).map(img => img.loading)"
        )

        self.assertIn("lazy", loading_modes)
        self.assertAspectGalleryBuilt()
        self.assertNoBrowserErrors()

    def test_paginated_gallery_rebuilds_layout_after_page_change(self):
        self.open_paginated_page("index.html")

        self.assertEqual(self.page.locator("#imageGallery .image-wrapper").count(), 1)
        self.assertGreater(self.page.locator(".pagination-controls button").count(), 0)
        self.assertAspectGalleryBuilt()

        self.page.click(".pagination-next")
        self.page.wait_for_timeout(150)

        self.assertEqual(self.page.locator("#imageGallery .image-wrapper").count(), 1)
        self.assertAspectGalleryBuilt()
        self.assertNoBrowserErrors()

    def test_theme_dropdown_applies_selected_theme(self):
        self.open_page("index.html")

        self.page.click("#theme-toggle")
        self.assertTrue(self.page.locator("#theme-panel").is_visible())
        self.page.click("[data-theme='theme-forest-night']")

        body_class = self.page.locator("body").get_attribute("class") or ""
        self.assertIn("theme-forest-night", body_class)
        self.assertFalse(self.page.locator("#theme-panel").is_visible())
        self.assertNoBrowserErrors()

    def test_custom_theme_appears_and_can_be_selected(self):
        self.open_page("index.html")

        self.page.click("#theme-toggle")
        self.page.click("[data-theme='theme-custom-night']")

        self.assertIn("theme-custom-night", self.page.locator("body").get_attribute("class") or "")
        self.assertEqual(
            self.page.locator("body").evaluate("body => getComputedStyle(body).backgroundColor"),
            "rgb(1, 2, 3)",
        )
        self.assertNoBrowserErrors()

    def test_restricted_local_storage_does_not_hide_or_break_page(self):
        self.page.add_init_script(
            "Object.defineProperty(window, 'localStorage', { get() { throw new Error('blocked'); } });"
        )

        self.open_page("index.html")

        self.assertIn("theme-frozen-aurora", self.page.locator("body").get_attribute("class") or "")
        self.assertEqual(self.page.locator("body").evaluate("body => getComputedStyle(body).display"), "block")
        self.assertNoBrowserErrors()

    def test_tags_page_renders_and_initializes_theme(self):
        self.open_page("tags.html")

        self.assertEqual(self.page.locator("body").evaluate("body => getComputedStyle(body).display"), "block")
        self.assertGreater(self.page.locator(".tag-category").count(), 0)
        self.assertEqual(self.page.evaluate("typeof window.cr4te?.onReady"), "function")
        self.assertNoBrowserErrors()

    def test_project_page_initializes_audio_controls(self):
        self.open_page(self.audio_project_path)

        self.assertEqual(self.page.locator(".audio-gallery").count(), 1)
        self.assertEqual(self.page.locator(".audio-gallery li").count(), 3)
        self.assertTrue(self.page.locator(".audio-gallery .progress-bar").is_disabled())
        self.assertEqual(self.page.locator(".audio-gallery .volume-slider").count(), 1)
        self.assertNoBrowserErrors()

    def test_audio_previous_and_next_buttons_disable_at_track_bounds(self):
        self.open_page(self.audio_project_path)
        self.page.evaluate(
            """
            () => {
                HTMLMediaElement.prototype.play = function () {
                    this.dispatchEvent(new Event('play'));
                    return Promise.resolve();
                };
            }
            """
        )

        previous_button = self.page.locator("[data-audio-action='previous']")
        next_button = self.page.locator("[data-audio-action='next']")
        tracks = self.page.locator(".audio-gallery li")

        tracks.nth(0).click()
        self.assertTrue(previous_button.is_disabled())
        self.assertFalse(next_button.is_disabled())

        tracks.nth(1).click()
        self.assertFalse(previous_button.is_disabled())
        self.assertFalse(next_button.is_disabled())

        tracks.nth(2).click()
        self.assertFalse(previous_button.is_disabled())
        self.assertTrue(next_button.is_disabled())
        self.assertNoBrowserErrors()

    def test_rendered_pages_do_not_use_inline_javascript_handlers(self):
        for rel_path in ("index.html", "projects.html", self.audio_project_path):
            with self.subTest(rel_path=rel_path):
                self.open_page(rel_path)
                inline_handler_count = self.page.locator("[onclick], [oninput], [onchange]").count()
                self.assertEqual(inline_handler_count, 0)
                self.assertNoBrowserErrors()

    def test_legacy_global_handlers_are_not_exposed(self):
        self.open_page(self.audio_project_path)

        globals_status = self.page.evaluate(
            """
            () => ({
                toggleMute: typeof window.toggleMute,
                togglePlay: typeof window.togglePlay,
                seekAudio: typeof window.seekAudio,
                setVolume: typeof window.setVolume,
                toggleVideoPlay: typeof window.toggleVideoPlay,
                seekVideo: typeof window.seekVideo,
                setVideoVolume: typeof window.setVideoVolume,
                toggleFullscreen: typeof window.toggleFullscreen,
                paginateGallery: typeof window.paginateGallery,
                rebuildAspectImageGallery: typeof window.rebuildAspectImageGallery,
                rebuildJustifiedImageGallery: typeof window.rebuildJustifiedImageGallery,
                rebindLightbox: typeof window.rebindLightbox,
                cr4teOnReady: typeof window.cr4te?.onReady,
                cr4teMediaProgress: typeof window.cr4te?.media?.updateProgress,
                cr4teMediaSeek: typeof window.cr4te?.media?.bindSeekSlider,
            })
            """
        )

        for name, value in globals_status.items():
            with self.subTest(name=name):
                if name.startswith("cr4te"):
                    self.assertEqual(value, "function")
                else:
                    self.assertEqual(value, "undefined")

        self.assertNoBrowserErrors()

    def test_single_image_lightbox_opens_and_closes(self):
        self.open_page(self.audio_project_path)

        self.page.locator("a[data-lightbox-single='true']").first.click()
        self.page.wait_for_timeout(150)

        self.assertTrue(self.page.locator("#lightbox-overlay").is_visible())
        self.page.keyboard.press("Escape")
        self.page.wait_for_timeout(150)
        self.assertFalse(self.page.locator("#lightbox-overlay").is_visible())
        self.assertNoBrowserErrors()

    def test_resize_does_not_raise_browser_errors(self):
        self.open_page(self.audio_project_path)

        self.page.set_viewport_size({"width": 390, "height": 844})
        self.page.wait_for_timeout(250)
        self.page.set_viewport_size({"width": 1280, "height": 900})
        self.page.wait_for_timeout(250)

        self.assertNoBrowserErrors()


if __name__ == "__main__":
    unittest.main()
