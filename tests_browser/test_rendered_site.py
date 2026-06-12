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
        cls.details_site_dir = Path(cls._tmp.name) / "details-site"
        cls._build_example_site(cls.site_dir)
        cls._build_example_site(cls.paginated_site_dir, cls._write_paginated_config(), domain=None)
        cls._build_example_site(cls.details_site_dir, cls._write_details_config(), domain=None)
        cls.audio_project_path = cls._find_audio_project_page()
        cls.caption_project_path = cls._find_caption_project_page()
        cls.creator_path = cls._find_creator_page()
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
    def _write_details_config(cls):
        config_path = Path(cls._tmp.name) / "details_config.json"
        config_path.write_text(
            json.dumps(
                {
                    "site_rendering": {
                        "portraits": {"visibility": "details"},
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
    def _find_caption_project_page(cls):
        for path in sorted((cls.site_dir / "html").rglob("*.html")):
            if "image-caption-section" in path.read_text(encoding="utf-8"):
                return path.relative_to(cls.site_dir).as_posix()
        raise AssertionError("Generated example site does not contain an image-caption project page")

    @classmethod
    def _find_creator_page(cls):
        for path in sorted((cls.site_dir / "html").rglob("*.html")):
            if '<div class="section-title">Profile</div>' in path.read_text(encoding="utf-8"):
                return path.relative_to(cls.site_dir).as_posix()
        raise AssertionError("Generated example site does not contain a creator page")

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

    def open_details_page(self, rel_path: str):
        self.page.goto(f"{self.base_url}/details-site/{rel_path}")
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
        self.assertGreater(self.page.locator('#imageGallery .media-badge[title="1 album"]').count(), 0)
        self.assertEqual(self.page.locator('#imageGallery .media-badge[title="1 Album"]').count(), 0)
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

    def test_details_portrait_visibility_uses_text_overview_and_detail_portraits(self):
        self.open_details_page("index.html")

        cards = self.page.locator("#imageGallery .creator-text-card")
        self.assertEqual(cards.count(), 3)
        self.assertEqual(self.page.locator("#imageGallery .card-image").count(), 0)
        self.assertEqual(self.page.locator("#imageGallery .aspect-ratio-box").count(), 0)
        self.assertGreater(self.page.locator("#imageGallery .creator-text-card__project-summary").count(), 0)
        self.assertGreater(self.page.locator("#imageGallery .creator-text-card__media-summary").count(), 0)
        self.assertGreater(self.page.get_by_text("1 project", exact=True).count(), 0)
        self.assertEqual(self.page.get_by_text("1 Project", exact=True).count(), 0)
        project_summary_box = self.page.locator("#imageGallery .creator-text-card__project-summary").first.bounding_box()
        media_summary_box = self.page.locator("#imageGallery .creator-text-card__media-summary").first.bounding_box()
        self.assertGreater(media_summary_box["y"], project_summary_box["y"])

        self.page.fill("#search-input", "nia")
        self.page.wait_for_timeout(150)
        self.assertEqual(self.page.locator("#imageGallery .creator-text-card").count(), 1)
        self.assertIn("Nia Solen", self.page.locator("#imageGallery").inner_text())

        self.open_details_page(self.creator_path)
        self.assertGreater(self.page.locator(".info-block__media img[alt^='Portrait of']").count(), 0)
        self.assertNoBrowserErrors()

    def test_logo_remains_active_and_consistent_across_pages_and_themes(self):
        self.open_page("index.html")
        logo_link = self.page.locator(".site-logo-link")
        logo = logo_link.locator(".site-logo")

        self.assertEqual(logo_link.get_attribute("href"), "index.html")
        self.assertEqual(logo_link.get_attribute("aria-label"), "cr4te Musicians overview")
        self.assertEqual(logo.get_attribute("src"), "assets/favicon.svg")
        self.assertEqual(self.page.locator(".nav-current").inner_text(), "Musicians")

        logo_src = logo.evaluate("element => element.currentSrc")
        self.page.get_by_role("button", name="Themes").click()
        self.page.get_by_role("menuitemradio", name="Forest Night").click()
        self.assertEqual(logo.evaluate("element => element.currentSrc"), logo_src)

        self.open_page(self.audio_project_path)
        logo_link = self.page.locator(".site-logo-link")
        self.assertTrue(logo_link.get_attribute("href").endswith("index.html"))
        logo_link.click()
        self.page.wait_for_load_state("load")
        self.assertTrue(self.page.url.endswith("/site/index.html"))
        self.assertNoBrowserErrors()

    def test_header_navigation_items_are_vertically_centered(self):
        self.open_page("index.html")

        centers = self.page.evaluate(
            """
            () => {
                const center = selector => {
                    const rect = document.querySelector(selector).getBoundingClientRect();
                    return rect.top + rect.height / 2;
                };
                return {
                    logo: center('.site-logo-link'),
                    breadcrumbs: center('.breadcrumb-list'),
                    theme: center('#theme-toggle'),
                };
            }
            """
        )

        self.assertAlmostEqual(centers["logo"], centers["breadcrumbs"], delta=0.25)
        self.assertAlmostEqual(centers["logo"], centers["theme"], delta=0.25)
        self.assertNoBrowserErrors()

    def test_search_clear_button_works_from_keyboard(self):
        self.open_page("index.html")
        self.page.fill("#search-input", "nia")
        self.page.locator("#search-input").press("Tab")

        self.assertEqual(self.page.evaluate("document.activeElement.id"), "clear-search")
        self.page.keyboard.press("Enter")

        self.assertEqual(self.page.locator("#search-input").input_value(), "")
        self.assertEqual(self.page.locator("#imageGallery .image-wrapper").count(), 3)
        self.assertNoBrowserErrors()

    def test_focus_indicator_is_keyboard_only(self):
        self.open_page("index.html")
        toggle = self.page.locator("#theme-toggle")

        toggle.click()
        mouse_outline = toggle.evaluate("element => getComputedStyle(element).outlineStyle")
        self.page.keyboard.press("Escape")
        toggle.evaluate("element => element.blur()")
        toggle.focus()
        keyboard_outline = toggle.evaluate(
            "element => ({ style: getComputedStyle(element).outlineStyle, width: getComputedStyle(element).outlineWidth })"
        )

        self.assertEqual(mouse_outline, "none")
        self.assertEqual(keyboard_outline["style"], "solid")
        self.assertEqual(keyboard_outline["width"], "2px")

    def test_focus_indicators_use_theme_colors_and_render_inside_control_bounds(self):
        self.open_page("index.html")

        focus_colors = []
        for theme in ("theme-frozen-aurora", "theme-forest-night", "theme-mono-terminal"):
            self.page.evaluate(
                """
                theme => {
                    document.body.className = theme;
                    document.querySelector('#search-input').focus();
                }
                """,
                theme,
            )
            focus = self.page.locator("#search-input").evaluate(
                """
                element => {
                    const style = getComputedStyle(element);
                    const probe = document.createElement('span');
                    probe.style.color = 'var(--theme-focus-outline)';
                    document.body.appendChild(probe);
                    const themeColor = getComputedStyle(probe).color;
                    probe.remove();
                    return {
                        color: style.outlineColor,
                        offset: style.outlineOffset,
                        themeColor,
                    };
                }
                """
            )
            self.assertEqual(focus["color"], focus["themeColor"])
            self.assertEqual(focus["offset"], "-2px")
            focus_colors.append(focus["color"])

        self.assertEqual(len(set(focus_colors)), len(focus_colors))

    def test_image_card_link_draws_focus_ring_around_whole_card(self):
        self.open_page("index.html")
        card = self.page.locator("#imageGallery .image-card").first
        link = card.locator(":scope > a")

        link.focus()
        styles = self.page.evaluate(
            """
            () => {
                const card = document.querySelector('#imageGallery .image-card');
                const link = card.querySelector(':scope > a');
                const cardStyle = getComputedStyle(card);
                const linkStyle = getComputedStyle(link);
                return {
                    cardOutline: cardStyle.outlineStyle,
                    cardOutlineOffset: cardStyle.outlineOffset,
                    linkOutline: linkStyle.outlineStyle,
                };
            }
            """
        )

        self.assertEqual(styles["cardOutline"], "solid")
        self.assertEqual(styles["cardOutlineOffset"], "-2px")
        self.assertEqual(styles["linkOutline"], "none")

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

    def test_theme_dropdown_supports_keyboard_navigation_and_escape(self):
        self.open_page("index.html")
        toggle = self.page.locator("#theme-toggle")
        toggle.focus()

        self.page.keyboard.press("ArrowDown")
        self.assertTrue(self.page.locator("#theme-panel").is_visible())
        first_theme = self.page.evaluate("document.activeElement.dataset.theme")

        self.page.keyboard.press("ArrowDown")
        second_theme = self.page.evaluate("document.activeElement.dataset.theme")
        self.assertNotEqual(first_theme, second_theme)

        self.page.keyboard.press("Escape")
        self.assertFalse(self.page.locator("#theme-panel").is_visible())
        self.assertEqual(self.page.evaluate("document.activeElement.id"), "theme-toggle")

        self.page.keyboard.press("ArrowDown")
        selected_theme = self.page.evaluate("document.activeElement.dataset.theme")
        self.page.keyboard.press("Enter")
        self.assertIn(selected_theme, self.page.locator("body").get_attribute("class") or "")
        self.assertEqual(self.page.evaluate("document.activeElement.id"), "theme-toggle")
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

    def test_caption_toggle_works_when_local_storage_is_restricted(self):
        self.page.add_init_script(
            "Object.defineProperty(window, 'localStorage', { get() { throw new Error('blocked'); } });"
        )

        self.open_page(self.caption_project_path)
        section = self.page.locator(".image-caption-section").first
        self.assertIn("no-captions", section.get_attribute("class") or "")
        self.assertEqual(section.locator(".caption-toggle-btn").get_attribute("aria-pressed"), "false")

        section.locator(".caption-toggle-btn").click()

        self.assertNotIn("no-captions", section.get_attribute("class") or "")
        self.assertEqual(section.locator(".caption-toggle-btn").get_attribute("aria-pressed"), "true")
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

    def test_audio_tracks_and_media_controls_expose_accessible_semantics(self):
        self.open_page(self.audio_project_path)
        track = self.page.locator("[data-audio-action='select-track']").first

        self.assertEqual(track.evaluate("element => element.tagName"), "BUTTON")
        self.assertEqual(self.page.locator(".audio-gallery .progress-bar").get_attribute("aria-label"), "Seek")
        self.assertEqual(self.page.locator(".audio-gallery .volume-slider").get_attribute("aria-label"), "Volume")

        track.focus()
        self.page.keyboard.press("Enter")
        self.assertEqual(self.page.locator(".audio-gallery").get_attribute("data-current-index"), "0")

        mute = self.page.locator(".audio-gallery .volume-toggle-btn")
        self.assertEqual(mute.get_attribute("aria-pressed"), "false")
        mute.click()
        self.assertEqual(mute.get_attribute("aria-pressed"), "true")
        self.assertNoBrowserErrors()

    def test_audio_track_list_supports_roving_keyboard_navigation(self):
        self.open_page(self.audio_project_path)
        tracks = self.page.locator("[data-audio-action='select-track']")
        first = tracks.nth(0)
        second = tracks.nth(1)
        last = tracks.nth(2)

        self.assertEqual(first.get_attribute("tabindex"), "0")
        self.assertEqual(second.get_attribute("tabindex"), "-1")
        first.focus()

        self.page.keyboard.press("ArrowDown")
        self.assertTrue(second.evaluate("element => document.activeElement === element"))
        self.assertEqual(self.page.locator(".audio-gallery").get_attribute("data-current-index"), None)
        self.assertEqual(first.get_attribute("tabindex"), "-1")
        self.assertEqual(second.get_attribute("tabindex"), "0")

        self.page.keyboard.press("ArrowUp")
        self.assertTrue(first.evaluate("element => document.activeElement === element"))
        self.page.keyboard.press("ArrowDown")
        self.page.keyboard.press("End")
        self.assertTrue(last.evaluate("element => document.activeElement === element"))
        self.page.keyboard.press("Home")
        self.assertTrue(first.evaluate("element => document.activeElement === element"))

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
        self.page.keyboard.press("Space")
        self.assertEqual(self.page.locator(".audio-gallery").get_attribute("data-current-index"), "0")
        self.assertNoBrowserErrors()

    def test_focused_video_surface_supports_space_and_enter_play_pause(self):
        self.open_page("index.html")
        self.page.evaluate(
            """
            () => {
                const wrapper = document.createElement('div');
                wrapper.className = 'video-wrapper';
                wrapper.innerHTML = `
                    <video tabindex="0" aria-label="Test video"></video>
                    <div class="video-controls">
                        <button data-video-action="toggle-play" data-play-label="Play" data-pause-label="Pause">
                            <svg class="play-toggle-icon">
                                <g data-play></g>
                                <g data-pause></g>
                            </svg>
                        </button>
                        <input class="progress-bar" type="range">
                        <span class="time-display"></span>
                    </div>
                `;
                const video = wrapper.querySelector('video');
                video.dataset.paused = 'true';
                Object.defineProperty(video, 'paused', { get() { return this.dataset.paused === 'true'; } });
                video.play = function () {
                    this.dataset.paused = 'false';
                    this.dispatchEvent(new Event('play'));
                    return Promise.resolve();
                };
                video.pause = function () {
                    this.dataset.paused = 'true';
                    this.dispatchEvent(new Event('pause'));
                };
                document.body.appendChild(wrapper);

                const script = document.createElement('script');
                script.src = 'assets/js/video_player.js?keyboard-test';
                document.body.appendChild(script);
            }
            """
        )
        self.page.wait_for_function("typeof window.cr4te?.video?.togglePlay === 'function'")
        video = self.page.locator(".video-wrapper video")
        video.focus()

        self.page.keyboard.press("Space")
        self.assertEqual(video.get_attribute("data-paused"), "false")
        self.page.keyboard.press("Enter")
        self.assertEqual(video.get_attribute("data-paused"), "true")
        self.assertNoBrowserErrors()

    def test_even_audio_track_uses_playing_colors_when_selected(self):
        self.open_page(self.audio_project_path)
        track = self.page.locator("[data-audio-action='select-track']").nth(1)

        track.click()
        self.page.wait_for_timeout(250)
        colors = track.evaluate(
            """
            element => {
                const style = getComputedStyle(element);
                const probe = document.createElement('span');
                probe.style.backgroundColor = 'var(--theme-track-playing-bg)';
                probe.style.color = 'var(--theme-track-playing-text)';
                document.body.appendChild(probe);
                const probeStyle = getComputedStyle(probe);
                const playingBackground = probeStyle.backgroundColor;
                const playingText = probeStyle.color;
                probe.remove();
                return {
                    background: style.backgroundColor,
                    text: style.color,
                    playingBackground,
                    playingText,
                };
            }
            """
        )

        self.assertIn("playing", track.get_attribute("class") or "")
        self.assertEqual(colors["background"], colors["playingBackground"])
        self.assertEqual(colors["text"], colors["playingText"])
        self.assertNoBrowserErrors()

    def test_starting_media_pauses_only_the_previously_active_player(self):
        self.open_page(self.audio_project_path)

        result = self.page.evaluate(
            """
            () => {
              const media = [
                document.createElement('audio'),
                document.createElement('video'),
                document.createElement('audio'),
              ];

              media.forEach((element, index) => {
                element.dataset.player = String(index);
                element.dataset.pauseCount = '0';
                element.pause = function () {
                  this.dataset.pauseCount = String(Number(this.dataset.pauseCount) + 1);
                  this.dispatchEvent(new Event('pause'));
                };
                document.body.appendChild(element);
              });

              media[0].dispatchEvent(new Event('play'));
              media[1].dispatchEvent(new Event('play'));
              media[2].dispatchEvent(new Event('play'));
              media[2].dispatchEvent(new Event('pause'));
              media[0].dispatchEvent(new Event('play'));

              return media.map(element => Number(element.dataset.pauseCount));
            }
            """
        )

        self.assertEqual(result, [1, 1, 0])
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

        trigger = self.page.locator("a[data-lightbox-single='true']").first
        trigger.focus()
        trigger.press("Enter")
        self.page.wait_for_timeout(150)

        overlay = self.page.locator("#lightbox-overlay")
        close = self.page.locator("#lightbox-close")

        self.assertTrue(overlay.is_visible())
        self.assertEqual(overlay.get_attribute("role"), "dialog")
        self.assertEqual(overlay.get_attribute("aria-modal"), "true")
        self.assertEqual(overlay.get_attribute("aria-describedby"), "lightbox-caption")
        self.assertEqual(close.evaluate("element => element.tagName"), "BUTTON")
        self.assertEqual(close.get_attribute("aria-label"), "Close lightbox")
        self.assertTrue(overlay.evaluate("element => document.activeElement === element"))

        self.page.keyboard.press("Tab")
        self.assertTrue(close.evaluate("element => document.activeElement === element"))
        self.page.keyboard.press("Shift+Tab")
        self.assertTrue(close.evaluate("element => document.activeElement === element"))

        self.page.keyboard.press("Escape")
        self.page.wait_for_timeout(150)
        self.assertFalse(overlay.is_visible())
        self.assertIsNotNone(overlay.get_attribute("hidden"))
        self.assertTrue(trigger.evaluate("element => document.activeElement === element"))
        self.assertNoBrowserErrors()

    def test_gallery_lightbox_uses_native_navigation_and_traps_focus(self):
        self.open_page(self.caption_project_path)
        trigger = self.page.locator("[data-lightbox='true'] a").first
        trigger.click()
        self.page.wait_for_timeout(150)

        close = self.page.locator("#lightbox-close")
        previous = self.page.locator("#lightbox-left")
        next_button = self.page.locator("#lightbox-right")
        image = self.page.locator("#lightbox-image")
        original_src = image.get_attribute("src")

        for button, label in (
            (previous, "Previous image"),
            (next_button, "Next image"),
        ):
            with self.subTest(label=label):
                self.assertTrue(button.is_visible())
                self.assertEqual(button.evaluate("element => element.tagName"), "BUTTON")
                self.assertEqual(button.get_attribute("aria-label"), label)

        overlay = self.page.locator("#lightbox-overlay")
        self.assertTrue(overlay.evaluate("element => document.activeElement === element"))
        self.assertEqual(overlay.evaluate("element => getComputedStyle(element).outlineStyle"), "none")

        for key in ("ArrowUp", "ArrowDown"):
            with self.subTest(key=key):
                self.page.keyboard.press(key)
                self.assertEqual(image.get_attribute("src"), original_src)
                self.assertTrue(overlay.evaluate("element => document.activeElement === element"))

        self.page.keyboard.press("ArrowRight")
        self.assertNotEqual(image.get_attribute("src"), original_src)
        self.assertTrue(overlay.evaluate("element => document.activeElement === element"))

        self.page.keyboard.press("Tab")
        self.assertTrue(close.evaluate("element => document.activeElement === element"))
        self.page.keyboard.press("Shift+Tab")
        self.assertTrue(next_button.evaluate("element => document.activeElement === element"))
        self.page.keyboard.press("Tab")
        self.assertTrue(close.evaluate("element => document.activeElement === element"))

        self.page.keyboard.press("Escape")
        self.assertTrue(trigger.evaluate("element => document.activeElement === element"))

        trigger.click()
        self.page.locator("#lightbox-overlay").click(position={"x": 5, "y": 5})
        self.assertFalse(self.page.locator("#lightbox-overlay").is_visible())
        self.assertTrue(trigger.evaluate("element => document.activeElement === element"))
        self.assertNoBrowserErrors()

    def test_resize_does_not_raise_browser_errors(self):
        self.open_page(self.audio_project_path)

        self.page.set_viewport_size({"width": 390, "height": 844})
        self.page.wait_for_timeout(250)
        self.page.set_viewport_size({"width": 1280, "height": 900})
        self.page.wait_for_timeout(250)

        self.assertNoBrowserErrors()

    def test_detail_content_is_visible_and_ordered_on_mobile_without_javascript(self):
        page = self.browser.new_page(
            java_script_enabled=False,
            viewport={"width": 390, "height": 844},
        )
        try:
            for rel_path in (self.creator_path, self.audio_project_path):
                with self.subTest(rel_path=rel_path):
                    page.set_viewport_size({"width": 390, "height": 844})
                    page.goto(f"{self.base_url}/site/{rel_path}")
                    page.wait_for_load_state("load")

                    mobile_layout = page.evaluate(
                        """
                        () => {
                            const layout = document.querySelector('.two-column-layout');
                            const content = document.querySelector('.detail-content');
                            const left = document.querySelector('.left-column');
                            const right = document.querySelector('.right-column');
                            const layoutRect = layout.getBoundingClientRect();
                            const contentRect = content.getBoundingClientRect();
                            const leftRect = left.getBoundingClientRect();
                            const rightRect = right.getBoundingClientRect();
                            return {
                                leftDisplay: getComputedStyle(left).display,
                                rightDisplay: getComputedStyle(right).display,
                                leftSections: left.querySelectorAll('.section-box').length,
                                rightSections: right.querySelectorAll('.section-box').length,
                                leftHeight: leftRect.height,
                                rightHeight: rightRect.height,
                                leftBeforeRight: leftRect.bottom <= rightRect.top,
                                outerBottomSpace: layoutRect.bottom - contentRect.bottom,
                                innerBottomPadding: parseFloat(getComputedStyle(content).paddingBottom),
                            };
                        }
                        """
                    )

                    self.assertNotEqual(mobile_layout["leftDisplay"], "none")
                    self.assertNotEqual(mobile_layout["rightDisplay"], "none")
                    self.assertGreater(mobile_layout["leftSections"], 0)
                    self.assertGreater(mobile_layout["rightSections"], 0)
                    self.assertGreater(mobile_layout["leftHeight"], 0)
                    self.assertGreater(mobile_layout["rightHeight"], 0)
                    self.assertTrue(mobile_layout["leftBeforeRight"])
                    self.assertGreater(mobile_layout["outerBottomSpace"], 0)
                    self.assertGreater(mobile_layout["innerBottomPadding"], 0)

                    page.set_viewport_size({"width": 1280, "height": 900})
                    desktop_side_by_side = page.evaluate(
                        """
                        () => {
                            const leftRect = document.querySelector('.left-column').getBoundingClientRect();
                            const rightRect = document.querySelector('.right-column').getBoundingClientRect();
                            return leftRect.right <= rightRect.left;
                        }
                        """
                    )
                    self.assertTrue(desktop_side_by_side)
        finally:
            page.close()


if __name__ == "__main__":
    unittest.main()
