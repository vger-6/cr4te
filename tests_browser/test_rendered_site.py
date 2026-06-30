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
        cls.disabled_portraits_site_dir = Path(cls._tmp.name) / "disabled-portraits-site"
        cls._build_example_site(cls.site_dir)
        cls._build_example_site(cls.paginated_site_dir, cls._write_paginated_config(), domain=None)
        cls._build_example_site(cls.details_site_dir, cls._write_details_config(), domain=None)
        cls._build_example_site(cls.disabled_portraits_site_dir, cls._write_disabled_portraits_config(), domain=None)
        cls.audio_project_path = cls._find_audio_project_page()
        cls.video_project_path = cls._find_video_project_page()
        cls.caption_project_path = cls._find_caption_project_page()
        cls.description_project_path = cls._find_project_page_with_description()
        cls.landscape_project_path = cls._find_landscape_project_page_with_metadata()
        cls.creator_path = cls._find_creator_page()
        cls.combined_event_creator_path = cls._find_creator_page_with_combined_event()
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
                            "creator_cards": {"page_rows": 1, "image_max_height": 2000},
                            "project_cards": {"page_rows": 1, "image_max_height": 2000},
                        },
                        "creator_page": {"media_gallery_page_rows": 1},
                        "project_page": {"media_gallery_page_rows": 1},
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
    def _write_disabled_portraits_config(cls):
        config_path = Path(cls._tmp.name) / "disabled_portraits_config.json"
        config_path.write_text(
            json.dumps(
                {
                    "site_rendering": {
                        "portraits": {"visibility": "disabled"},
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
    def _find_video_project_page(cls):
        for path in sorted((cls.site_dir / "html").rglob("*.html")):
            if "video-wrapper" in path.read_text(encoding="utf-8"):
                return path.relative_to(cls.site_dir).as_posix()
        raise AssertionError("Generated example site does not contain a video project page")

    @classmethod
    def _find_caption_project_page(cls):
        for path in sorted((cls.site_dir / "html").rglob("*.html")):
            if "image-caption-section" in path.read_text(encoding="utf-8"):
                return path.relative_to(cls.site_dir).as_posix()
        raise AssertionError("Generated example site does not contain an image-caption project page")

    @classmethod
    def _find_project_page_with_description(cls):
        for path in sorted((cls.site_dir / "html").rglob("*.html")):
            if "expandable-text--project-description" in path.read_text(encoding="utf-8"):
                return path.relative_to(cls.site_dir).as_posix()
        raise AssertionError("Generated example site does not contain a project page with a description")

    @classmethod
    def _find_landscape_project_page_with_metadata(cls):
        for path in sorted((cls.site_dir / "html").rglob("*.html")):
            content = path.read_text(encoding="utf-8")
            if (
                'info-block info-block--landscape' in content
                and '<dt class="meta-label data-label">Release Date</dt>' in content
            ):
                return path.relative_to(cls.site_dir).as_posix()
        raise AssertionError("Generated example site does not contain a landscape project with multiple metadata entries")

    @classmethod
    def _find_creator_page(cls):
        for path in sorted((cls.site_dir / "html").rglob("*.html")):
            if '<div class="section-title">Profile</div>' in path.read_text(encoding="utf-8"):
                return path.relative_to(cls.site_dir).as_posix()
        raise AssertionError("Generated example site does not contain a creator page")

    @classmethod
    def _find_creator_page_with_combined_event(cls):
        for path in sorted((cls.site_dir / "html").rglob("*.html")):
            if "January 1986 in Berlin" in path.read_text(encoding="utf-8"):
                return path.relative_to(cls.site_dir).as_posix()
        raise AssertionError("Generated example site does not contain a combined date-and-place event")

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

    def open_disabled_portraits_page(self, rel_path: str):
        self.page.goto(f"{self.base_url}/disabled-portraits-site/{rel_path}")
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
        self.assertTrue(self.page.locator(".empty-state--search").is_hidden())

        self.page.fill("#search-input", "no-such-musician")
        self.page.wait_for_timeout(150)

        empty_state = self.page.locator(".empty-state--search")
        self.assertEqual(cards.count(), 0)
        self.assertFalse(empty_state.is_hidden())
        self.assertEqual(empty_state.inner_text(), "No results match your search")
        self.assertEqual(empty_state.get_attribute("role"), "status")
        self.assertEqual(empty_state.get_attribute("aria-live"), "polite")
        self.assertTrue(self.page.locator("#imageGallery").is_hidden())

        self.page.click("#clear-search")
        self.page.wait_for_timeout(150)

        self.assertEqual(self.page.locator("#imageGallery .image-wrapper").count(), 3)
        self.assertTrue(self.page.locator(".empty-state--search").is_hidden())
        self.assertFalse(self.page.locator("#imageGallery").is_hidden())
        self.assertAspectGalleryBuilt()
        self.assertNoBrowserErrors()

    def test_details_portrait_visibility_uses_text_overview_and_detail_portraits(self):
        """Covers SITE-028 and SITE-029."""
        self.open_details_page("index.html")

        cards = self.page.locator("#imageGallery .creator-text-card")
        self.assertEqual(cards.count(), 3)
        self.assertEqual(self.page.locator("#imageGallery .card-image").count(), 0)
        self.assertEqual(self.page.locator("#imageGallery .aspect-ratio-box").count(), 0)
        self.assertGreater(self.page.locator("#imageGallery .creator-text-card__project-summary").count(), 0)
        self.assertGreater(self.page.locator("#imageGallery .creator-text-card__media-summary").count(), 0)
        self.assertGreater(self.page.get_by_text("1 project", exact=True).count(), 0)
        self.assertEqual(self.page.get_by_text("1 Project", exact=True).count(), 0)
        text_card_padding = self.page.locator("#imageGallery .creator-text-card__content").first.evaluate(
            "element => ({ top: getComputedStyle(element).paddingTop, right: getComputedStyle(element).paddingRight })"
        )
        self.assertEqual(text_card_padding["top"], text_card_padding["right"])
        self.assertGreater(float(text_card_padding["top"].removesuffix("px")), 0)
        project_summary_box = self.page.locator("#imageGallery .creator-text-card__project-summary").first.bounding_box()
        media_summary_box = self.page.locator("#imageGallery .creator-text-card__media-summary").first.bounding_box()
        self.assertGreater(media_summary_box["y"], project_summary_box["y"])
        unfiltered_card_width = cards.first.bounding_box()["width"]

        self.page.fill("#search-input", "nia")
        self.page.wait_for_timeout(150)
        self.assertEqual(self.page.locator("#imageGallery .creator-text-card").count(), 1)
        self.assertIn("Nia Solen", self.page.locator("#imageGallery").inner_text())
        filtered_card_width = self.page.locator("#imageGallery .creator-text-card").first.bounding_box()["width"]
        self.assertAlmostEqual(filtered_card_width, unfiltered_card_width, delta=1)

        self.open_details_page(self.creator_path)
        self.assertGreater(self.page.locator(".info-block__media img[alt^='Portrait of']").count(), 0)
        self.assertNoBrowserErrors()

    def test_detail_metadata_uses_stacked_semantic_presentation_and_preserves_image_layouts(self):
        """Covers SITE-016 and SITE-027."""
        self.open_page(self.creator_path)
        metadata = self.page.locator(".meta-list").first
        entries = metadata.locator(".meta-entry")

        self.assertEqual(metadata.evaluate("element => element.tagName"), "DL")
        self.assertGreater(entries.count(), 1)
        self.assertEqual(entries.first.locator(".meta-label").evaluate("element => element.tagName"), "DT")
        self.assertEqual(entries.first.locator(".meta-value").evaluate("element => element.tagName"), "DD")

        layout = self.page.evaluate(
            """
            () => {
                const block = document.querySelector('.info-block--portrait');
                const entries = block.querySelectorAll('.meta-entry');
                const label = entries[0].querySelector('.meta-label');
                const value = entries[0].querySelector('.meta-value');
                const nextLabel = entries[1].querySelector('.meta-label');
                const mediaRect = block.querySelector('.info-block__media').getBoundingClientRect();
                const metaRect = block.querySelector('.info-block__meta').getBoundingClientRect();
                const labelRect = label.getBoundingClientRect();
                const valueRect = value.getBoundingClientRect();
                const nextLabelRect = nextLabel.getBoundingClientRect();
                const probe = document.createElement('span');
                probe.style.color = 'var(--theme-data-label-text)';
                document.body.appendChild(probe);
                const labelToken = getComputedStyle(probe).color;
                probe.style.color = 'var(--theme-link)';
                const linkToken = getComputedStyle(probe).color;
                probe.remove();
                return {
                    labelToken,
                    linkToken,
                    blockGap: parseFloat(getComputedStyle(block).columnGap),
                    labelColor: getComputedStyle(label).color,
                    labelSize: parseFloat(getComputedStyle(label).fontSize),
                    valueSize: parseFloat(getComputedStyle(value).fontSize),
                    valueBelowLabel: valueRect.top >= labelRect.bottom,
                    labelValueGap: valueRect.top - labelRect.bottom,
                    entryGap: nextLabelRect.top - valueRect.bottom,
                    metadataBesidePortrait: metaRect.left >= mediaRect.right,
                    portraitMetadataGap: metaRect.left - mediaRect.right,
                };
            }
            """
        )

        self.assertEqual(layout["labelColor"], layout["labelToken"])
        self.assertNotEqual(layout["labelColor"], layout["linkToken"])
        self.assertLess(layout["labelSize"], layout["valueSize"])
        self.assertTrue(layout["valueBelowLabel"])
        self.assertGreaterEqual(layout["labelValueGap"], 0)
        self.assertGreater(layout["entryGap"], layout["labelValueGap"])
        self.assertTrue(layout["metadataBesidePortrait"])
        self.assertAlmostEqual(layout["portraitMetadataGap"], layout["blockGap"], delta=0.25)

        for theme in ("theme-frozen-aurora", "theme-forest-night", "theme-mono-terminal", "theme-amber-terminal"):
            colors = self.page.evaluate(
                """
                theme => {
                    document.body.className = theme;
                    const label = document.querySelector('.meta-label');
                    const probe = document.createElement('span');
                    probe.style.color = 'var(--theme-data-label-text)';
                    document.body.appendChild(probe);
                    const labelToken = getComputedStyle(probe).color;
                    probe.style.color = 'var(--theme-link)';
                    const result = {
                        label: getComputedStyle(label).color,
                        labelToken,
                        linkToken: getComputedStyle(probe).color,
                    };
                    probe.remove();
                    return result;
                }
                """,
                theme,
            )
            self.assertEqual(colors["label"], colors["labelToken"])
            self.assertNotEqual(colors["label"], colors["linkToken"])

        self.page.set_viewport_size({"width": 360, "height": 900})
        self.page.reload()
        narrow_layout = self.page.evaluate(
            """
            () => {
                const block = document.querySelector('.info-block--portrait');
                const mediaRect = block.querySelector('.info-block__media').getBoundingClientRect();
                const metaRect = block.querySelector('.info-block__meta').getBoundingClientRect();
                return {
                    metadataBelowPortrait: metaRect.top >= mediaRect.bottom,
                    metadataVisible: metaRect.height > 0,
                    portraitMetadataGap: metaRect.top - mediaRect.bottom,
                };
            }
            """
        )
        self.assertTrue(narrow_layout["metadataBelowPortrait"])
        self.assertTrue(narrow_layout["metadataVisible"])
        self.assertAlmostEqual(
            narrow_layout["portraitMetadataGap"],
            layout["portraitMetadataGap"],
            delta=0.25,
        )

        self.page.set_viewport_size({"width": 1280, "height": 720})
        self.open_page(self.landscape_project_path)
        landscape_layout = self.page.evaluate(
            """
            () => {
                const block = document.querySelector('.info-block--landscape');
                const mediaRect = block.querySelector('.info-block__media').getBoundingClientRect();
                const metaRect = block.querySelector('.info-block__meta').getBoundingClientRect();
                const entries = block.querySelectorAll('.meta-entry');
                const firstRect = entries[0].getBoundingClientRect();
                const secondRect = entries[1].getBoundingClientRect();
                return {
                    blockGap: parseFloat(getComputedStyle(block).rowGap),
                    metadataBelowImage: metaRect.top >= mediaRect.bottom,
                    imageMetadataGap: metaRect.top - mediaRect.bottom,
                    entriesShareRow: Math.abs(firstRect.top - secondRect.top) < 1,
                    entriesEqualWidth: Math.abs(firstRect.width - secondRect.width) < 1,
                };
            }
            """
        )
        self.assertTrue(landscape_layout["metadataBelowImage"])
        self.assertAlmostEqual(
            landscape_layout["imageMetadataGap"],
            landscape_layout["blockGap"],
            delta=0.25,
        )
        self.assertLess(landscape_layout["blockGap"], layout["blockGap"])
        self.assertTrue(landscape_layout["entriesShareRow"])
        self.assertTrue(landscape_layout["entriesEqualWidth"])

        self.page.set_viewport_size({"width": 360, "height": 900})
        self.page.reload()
        narrow_landscape_layout = self.page.evaluate(
            """
            () => {
                const entries = document.querySelector('.info-block--landscape').querySelectorAll('.meta-entry');
                const firstRect = entries[0].getBoundingClientRect();
                const secondRect = entries[1].getBoundingClientRect();
                return secondRect.top >= firstRect.bottom;
            }
            """
        )
        self.assertTrue(narrow_landscape_layout)
        self.assertNoBrowserErrors()

    def test_markdown_text_starts_with_compact_top_spacing(self):
        """Covers SITE-027."""
        self.open_page(self.creator_path)
        first_text_block = self.page.locator(".text-content > :first-child").first

        self.assertGreater(first_text_block.count(), 0)
        spacing = first_text_block.evaluate(
            """
            element => {
                const content = element.parentElement;
                const divider = content.previousElementSibling;
                return {
                    dividerGap: element.getBoundingClientRect().top - divider.getBoundingClientRect().bottom,
                    contentPaddingTop: getComputedStyle(content).paddingTop,
                    firstChildMarginTop: getComputedStyle(element).marginTop,
                };
            }
            """
        )
        content_padding = float(spacing["contentPaddingTop"].removesuffix("px"))
        self.assertAlmostEqual(
            spacing["dividerGap"],
            content_padding,
            delta=0.25,
        )
        self.assertGreater(content_padding, 0)
        self.assertEqual(spacing["firstChildMarginTop"], "0px")
        self.assertNoBrowserErrors()

    def test_detail_about_and_description_text_expand_only_when_too_long(self):
        """Covers SITE-026."""
        self.open_page(self.creator_path)

        creator_text = self.page.evaluate(
            """
            async () => {
                const tick = () => new Promise(resolve => requestAnimationFrame(resolve));
                const root = document.querySelector('.expandable-text--creator-about');
                const content = root.querySelector('[data-expandable-text-content]');
                const button = root.querySelector('[data-expandable-text-toggle]');
                const measure = () => {
                    const rootStyle = getComputedStyle(root);
                    const contentStyle = getComputedStyle(content);
                    return {
                        documentLanguage: document.documentElement.lang,
                        desktopLines: rootStyle.getPropertyValue('--expandable-text-lines').trim(),
                        mobileLines: rootStyle.getPropertyValue('--expandable-text-mobile-lines').trim(),
                        currentLines: rootStyle.getPropertyValue('--expandable-text-current-lines').trim(),
                        lineClamp: contentStyle.webkitLineClamp,
                        hyphens: contentStyle.hyphens,
                        overflowWrap: contentStyle.overflowWrap,
                        buttonHidden: button.hidden,
                        buttonText: button.textContent.trim(),
                        ariaExpanded: button.getAttribute('aria-expanded'),
                        isCollapsed: root.classList.contains('is-collapsed'),
                        isExpanded: root.classList.contains('is-expanded'),
                        isClipped: content.scrollHeight > content.clientHeight + 1,
                    };
                };

                content.innerHTML = '<p>Short text.</p>';
                window.cr4te.expandableText.update();
                await tick();
                await tick();
                const shortText = measure();

                content.innerHTML = Array.from(
                    { length: 16 },
                    (_, index) => `<p>Creator biography paragraph ${index + 1} with enough prose to exceed the limit.</p>`
                ).join('');
                window.cr4te.expandableText.update();
                await tick();
                await tick();
                const collapsed = measure();

                button.click();
                await tick();
                const expanded = measure();

                return { shortText, collapsed, expanded };
            }
            """
        )
        self.assertTrue(creator_text["shortText"]["buttonHidden"])
        self.assertFalse(creator_text["shortText"]["isCollapsed"])
        self.assertEqual(creator_text["collapsed"]["documentLanguage"], "en-US")
        self.assertEqual(creator_text["collapsed"]["desktopLines"], "8")
        self.assertEqual(creator_text["collapsed"]["mobileLines"], "2")
        self.assertEqual(creator_text["collapsed"]["currentLines"], "8")
        self.assertEqual(creator_text["collapsed"]["lineClamp"], "8")
        self.assertEqual(creator_text["collapsed"]["hyphens"], "auto")
        self.assertEqual(creator_text["collapsed"]["overflowWrap"], "break-word")
        self.assertFalse(creator_text["collapsed"]["buttonHidden"])
        self.assertEqual(creator_text["collapsed"]["buttonText"], "Show more")
        self.assertEqual(creator_text["collapsed"]["ariaExpanded"], "false")
        self.assertTrue(creator_text["collapsed"]["isCollapsed"])
        self.assertTrue(creator_text["collapsed"]["isClipped"])
        self.assertFalse(creator_text["expanded"]["isCollapsed"])
        self.assertTrue(creator_text["expanded"]["isExpanded"])
        self.assertFalse(creator_text["expanded"]["isClipped"])
        self.assertEqual(creator_text["expanded"]["buttonText"], "Show less")
        self.assertEqual(creator_text["expanded"]["ariaExpanded"], "true")

        self.page.set_viewport_size({"width": 360, "height": 900})
        self.open_page(self.description_project_path)
        project_text = self.page.evaluate(
            """
            async () => {
                const tick = () => new Promise(resolve => requestAnimationFrame(resolve));
                const root = document.querySelector('.expandable-text--project-description');
                const content = root.querySelector('[data-expandable-text-content]');
                const button = root.querySelector('[data-expandable-text-toggle]');

                content.innerHTML = Array.from(
                    { length: 16 },
                    (_, index) => `<p>Project description paragraph ${index + 1} with enough prose to exceed the limit.</p>`
                ).join('');
                window.cr4te.expandableText.update();
                await tick();
                await tick();

                const rootStyle = getComputedStyle(root);
                const contentStyle = getComputedStyle(content);
                return {
                    desktopLines: rootStyle.getPropertyValue('--expandable-text-lines').trim(),
                    mobileLines: rootStyle.getPropertyValue('--expandable-text-mobile-lines').trim(),
                    currentLines: rootStyle.getPropertyValue('--expandable-text-current-lines').trim(),
                    lineClamp: contentStyle.webkitLineClamp,
                    buttonHidden: button.hidden,
                    buttonText: button.textContent.trim(),
                    ariaExpanded: button.getAttribute('aria-expanded'),
                    isCollapsed: root.classList.contains('is-collapsed'),
                    isClipped: content.scrollHeight > content.clientHeight + 1,
                };
            }
            """
        )
        self.assertEqual(project_text["desktopLines"], "8")
        self.assertEqual(project_text["mobileLines"], "2")
        self.assertEqual(project_text["currentLines"], "2")
        self.assertEqual(project_text["lineClamp"], "2")
        self.assertFalse(project_text["buttonHidden"])
        self.assertEqual(project_text["buttonText"], "Show more")
        self.assertEqual(project_text["ariaExpanded"], "false")
        self.assertTrue(project_text["isCollapsed"])
        self.assertTrue(project_text["isClipped"])
        self.assertNoBrowserErrors()

    def test_image_less_detail_metadata_uses_responsive_equal_columns(self):
        self.open_disabled_portraits_page(self.creator_path)

        wide_layout = self.page.evaluate(
            """
            () => {
                const block = document.querySelector('.info-block');
                const entries = block.querySelectorAll('.meta-entry');
                const firstRect = entries[0].getBoundingClientRect();
                const secondRect = entries[1].getBoundingClientRect();
                return {
                    hasMedia: Boolean(block.querySelector('.info-block__media')),
                    entriesShareRow: Math.abs(firstRect.top - secondRect.top) < 1,
                    entriesEqualWidth: Math.abs(firstRect.width - secondRect.width) < 1,
                    entriesAlignContentToTop: Array.from(entries).every(
                        entry => getComputedStyle(entry).alignContent === 'start'
                    ),
                };
            }
            """
        )
        self.assertFalse(wide_layout["hasMedia"])
        self.assertTrue(wide_layout["entriesShareRow"])
        self.assertTrue(wide_layout["entriesEqualWidth"])
        self.assertTrue(wide_layout["entriesAlignContentToTop"])

        self.page.set_viewport_size({"width": 360, "height": 900})
        self.page.reload()
        narrow_layout = self.page.evaluate(
            """
            () => {
                const entries = document.querySelector('.info-block').querySelectorAll('.meta-entry');
                const firstRect = entries[0].getBoundingClientRect();
                const secondRect = entries[1].getBoundingClientRect();
                return secondRect.top >= firstRect.bottom;
            }
            """
        )
        self.assertTrue(narrow_layout)
        self.assertNoBrowserErrors()

    def test_creator_event_metadata_combines_date_and_place(self):
        self.open_page(self.combined_event_creator_path)

        born_entry = self.page.locator(".meta-entry").filter(has_text="Born")
        self.assertEqual(born_entry.count(), 1)
        self.assertEqual(born_entry.locator(".meta-label").inner_text(), "Born")
        self.assertEqual(born_entry.locator(".meta-value").inner_text(), "January 1986 in Berlin")
        self.assertEqual(self.page.get_by_text("Born in", exact=True).count(), 0)
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

    def test_detail_breadcrumb_truncates_without_moving_primary_header_controls(self):
        """Covers SITE-024."""
        self.open_page(self.audio_project_path)

        self.assertEqual(self.page.locator(".page-header > h1").count(), 0)
        self.assertEqual(self.page.locator(".page-content > h1").count(), 1)
        self.assertEqual(self.page.locator(".breadcrumb-section").count(), 1)
        self.assertEqual(self.page.locator(".breadcrumb-section > a").count(), 1)
        self.assertEqual(self.page.locator(".breadcrumb-section .nav-current").count(), 1)
        self.assertEqual(
            self.page.locator(".breadcrumb-section > .breadcrumb-separator--section").count(),
            2,
        )
        self.assertEqual(self.page.locator(".breadcrumb-separator--relation").inner_text(), "›")

        separator_alignment = self.page.evaluate(
            """
            () => {
                const primaryItems = Array.from(document.querySelector('.breadcrumb-list').children);
                const tags = primaryItems[primaryItems.length - 1].getBoundingClientRect();
                const separator = document
                    .querySelector('.breadcrumb-section > .breadcrumb-separator')
                    .getBoundingClientRect();
                const creator = document
                    .querySelector('.breadcrumb-section .breadcrumb-item')
                    .getBoundingClientRect();
                const separatorCenter = separator.left + separator.width / 2;
                return {
                    tagsToSeparator: separatorCenter - tags.right,
                    separatorToCreator: creator.left - separatorCenter,
                };
            }
            """
        )
        self.assertAlmostEqual(
            separator_alignment["tagsToSeparator"],
            separator_alignment["separatorToCreator"],
            delta=0.5,
        )

        breadcrumb_behavior = self.page.evaluate(
            """
            async () => {
                const section = document.querySelector('.breadcrumb-section');
                const items = Array.from(section.querySelectorAll('.breadcrumb-item'));
                const relation = section.querySelector('.breadcrumb-separator--relation');
                const tick = () => new Promise(resolve => requestAnimationFrame(resolve));

                items[0].textContent = 'Creator';
                items[0].dataset.overflowTitle = 'Creator';
                items[1].textContent = 'Project';
                items[1].dataset.overflowTitle = 'Project';
                section.style.maxWidth = 'none';
                section.style.flex = '1 1 auto';
                window.dispatchEvent(new Event('resize'));
                await tick();
                const shortTitles = items.map(item => item.getAttribute('title'));

                const longCreator = 'Creator With A Very Long Display Name That Needs Ellipsis';
                const longProject = 'Project With A Very Long Display Title That Needs Ellipsis';
                items[0].textContent = longCreator;
                items[0].dataset.overflowTitle = longCreator;
                items[1].textContent = longProject;
                items[1].dataset.overflowTitle = longProject;
                section.style.maxWidth = '12rem';
                section.style.flex = '0 1 12rem';
                window.dispatchEvent(new Event('resize'));
                await tick();
                await tick();

                const sectionRect = section.getBoundingClientRect();
                const itemRects = items.map(item => item.getBoundingClientRect());
                return {
                    sectionWhiteSpace: getComputedStyle(section).whiteSpace,
                    itemTextOverflows: items.map(item => getComputedStyle(item).textOverflow),
                    itemOverflows: items.map(item => item.scrollWidth > item.clientWidth),
                    itemTitles: items.map(item => item.getAttribute('title')),
                    shortTitles,
                    relationText: relation.textContent.trim(),
                    sameLine: Math.abs(itemRects[0].top - itemRects[1].top) < 0.5,
                    sectionHeight: sectionRect.height,
                    itemHeight: Math.max(...itemRects.map(rect => rect.height)),
                };
            }
            """
        )
        self.assertEqual(breadcrumb_behavior["sectionWhiteSpace"], "nowrap")
        self.assertTrue(all(value == "ellipsis" for value in breadcrumb_behavior["itemTextOverflows"]))
        self.assertTrue(all(breadcrumb_behavior["itemOverflows"]))
        self.assertEqual(breadcrumb_behavior["shortTitles"], [None, None])
        self.assertEqual(
            breadcrumb_behavior["itemTitles"],
            [
                "Creator With A Very Long Display Name That Needs Ellipsis",
                "Project With A Very Long Display Title That Needs Ellipsis",
            ],
        )
        self.assertEqual(breadcrumb_behavior["relationText"], "›")
        self.assertTrue(breadcrumb_behavior["sameLine"])
        self.assertLessEqual(breadcrumb_behavior["sectionHeight"], breadcrumb_behavior["itemHeight"] * 1.5)

        self.page.evaluate(
            """
            () => {
                const section = document.querySelector('.breadcrumb-section');
                section.style.maxWidth = '';
                section.style.flex = '';
                window.dispatchEvent(new Event('resize'));
            }
            """
        )
        self.page.set_viewport_size({"width": 820, "height": 900})
        squeezed = self.page.evaluate(
            """
            async () => {
                const tick = () => new Promise(resolve => requestAnimationFrame(resolve));
                await tick();
                const primary = document.querySelector('.breadcrumb-list').getBoundingClientRect();
                const section = document.querySelector('.breadcrumb-section').getBoundingClientRect();
                const leadingSeparator = document.querySelector(
                    '.breadcrumb-section > .breadcrumb-separator'
                ).getBoundingClientRect();
                const theme = document.querySelector('#theme-toggle').getBoundingClientRect();
                const sectionStyle = getComputedStyle(document.querySelector('.breadcrumb-section'));
                return {
                    primaryRight: primary.right,
                    sectionLeft: section.left,
                    sectionRight: section.right,
                    leadingSeparatorLeft: leadingSeparator.left,
                    themeLeft: theme.left,
                    sectionOverflow: sectionStyle.overflowX,
                    sectionWidth: section.width,
                };
            }
            """
        )
        self.assertGreaterEqual(squeezed["sectionLeft"], squeezed["primaryRight"] - 0.5)
        self.assertGreaterEqual(squeezed["leadingSeparatorLeft"], squeezed["primaryRight"] - 0.5)
        self.assertLessEqual(squeezed["sectionRight"], squeezed["themeLeft"] + 0.5)
        self.assertEqual(squeezed["sectionOverflow"], "hidden")
        self.assertGreaterEqual(squeezed["sectionWidth"], 0)

        colors = self.page.evaluate(
            """
            () => {
                const resolveColor = value => {
                    const probe = document.createElement('span');
                    probe.style.color = value;
                    document.body.appendChild(probe);
                    const color = getComputedStyle(probe).color;
                    probe.remove();
                    return color;
                };
                return {
                    separator: getComputedStyle(document.querySelector('.breadcrumb-separator')).color,
                    expectedSeparator: resolveColor('var(--theme-breadcrumb-separator)'),
                };
            }
            """
        )
        self.assertEqual(colors["separator"], colors["expectedSeparator"])

        self.page.set_viewport_size({"width": 640, "height": 900})
        narrow = self.page.evaluate(
            """
            () => {
                const rect = selector => document.querySelector(selector).getBoundingClientRect();
                const logo = rect('.site-logo-link');
                const primary = rect('.breadcrumb-list');
                const theme = rect('#theme-toggle');
                const sectionElement = document.querySelector('.breadcrumb-section');
                const section = sectionElement.getBoundingClientRect();
                const centers = [logo, primary, theme].map(box => box.top + box.height / 2);
                return {
                    firstRowCenterSpread: Math.max(...centers) - Math.min(...centers),
                    firstRowBottom: Math.max(logo.bottom, primary.bottom, theme.bottom),
                    sectionTop: section.top,
                    sectionWhiteSpace: getComputedStyle(sectionElement).whiteSpace,
                    leadingSeparatorDisplay: getComputedStyle(
                        sectionElement.querySelector('.breadcrumb-separator')
                    ).display,
                };
            }
            """
        )
        self.assertLessEqual(narrow["firstRowCenterSpread"], 0.5)
        self.assertGreater(narrow["sectionTop"], narrow["firstRowBottom"])
        self.assertEqual(narrow["sectionWhiteSpace"], "nowrap")
        self.assertEqual(narrow["leadingSeparatorDisplay"], "none")

        self.open_page(self.creator_path)
        self.assertEqual(self.page.locator(".page-header > h1").count(), 0)
        self.assertEqual(self.page.locator(".page-content > h1").count(), 1)
        self.assertEqual(self.page.locator(".breadcrumb-section").count(), 1)
        self.assertEqual(self.page.locator(".breadcrumb-section > a").count(), 0)
        self.assertEqual(self.page.locator(".breadcrumb-section .nav-current").count(), 1)
        self.assertEqual(
            self.page.locator(".breadcrumb-section > .breadcrumb-separator--section").count(),
            1,
        )
        self.assertNoBrowserErrors()

    def test_navigation_and_page_content_use_distinct_aligned_geometry(self):
        """Covers SITE-025."""
        self.open_page("index.html")

        geometry = self.page.evaluate(
            """
            () => {
                const headerElement = document.querySelector('.page-header');
                const contentElement = document.querySelector('.page-content');
                const hiddenTitleElement = document.querySelector('#page-title.visually-hidden');
                const searchElement = document.querySelector('.search-bar-wrapper');
                const panelElement = document.querySelector('.overview-layout');
                const header = headerElement.getBoundingClientRect();
                const content = contentElement.getBoundingClientRect();
                const search = searchElement.getBoundingClientRect();
                const panel = panelElement.getBoundingClientRect();
                const contentStyle = getComputedStyle(contentElement);
                const hiddenTitleStyle = getComputedStyle(hiddenTitleElement);
                const searchStyle = getComputedStyle(document.querySelector('.search-box'));
                return {
                    viewportWidth: innerWidth,
                    headerLeft: header.left,
                    headerRight: header.right,
                    contentLeft: content.left,
                    contentRight: content.right,
                    contentPaddingLeft: parseFloat(contentStyle.paddingLeft),
                    contentPaddingRight: parseFloat(contentStyle.paddingRight),
                    contentLabel: contentElement.getAttribute('aria-labelledby'),
                    hiddenTitleText: hiddenTitleElement.textContent.trim(),
                    hiddenTitlePosition: hiddenTitleStyle.position,
                    hiddenTitleWidth: hiddenTitleStyle.width,
                    hiddenTitleHeight: hiddenTitleStyle.height,
                    visibleTitleCount: document.querySelectorAll('.page-title').length,
                    searchLeft: search.left,
                    searchRight: search.right,
                    panelLeft: panel.left,
                    panelRight: panel.right,
                    searchHeight: search.height,
                    searchFontSize: searchStyle.fontSize,
                    bodyFontSize: getComputedStyle(document.body).fontSize,
                };
            }
            """
        )
        self.assertAlmostEqual(geometry["headerLeft"], 0, delta=0.25)
        self.assertAlmostEqual(geometry["headerRight"], geometry["viewportWidth"], delta=0.25)
        self.assertAlmostEqual(geometry["contentLeft"], 0, delta=0.25)
        self.assertAlmostEqual(geometry["contentRight"], geometry["viewportWidth"], delta=0.25)
        self.assertGreater(geometry["contentPaddingLeft"], 0)
        self.assertGreater(geometry["contentPaddingRight"], 0)
        self.assertEqual(geometry["contentLabel"], "page-title")
        self.assertGreater(len(geometry["hiddenTitleText"]), 0)
        self.assertEqual(geometry["hiddenTitlePosition"], "absolute")
        self.assertEqual(geometry["hiddenTitleWidth"], "1px")
        self.assertEqual(geometry["hiddenTitleHeight"], "1px")
        self.assertEqual(geometry["visibleTitleCount"], 0)
        self.assertAlmostEqual(geometry["searchLeft"], geometry["panelLeft"], delta=0.25)
        self.assertAlmostEqual(geometry["searchRight"], geometry["panelRight"], delta=0.25)
        self.assertGreater(geometry["searchHeight"], 0)
        self.assertEqual(geometry["searchFontSize"], geometry["bodyFontSize"])

        for theme in ("theme-frozen-aurora", "theme-forest-night", "theme-mono-terminal"):
            colors = self.page.evaluate(
                """
                theme => {
                    document.body.className = theme;
                    const headerStyle = getComputedStyle(document.querySelector('.page-header'));
                    const searchStyle = getComputedStyle(document.querySelector('.search-box'));
                    const bodyStyle = getComputedStyle(document.body);
                    const probe = document.createElement('span');
                    probe.style.backgroundColor = 'var(--theme-navigation-bg)';
                    probe.style.color = 'var(--theme-text)';
                    document.body.appendChild(probe);
                    const navigationBackground = getComputedStyle(probe).backgroundColor;
                    const themeText = getComputedStyle(probe).color;
                    probe.remove();
                    return {
                        navigationBackground: headerStyle.backgroundColor,
                        navigationToken: navigationBackground,
                        pageBackground: bodyStyle.backgroundColor,
                        searchBackground: searchStyle.backgroundColor,
                        searchText: searchStyle.color,
                        themeText,
                    };
                }
                """,
                theme,
            )
            self.assertEqual(colors["navigationBackground"], colors["navigationToken"])
            self.assertNotEqual(colors["navigationBackground"], colors["pageBackground"])
            self.assertEqual(colors["searchBackground"], colors["pageBackground"])
            self.assertEqual(colors["searchText"], colors["themeText"])
        self.assertNoBrowserErrors()

    def test_content_first_typography_hierarchy(self):
        """Covers SITE-026."""
        self.open_page(self.creator_path)

        sizes = self.page.evaluate(
            """
            () => {
                const markdown = document.querySelector('.markdown');
                const heading = document.createElement('h1');
                markdown.appendChild(heading);
                const result = {
                    body: parseFloat(getComputedStyle(document.body).fontSize),
                    sectionTitle: parseFloat(getComputedStyle(document.querySelector('.section-title')).fontSize),
                    markdownHeading: parseFloat(getComputedStyle(heading).fontSize),
                    visibleTitleCount: document.querySelectorAll('.page-title').length,
                };
                heading.remove();
                return result;
            }
            """
        )
        self.assertEqual(sizes["visibleTitleCount"], 0)
        self.assertGreater(sizes["sectionTitle"], sizes["body"])
        self.assertLessEqual(sizes["markdownHeading"], sizes["body"])
        self.assertNoBrowserErrors()

    def test_section_titles_truncate_and_show_tooltips_only_on_overflow(self):
        """Covers SITE-026."""
        self.open_page(self.creator_path)

        plain_title = self.page.evaluate(
            """
            async () => {
                const title = document.querySelector('.section-title');
                const tick = () => new Promise(resolve => requestAnimationFrame(resolve));

                title.textContent = 'Profile';
                title.style.maxWidth = 'none';
                window.dispatchEvent(new Event('resize'));
                await tick();
                const shortTitle = title.getAttribute('title');

                const longTitle = 'A Very Long Section Title That Should Stay On One Line And Use An Ellipsis';
                title.textContent = longTitle;
                title.style.maxWidth = '9rem';
                window.dispatchEvent(new Event('resize'));
                await tick();
                await tick();

                const style = getComputedStyle(title);
                return {
                    whiteSpace: style.whiteSpace,
                    textOverflow: style.textOverflow,
                    overflowX: style.overflowX,
                    isOverflowing: title.scrollWidth > title.clientWidth,
                    shortTitle,
                    longTitle: title.getAttribute('title'),
                };
            }
            """
        )
        self.assertEqual(plain_title["whiteSpace"], "nowrap")
        self.assertEqual(plain_title["textOverflow"], "ellipsis")
        self.assertEqual(plain_title["overflowX"], "hidden")
        self.assertTrue(plain_title["isOverflowing"])
        self.assertIsNone(plain_title["shortTitle"])
        self.assertEqual(
            plain_title["longTitle"],
            "A Very Long Section Title That Should Stay On One Line And Use An Ellipsis",
        )

        self.open_page(self.caption_project_path)
        action_title = self.page.evaluate(
            """
            async () => {
                const sectionTitle = document.querySelector('.image-caption-section .section-title');
                const text = sectionTitle.querySelector(':scope > span');
                const button = sectionTitle.querySelector('.caption-toggle-btn');
                const tick = () => new Promise(resolve => requestAnimationFrame(resolve));
                const longTitle = 'A Very Long Image Section Title That Must Truncate Before The Action Button';

                text.textContent = longTitle;
                sectionTitle.style.maxWidth = '12rem';
                window.dispatchEvent(new Event('resize'));
                await tick();
                await tick();

                const sectionRect = sectionTitle.getBoundingClientRect();
                const buttonRect = button.getBoundingClientRect();
                const textStyle = getComputedStyle(text);
                return {
                    textWhiteSpace: textStyle.whiteSpace,
                    textOverflow: textStyle.textOverflow,
                    textIsOverflowing: text.scrollWidth > text.clientWidth,
                    textTitle: text.getAttribute('title'),
                    sectionTitle: sectionTitle.getAttribute('title'),
                    buttonVisible: buttonRect.width > 0 && buttonRect.right <= sectionRect.right + 0.5,
                };
            }
            """
        )
        self.assertEqual(action_title["textWhiteSpace"], "nowrap")
        self.assertEqual(action_title["textOverflow"], "ellipsis")
        self.assertTrue(action_title["textIsOverflowing"])
        self.assertEqual(
            action_title["textTitle"],
            "A Very Long Image Section Title That Must Truncate Before The Action Button",
        )
        self.assertIsNone(action_title["sectionTitle"])
        self.assertTrue(action_title["buttonVisible"])
        self.assertNoBrowserErrors()

    def test_text_overflow_policy_matches_content_role(self):
        """Covers SITE-026."""
        self.open_page(self.audio_project_path)

        audio = self.page.evaluate(
            """
            async () => {
                const tick = () => new Promise(resolve => requestAnimationFrame(resolve));
                const track = document.querySelector('.track-title-text');
                const row = track.closest('.track-title');
                const longTitle = 'A Very Long Track Title That Should Stay On One Line With An Ellipsis';

                track.textContent = longTitle;
                row.style.maxWidth = '8rem';
                window.dispatchEvent(new Event('resize'));
                await tick();
                await tick();

                const style = getComputedStyle(track);
                return {
                    whiteSpace: style.whiteSpace,
                    textOverflow: style.textOverflow,
                    overflowX: style.overflowX,
                    isOverflowing: track.scrollWidth > track.clientWidth,
                    title: track.getAttribute('title'),
                };
            }
            """
        )
        self.assertEqual(audio["whiteSpace"], "nowrap")
        self.assertEqual(audio["textOverflow"], "ellipsis")
        self.assertEqual(audio["overflowX"], "hidden")
        self.assertTrue(audio["isOverflowing"])
        self.assertEqual(
            audio["title"],
            "A Very Long Track Title That Should Stay On One Line With An Ellipsis",
        )

        self.open_page("tags.html")
        tags = self.page.evaluate(
            """
            async () => {
                const tick = () => new Promise(resolve => requestAnimationFrame(resolve));
                const longTag = 'A Very Long Tag Label That Should Stay On One Line';
                const tag = document.querySelector('.tag-category .tag');
                const category = document.querySelector('.tag-category-label');

                tag.textContent = longTag;
                tag.style.width = '6rem';
                category.textContent = longTag;
                category.style.width = '6rem';
                window.dispatchEvent(new Event('resize'));
                await tick();
                await tick();

                const measure = element => {
                    const style = getComputedStyle(element);
                    return {
                        whiteSpace: style.whiteSpace,
                        textOverflow: style.textOverflow,
                        overflowX: style.overflowX,
                        isOverflowing: element.scrollWidth > element.clientWidth,
                        title: element.getAttribute('title'),
                    };
                };

                return {
                    tag: measure(tag),
                    category: measure(category),
                    longTag,
                };
            }
            """
        )
        for label in ("tag", "category"):
            with self.subTest(label=label):
                self.assertEqual(tags[label]["whiteSpace"], "nowrap")
                self.assertEqual(tags[label]["textOverflow"], "ellipsis")
                self.assertEqual(tags[label]["overflowX"], "hidden")
                self.assertTrue(tags[label]["isOverflowing"])
                self.assertEqual(tags[label]["title"], tags["longTag"])

        self.open_page("index.html")
        image_caption = self.page.evaluate(
            """
            async () => {
                const tick = () => new Promise(resolve => requestAnimationFrame(resolve));
                const caption = document.querySelector('#imageGallery .image-card .image-caption');
                const longCaption = 'A long image caption that should wrap naturally but stop after two displayed lines';

                caption.textContent = longCaption;
                caption.style.width = '7rem';
                window.dispatchEvent(new Event('resize'));
                await tick();
                await tick();

                const style = getComputedStyle(caption);
                return {
                    lineClamp: style.webkitLineClamp,
                    whiteSpace: style.whiteSpace,
                    overflowY: style.overflowY,
                    isClipped: caption.scrollHeight > caption.clientHeight + 1,
                    title: caption.getAttribute('title'),
                };
            }
            """
        )
        self.assertEqual(image_caption["lineClamp"], "2")
        self.assertEqual(image_caption["whiteSpace"], "normal")
        self.assertEqual(image_caption["overflowY"], "hidden")
        self.assertTrue(image_caption["isClipped"])
        self.assertEqual(
            image_caption["title"],
            "A long image caption that should wrap naturally but stop after two displayed lines",
        )

        self.open_disabled_portraits_page("index.html")
        text_card = self.page.evaluate(
            """
            async () => {
                const tick = () => new Promise(resolve => requestAnimationFrame(resolve));
                const name = document.querySelector('.creator-text-card__name');
                const summary = document.querySelector('.creator-text-card__summary');
                const longName = 'A Very Long Creator Name That Should Wrap But Clamp After Two Lines';
                const longSummary = 'A Very Long Count Summary That Should Wrap But Clamp After Two Lines';

                name.textContent = longName;
                name.style.width = '7rem';
                summary.textContent = longSummary;
                summary.style.width = '7rem';
                window.dispatchEvent(new Event('resize'));
                await tick();
                await tick();

                const measure = element => {
                    const style = getComputedStyle(element);
                    return {
                        lineClamp: style.webkitLineClamp,
                        whiteSpace: style.whiteSpace,
                        overflowY: style.overflowY,
                        isClipped: element.scrollHeight > element.clientHeight + 1,
                        title: element.getAttribute('title'),
                    };
                };

                return {
                    name: measure(name),
                    summary: measure(summary),
                    longName,
                    longSummary,
                };
            }
            """
        )
        self.assertEqual(text_card["name"]["lineClamp"], "2")
        self.assertEqual(text_card["name"]["whiteSpace"], "normal")
        self.assertEqual(text_card["name"]["overflowY"], "hidden")
        self.assertTrue(text_card["name"]["isClipped"])
        self.assertEqual(text_card["name"]["title"], text_card["longName"])
        self.assertEqual(text_card["summary"]["lineClamp"], "2")
        self.assertEqual(text_card["summary"]["whiteSpace"], "normal")
        self.assertEqual(text_card["summary"]["overflowY"], "hidden")
        self.assertTrue(text_card["summary"]["isClipped"])
        self.assertEqual(text_card["summary"]["title"], text_card["longSummary"])

        self.open_page(self.creator_path)
        detail_text = self.page.evaluate(
            """
            () => {
                const prose = document.querySelector('.text-content');
                const meta = document.querySelector('.meta-value');
                const proseStyle = getComputedStyle(prose);
                const metaStyle = getComputedStyle(meta);

                return {
                    proseWhiteSpace: proseStyle.whiteSpace,
                    proseTextOverflow: proseStyle.textOverflow,
                    proseTitle: prose.getAttribute('title'),
                    metaWhiteSpace: metaStyle.whiteSpace,
                    metaTextOverflow: metaStyle.textOverflow,
                    metaTitle: meta.getAttribute('title'),
                };
            }
            """
        )
        self.assertEqual(detail_text["proseWhiteSpace"], "normal")
        self.assertEqual(detail_text["proseTextOverflow"], "clip")
        self.assertIsNone(detail_text["proseTitle"])
        self.assertEqual(detail_text["metaWhiteSpace"], "normal")
        self.assertEqual(detail_text["metaTextOverflow"], "clip")
        self.assertIsNone(detail_text["metaTitle"])
        self.assertNoBrowserErrors()

    def test_page_section_and_gallery_spacing_follow_layout_tokens(self):
        """Covers SITE-027."""
        self.open_page("index.html")

        overview = self.page.evaluate(
            """
            () => {
                const contentElement = document.querySelector('.page-content');
                const content = contentElement.getBoundingClientRect();
                const contentStyle = getComputedStyle(contentElement);
                const search = document.querySelector('.search-bar-wrapper').getBoundingClientRect();
                const searchStyle = getComputedStyle(document.querySelector('.search-bar-wrapper'));
                const panelElement = document.querySelector('.overview-layout');
                const panel = panelElement.getBoundingClientRect();
                const panelStyle = getComputedStyle(panelElement);
                const galleryElement = document.querySelector('.card-gallery');
                const gallery = galleryElement.getBoundingClientRect();
                const card = document.querySelector('.image-card');
                const cardCaption = card.querySelector('.image-caption');
                return {
                    contentPadding: [
                        contentStyle.paddingTop,
                        contentStyle.paddingRight,
                        contentStyle.paddingBottom,
                        contentStyle.paddingLeft,
                    ],
                    contentLeft: content.left,
                    contentRight: content.right,
                    searchPanelGap: panel.top - search.bottom,
                    searchMarginBottom: searchStyle.marginBottom,
                    bottomGap: content.bottom - panel.bottom,
                    cardGap: getComputedStyle(galleryElement).gap,
                    cardPaddingBottom: getComputedStyle(card).paddingBottom,
                    cardCaptionPaddingTop: getComputedStyle(cardCaption).paddingTop,
                    overviewTopGap: gallery.top - panel.top - parseFloat(panelStyle.borderTopWidth),
                };
            }
            """
        )
        content_padding = [float(value.removesuffix("px")) for value in overview["contentPadding"]]
        card_gap = float(overview["cardGap"].removesuffix("px"))
        card_text_space = float(overview["cardPaddingBottom"].removesuffix("px"))
        self.assertTrue(all(value > 0 for value in content_padding))
        self.assertAlmostEqual(
            overview["searchPanelGap"],
            float(overview["searchMarginBottom"].removesuffix("px")),
            delta=0.25,
        )
        self.assertAlmostEqual(overview["bottomGap"], content_padding[2], delta=0.25)
        self.assertGreater(card_gap, overview["searchPanelGap"])
        self.assertEqual(overview["cardPaddingBottom"], overview["cardCaptionPaddingTop"])
        self.assertLess(card_text_space, card_gap)
        self.assertAlmostEqual(overview["overviewTopGap"], card_gap, delta=0.25)

        self.open_page(self.creator_path)
        detail = self.page.evaluate(
            """
            () => {
                const layout = document.querySelector('.two-column-layout').getBoundingClientRect();
                const left = document.querySelector('.left-column').getBoundingClientRect();
                const right = document.querySelector('.right-column').getBoundingClientRect();
                const leftStyle = getComputedStyle(document.querySelector('.left-column'));
                const contentElement = document.querySelector('.page-content');
                const content = contentElement.getBoundingClientRect();
                const contentStyle = getComputedStyle(contentElement);
                const detailStyle = getComputedStyle(document.querySelector('.detail-content'));
                const regularSectionContent = document.querySelector(
                    '.section-box > hr + .section-content:not(.text-content)'
                );
                const regularDivider = regularSectionContent.previousElementSibling;
                const regularFirstChild = regularSectionContent.firstElementChild;
                return {
                    paneGap: right.left - left.right,
                    configuredPaneGap: detailStyle.gap,
                    leftGap: layout.left - content.left,
                    rightGap: content.right - layout.right,
                    bottomGap: content.bottom - layout.bottom,
                    contentPaddingRight: contentStyle.paddingRight,
                    contentPaddingBottom: contentStyle.paddingBottom,
                    contentPaddingLeft: contentStyle.paddingLeft,
                    panelPaddingTop: leftStyle.paddingTop,
                    panelPaddingBottom: leftStyle.paddingBottom,
                    sectionContentPaddingTop: getComputedStyle(regularSectionContent).paddingTop,
                    sectionContentDividerGap:
                        regularFirstChild.getBoundingClientRect().top - regularDivider.getBoundingClientRect().bottom,
                };
            }
            """
        )
        self.assertAlmostEqual(
            detail["paneGap"],
            float(detail["configuredPaneGap"].removesuffix("px")),
            delta=0.25,
        )
        self.assertAlmostEqual(
            detail["leftGap"],
            float(detail["contentPaddingLeft"].removesuffix("px")),
            delta=0.25,
        )
        self.assertAlmostEqual(
            detail["rightGap"],
            float(detail["contentPaddingRight"].removesuffix("px")),
            delta=0.25,
        )
        self.assertAlmostEqual(
            detail["bottomGap"],
            float(detail["contentPaddingBottom"].removesuffix("px")),
            delta=0.25,
        )
        panel_padding_top = float(detail["panelPaddingTop"].removesuffix("px"))
        panel_padding_bottom = float(detail["panelPaddingBottom"].removesuffix("px"))
        self.assertGreater(panel_padding_top, 0)
        self.assertGreaterEqual(panel_padding_bottom, panel_padding_top)
        section_padding_top = float(detail["sectionContentPaddingTop"].removesuffix("px"))
        self.assertGreater(section_padding_top, 0)
        self.assertGreaterEqual(panel_padding_top, section_padding_top)
        self.assertAlmostEqual(detail["sectionContentDividerGap"], section_padding_top, delta=0.25)

        markdown_last_margin = self.page.locator(".text-content > :last-child").first.evaluate(
            "element => getComputedStyle(element).marginBottom"
        )
        self.assertEqual(markdown_last_margin, "0px")

        self.open_page(self.caption_project_path)
        gallery_gap = self.page.locator(".image-gallery--justified").first.evaluate(
            "element => getComputedStyle(element).gap"
        )
        self.assertGreater(float(gallery_gap.removesuffix("px")), 0)
        caption_spacing = self.page.locator(".image-gallery--justified .image-caption").first.evaluate(
            "element => ({ top: getComputedStyle(element).marginTop, left: getComputedStyle(element).marginLeft })"
        )
        self.assertEqual(caption_spacing["left"], "0px")
        self.assertLess(
            float(caption_spacing["top"].removesuffix("px")),
            float(gallery_gap.removesuffix("px")),
        )
        self.assertNoBrowserErrors()

    def test_navigation_surfaces_and_panels_follow_selected_theme(self):
        """Covers SITE-025."""
        self.open_page(self.creator_path)

        def border(selector):
            return self.page.locator(selector).evaluate(
                "element => [getComputedStyle(element).borderTopWidth, "
                "getComputedStyle(element).borderTopColor]"
            )

        frozen_panel_border = border(".left-column")
        frozen_shell = self.page.evaluate(
            """
            () => {
                const header = getComputedStyle(document.querySelector('.page-header'));
                return {
                    bodyBackground: getComputedStyle(document.body).backgroundColor,
                    navigationBackground: header.backgroundColor,
                    navigationBorder: [header.borderBottomWidth, header.borderBottomColor],
                    visibleTitleCount: document.querySelectorAll('.page-title').length,
                };
            }
            """
        )
        self.assertNotEqual(frozen_shell["navigationBackground"], frozen_shell["bodyBackground"])
        self.assertGreater(float(frozen_shell["navigationBorder"][0].removesuffix("px")), 0)
        self.assertEqual(frozen_shell["visibleTitleCount"], 0)
        self.assertGreater(float(frozen_panel_border[0].removesuffix("px")), 0)

        self.page.get_by_role("button", name="Themes").click()
        self.page.get_by_role("menuitemradio", name="Forest Night").click()
        forest_panel_border = border(".left-column")
        forest_shell = self.page.evaluate(
            """
            () => {
                return {
                    bodyBackground: getComputedStyle(document.body).backgroundColor,
                    navigationBackground: getComputedStyle(document.querySelector('.page-header')).backgroundColor,
                    visibleTitleCount: document.querySelectorAll('.page-title').length,
                };
            }
            """
        )
        self.assertNotEqual(forest_shell["navigationBackground"], forest_shell["bodyBackground"])
        self.assertEqual(forest_shell["visibleTitleCount"], 0)
        self.assertNotEqual(forest_panel_border[1], frozen_panel_border[1])

        self.assertEqual(border(".left-column"), forest_panel_border)
        self.assertEqual(border(".right-column"), forest_panel_border)
        divider_and_title = self.page.evaluate(
            """
            () => ({
                divider: getComputedStyle(document.querySelector('.section-box hr')).borderTopColor,
                title: getComputedStyle(document.querySelector('.section-title')).color,
            })
            """
        )
        self.assertNotEqual(divider_and_title["divider"], forest_panel_border[1])
        self.assertNotEqual(divider_and_title["divider"], divider_and_title["title"])

        self.page.evaluate("document.body.className = 'theme-frozen-aurora'")
        frozen_divider_and_title = self.page.evaluate(
            """
            () => ({
                divider: getComputedStyle(document.querySelector('.section-box hr')).borderTopColor,
                title: getComputedStyle(document.querySelector('.section-title')).color,
            })
            """
        )
        self.assertNotEqual(frozen_divider_and_title["divider"], frozen_panel_border[1])
        self.assertNotEqual(frozen_divider_and_title["divider"], frozen_divider_and_title["title"])
        self.assertNotEqual(frozen_divider_and_title["divider"], divider_and_title["divider"])
        self.assertNoBrowserErrors()

    def test_theme_specific_pagination_radius_and_optional_audio_track_separators_resolve(self):
        self.open_paginated_page("index.html")
        pagination = self.page.evaluate(
            """
            () => {
                const button = document.querySelector('.pagination-controls button');
                const style = getComputedStyle(button);
                const probe = document.createElement('span');
                probe.style.borderRadius = 'var(--theme-pagination-button-radius)';
                document.body.appendChild(probe);
                const token = getComputedStyle(probe).borderRadius;
                probe.remove();
                return {
                    radius: style.borderRadius,
                    token,
                };
            }
            """
        )
        self.assertEqual(pagination["radius"], pagination["token"])
        self.assertGreater(float(pagination["radius"].removesuffix("px")), 0)

        self.open_page(self.audio_project_path)
        tracks = self.page.locator(".audio-gallery li")
        self.assertGreater(tracks.count(), 1)
        track_separators = self.page.evaluate(
            """
            () => {
                const rows = document.querySelectorAll('.audio-gallery li');
                const before = getComputedStyle(rows[0]).borderBottomWidth;
                document.body.style.setProperty('--theme-track-separator', 'rgb(12, 34, 56)');
                document.body.style.setProperty('--theme-track-separator-width', '2px');
                const firstRow = getComputedStyle(rows[0]);
                const lastRow = getComputedStyle(rows[rows.length - 1]);
                return {
                    defaultWidth: before,
                    firstSeparatorWidth: firstRow.borderBottomWidth,
                    firstSeparatorColor: firstRow.borderBottomColor,
                    lastSeparatorWidth: lastRow.borderBottomWidth,
                };
            }
            """
        )
        self.assertEqual(track_separators["defaultWidth"], "0px")
        self.assertEqual(track_separators["firstSeparatorWidth"], "2px")
        self.assertEqual(track_separators["firstSeparatorColor"], "rgb(12, 34, 56)")
        self.assertEqual(track_separators["lastSeparatorWidth"], "0px")
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
        self.assertGreater(float(keyboard_outline["width"].removesuffix("px")), 0)

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
            self.assertLessEqual(float(focus["offset"].removesuffix("px")), 0)
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
        self.assertLessEqual(float(styles["cardOutlineOffset"].removesuffix("px")), 0)
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
        startup_state = self.page.evaluate(
            """
            () => {
                const gallery = document.querySelector("#imageGallery");
                return {
                    ready: gallery.classList.contains("gallery-ready"),
                    visibility: getComputedStyle(gallery).visibility,
                };
            }
            """
        )

        self.assertIn("lazy", loading_modes)
        self.assertTrue(startup_state["ready"])
        self.assertEqual(startup_state["visibility"], "visible")
        self.assertAspectGalleryBuilt()
        self.assertNoBrowserErrors()

    def test_js_gallery_startup_layout_is_hidden_until_builder_runs(self):
        self.page.route("**/aspect_gallery_builder.js", lambda route: route.abort())
        self.page.goto(f"{self.base_url}/site/index.html")
        self.page.wait_for_load_state("load")

        startup_state = self.page.evaluate(
            """
            () => {
                const gallery = document.querySelector("#imageGallery");
                return {
                    jsEnabled: document.documentElement.classList.contains("cr4te-js"),
                    ready: gallery.classList.contains("gallery-ready"),
                    visibility: getComputedStyle(gallery).visibility,
                    wrappers: gallery.querySelectorAll(".image-wrapper").length,
                };
            }
            """
        )

        self.assertTrue(startup_state["jsEnabled"])
        self.assertFalse(startup_state["ready"])
        self.assertEqual(startup_state["visibility"], "hidden")
        self.assertGreater(startup_state["wrappers"], 0)

    def test_no_javascript_overview_gallery_fallback_remains_visible(self):
        """Covers SITE-032."""
        page = self.browser.new_page(java_script_enabled=False)
        try:
            page.goto(f"{self.base_url}/site/index.html")
            page.wait_for_load_state("load")

            startup_state = page.evaluate(
                """
                () => {
                    const gallery = document.querySelector("#imageGallery");
                    return {
                        jsEnabled: document.documentElement.classList.contains("cr4te-js"),
                        ready: gallery.classList.contains("gallery-ready"),
                        visibility: getComputedStyle(gallery).visibility,
                        wrappers: gallery.querySelectorAll(".image-wrapper").length,
                    };
                }
                """
            )

            self.assertFalse(startup_state["jsEnabled"])
            self.assertFalse(startup_state["ready"])
            self.assertEqual(startup_state["visibility"], "visible")
            self.assertGreater(startup_state["wrappers"], 0)
        finally:
            page.close()

    def test_aspect_gallery_builder_falls_back_for_malformed_aspect_ratios(self):
        self.open_page("index.html")

        aspect_ratios = self.page.evaluate(
            """
            () => ["3/2/1", "3.0/2", "3:2", "0/2", "-3/2"].map(value => {
                const gallery = document.createElement("div");
                gallery.className = "image-gallery--aspect";
                gallery.dataset.aspectRatio = value;
                gallery.innerHTML = '<div class="image-wrapper"><img alt=""></div>';
                document.body.appendChild(gallery);

                window.cr4te.galleries.rebuildAspect(gallery);
                const aspectRatio = gallery.querySelector(".aspect-ratio-box").style.aspectRatio;
                gallery.remove();
                return aspectRatio;
            })
            """
        )

        self.assertEqual(aspect_ratios, ["1 / 1"] * 5)
        self.assertNoBrowserErrors()

    def test_paginated_aspect_gallery_falls_back_for_malformed_aspect_ratio(self):
        self.open_paginated_page("index.html")

        self.page.evaluate(
            """
            () => {
                const gallery = document.querySelector("#imageGallery");
                gallery.dataset.aspectRatio = "3/2/1";
                window.dispatchEvent(new Event("resize"));
            }
            """
        )

        self.assertGreater(self.page.locator(".pagination-controls button").count(), 0)
        self.assertAspectGalleryBuilt()
        self.assertNoBrowserErrors()

    def test_paginated_gallery_rebuilds_layout_after_page_change(self):
        """Covers SITE-027, SITE-032, and SITE-035."""
        self.open_paginated_page("index.html")

        self.assertEqual(self.page.locator("#imageGallery .image-wrapper").count(), 1)
        self.assertGreater(self.page.locator(".pagination-controls button").count(), 0)
        pagination_padding = self.page.locator(".pagination-controls").evaluate(
            "element => getComputedStyle(element).paddingTop"
        )
        self.assertGreater(float(pagination_padding.removesuffix("px")), 0)
        self.assertAspectGalleryBuilt()

        self.page.click(".pagination-next")
        self.page.wait_for_timeout(150)

        self.assertEqual(self.page.locator("#imageGallery .image-wrapper").count(), 1)
        self.assertAspectGalleryBuilt()
        self.assertNoBrowserErrors()

    def test_paginated_galleries_use_configured_row_count_for_aspect_and_justified_layouts(self):
        """Covers SITE-035."""
        self.open_page("index.html")

        row_counts = self.page.evaluate(
            """
            () => {
                function rowsFor(gallery) {
                    const tops = Array.from(gallery.querySelectorAll('.image-wrapper'))
                        .map(wrapper => Math.round(wrapper.getBoundingClientRect().top));
                    return new Set(tops).size;
                }

                function visibleCount(gallery) {
                    return gallery.querySelectorAll('.image-wrapper').length;
                }

                function buildGallery(id, className, width, maxHeight, wrappersHtml) {
                    const section = document.createElement('section');
                    section.className = 'section-box';
                    section.innerHTML = `<div class="section-content"><div id="${id}" class="${className}" data-image-max-height="${maxHeight}" data-aspect-ratio="1/1" data-page-rows="2"></div></div>`;
                    document.body.appendChild(section);

                    const gallery = section.querySelector(`#${id}`);
                    gallery.style.width = `${width}px`;
                    gallery.style.maxWidth = `${width}px`;
                    gallery.innerHTML = wrappersHtml;

                    const wrappers = Array.from(gallery.querySelectorAll('.image-wrapper'));
                    window.cr4te.pagination.mount(gallery, wrappers, 2);
                    return gallery;
                }

                const aspectGallery = buildGallery(
                    'synthetic-aspect-gallery',
                    'image-gallery--aspect',
                    600,
                    200,
                    Array.from({ length: 7 }, (_, index) => `<div class="image-wrapper" data-width="100" data-height="100"><img alt="Aspect ${index}"></div>`).join('')
                );

                const justifiedGallery = buildGallery(
                    'synthetic-justified-gallery',
                    'image-gallery--justified',
                    600,
                    200,
                    Array.from({ length: 5 }, (_, index) => `<div class="image-wrapper" data-width="200" data-height="100"><img alt="Justified ${index}"></div>`).join('')
                );

                const initial = {
                    aspectCount: visibleCount(aspectGallery),
                    aspectRows: rowsFor(aspectGallery),
                    justifiedCount: visibleCount(justifiedGallery),
                    justifiedRows: rowsFor(justifiedGallery),
                };

                aspectGallery.style.width = '400px';
                aspectGallery.style.maxWidth = '400px';
                window.dispatchEvent(new Event('resize'));

                return {
                    ...initial,
                    reflowedAspectCount: visibleCount(aspectGallery),
                    reflowedAspectRows: rowsFor(aspectGallery),
                };
            }
            """
        )

        self.assertEqual(row_counts["aspectCount"], 6)
        self.assertEqual(row_counts["aspectRows"], 2)
        self.assertEqual(row_counts["justifiedCount"], 4)
        self.assertEqual(row_counts["justifiedRows"], 2)
        self.assertEqual(row_counts["reflowedAspectCount"], 4)
        self.assertEqual(row_counts["reflowedAspectRows"], 2)
        self.assertNoBrowserErrors()

    def test_reduced_motion_disables_shared_transitions_and_smooth_pagination_scroll(self):
        self.page.emulate_media(reduced_motion="reduce")
        self.open_paginated_page("index.html")
        self.page.evaluate(
            """
            () => {
                const overview = document.querySelector(".overview-layout");
                overview.style.height = "100px";
                window.__scrollBehaviors = [];
                overview.scrollTo = options => window.__scrollBehaviors.push(options.behavior);
            }
            """
        )

        motion = self.page.evaluate(
            """
            () => {
                const root = getComputedStyle(document.documentElement);
                const button = document.querySelector(".pagination-controls button:not(:disabled)");
                return {
                    prefersReducedMotion: window.utils.prefersReducedMotion(),
                    interaction: root.getPropertyValue("--motion-interaction").trim(),
                    visibility: root.getPropertyValue("--motion-visibility").trim(),
                    buttonDuration: getComputedStyle(button).transitionDuration,
                };
            }
            """
        )
        self.page.click(".pagination-next")
        self.page.wait_for_timeout(50)

        self.assertTrue(motion["prefersReducedMotion"])
        self.assertEqual(motion["interaction"], "0s")
        self.assertEqual(motion["visibility"], "0s")
        self.assertEqual(set(motion["buttonDuration"].split(", ")), {"0s"})
        self.assertEqual(self.page.evaluate("window.__scrollBehaviors"), ["auto"])
        self.assertNoBrowserErrors()

    def test_pagination_hover_feedback_preserves_button_geometry(self):
        self.open_paginated_page("index.html")
        button = self.page.locator(".pagination-next")
        before = button.bounding_box()
        transitions = button.evaluate(
            "element => getComputedStyle(element).transitionProperty.split(', ').sort()"
        )

        button.hover()
        self.page.wait_for_timeout(250)
        after = button.bounding_box()

        self.assertEqual(transitions, ["background-color", "color"])
        self.assertEqual(before["width"], after["width"])
        self.assertEqual(before["height"], after["height"])
        self.assertNoBrowserErrors()

    def test_media_badges_remain_visible_for_hover_focus_and_touch_input(self):
        self.open_page("index.html")
        badge_group = self.page.locator(".media-type-badges").first
        card = badge_group.locator("xpath=ancestor::*[contains(@class, 'image-card')]")
        card_link = card.locator(":scope > a")

        self.assertEqual(badge_group.evaluate("element => getComputedStyle(element).opacity"), "0")
        self.assertEqual(
            badge_group.evaluate("element => getComputedStyle(element).transitionProperty"),
            "opacity",
        )

        card.hover()
        self.page.wait_for_timeout(250)
        self.assertEqual(badge_group.evaluate("element => getComputedStyle(element).opacity"), "1")

        self.page.mouse.move(0, 0)
        self.page.wait_for_timeout(250)
        self.assertEqual(badge_group.evaluate("element => getComputedStyle(element).opacity"), "0")

        card_link.focus()
        self.page.wait_for_timeout(250)
        self.assertEqual(badge_group.evaluate("element => getComputedStyle(element).opacity"), "1")

        touch_page = self.browser.new_page(has_touch=True, viewport={"width": 390, "height": 844})
        try:
            touch_page.goto(f"{self.base_url}/site/index.html")
            touch_page.wait_for_load_state("load")
            touch_badge_group = touch_page.locator(".media-type-badges").first
            self.assertEqual(touch_badge_group.evaluate("element => getComputedStyle(element).opacity"), "1")
        finally:
            touch_page.close()

        self.assertNoBrowserErrors()

    def test_theme_dropdown_applies_selected_theme(self):
        self.open_page("index.html")

        self.page.click("#theme-toggle")
        self.assertTrue(self.page.locator("#theme-panel").is_visible())
        self.page.click("[data-theme='theme-forest-night']")

        root_class = self.page.locator("html").get_attribute("class") or ""
        body_class = self.page.locator("body").get_attribute("class") or ""
        self.assertIn("theme-forest-night", root_class)
        self.assertIn("theme-forest-night", body_class)
        self.assertFalse(self.page.locator("#theme-panel").is_visible())

    def test_saved_theme_is_applied_before_theme_menu_initializes(self):
        """Covers SITE-022."""
        self.page.add_init_script("localStorage.setItem('cr4te_theme', 'theme-forest-night');")
        self.page.route("**/theme_selector.js", lambda route: route.abort())

        self.page.goto(f"{self.base_url}/site/index.html")
        self.page.wait_for_load_state("domcontentloaded")

        theme_state = self.page.evaluate(
            """
            () => ({
                rootClass: document.documentElement.className,
                bodyClass: document.body.className,
                resolvedTheme: document.documentElement.dataset.resolvedTheme,
                bodyBackground: getComputedStyle(document.body).backgroundColor,
            })
            """
        )

        self.assertIn("theme-forest-night", theme_state["rootClass"])
        self.assertNotIn("theme-frozen-aurora", theme_state["rootClass"])
        self.assertNotIn("theme-frozen-aurora", theme_state["bodyClass"])
        self.assertEqual(theme_state["resolvedTheme"], "theme-forest-night")
        self.assertTrue(theme_state["bodyBackground"])

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
        """Covers SITE-018 and SITE-034."""
        self.open_page(self.creator_path)
        metadata_label_style = self.page.locator(".meta-label").first.evaluate(
            """
            label => {
                const style = getComputedStyle(label);
                return {
                    color: style.color,
                    fontSize: style.fontSize,
                    fontWeight: style.fontWeight,
                };
            }
            """
        )

        self.open_page("tags.html")

        self.assertEqual(self.page.locator("body").evaluate("body => getComputedStyle(body).display"), "block")
        self.assertGreater(self.page.locator(".tag-category").count(), 0)
        tag_category_labels = self.page.locator(".tag-category-label")
        self.assertGreater(tag_category_labels.count(), 0)
        self.assertTrue(all(not label.endswith(":") for label in tag_category_labels.all_inner_texts()))
        self.assertGreater(self.page.locator(".tag-category .tag").count(), 0)
        tag_category_label_style = tag_category_labels.first.evaluate(
            """
            label => {
                const style = getComputedStyle(label);
                return {
                    color: style.color,
                    fontSize: style.fontSize,
                    fontWeight: style.fontWeight,
                };
            }
            """
        )
        self.assertEqual(tag_category_label_style, metadata_label_style)

        tag_grid = self.page.locator(".tag-list")
        desktop_grid = tag_grid.evaluate(
            """
            element => ({
                display: getComputedStyle(element).display,
                columns: getComputedStyle(element).gridTemplateColumns.split(' ').length,
                gap: parseFloat(getComputedStyle(element).gap),
            })
            """
        )
        self.assertEqual(desktop_grid["display"], "grid")
        self.assertGreater(desktop_grid["columns"], 1)
        self.assertGreater(desktop_grid["gap"], 0)

        self.page.set_viewport_size({"width": 390, "height": 844})
        mobile_columns = tag_grid.evaluate(
            "element => getComputedStyle(element).gridTemplateColumns.split(' ').length"
        )
        self.assertEqual(mobile_columns, 1)
        self.assertEqual(self.page.evaluate("typeof window.cr4te?.onReady"), "function")
        self.assertNoBrowserErrors()

    def test_project_page_initializes_audio_controls(self):
        """Covers SITE-006 and SITE-027."""
        self.open_page(self.audio_project_path)

        self.assertEqual(self.page.locator(".audio-gallery").count(), 1)
        self.assertEqual(self.page.locator(".audio-gallery li").count(), 3)
        track_padding = self.page.locator(".track-title").first.evaluate(
            "element => ({ top: getComputedStyle(element).paddingTop, right: getComputedStyle(element).paddingRight })"
        )
        track_padding_top = float(track_padding["top"].removesuffix("px"))
        track_padding_right = float(track_padding["right"].removesuffix("px"))
        self.assertGreater(track_padding_top, 0)
        self.assertGreater(track_padding_right, track_padding_top)
        self.assertTrue(self.page.locator(".audio-gallery .progress-bar").is_disabled())
        self.assertEqual(self.page.locator(".audio-gallery .volume-slider").count(), 1)
        self.assertNoBrowserErrors()

    def test_audio_and_video_control_visibility_states_remain_functional(self):
        """Covers SITE-027."""
        self.open_page(self.audio_project_path)
        audio_visibility = self.page.evaluate(
            """
            () => {
                const section = document.querySelector('.audio-gallery-section');
                const gallery = section.querySelector('.audio-gallery');
                const controls = section.querySelector('.audio-controls-wrapper');
                const scrollContainer = window.utils.getExplicitScrollableAncestor(gallery) || window;
                const transitionProperty = getComputedStyle(controls).transitionProperty;

                section.getBoundingClientRect = () => ({ top: 0 });
                controls.getBoundingClientRect = () => ({ top: 150 });
                scrollContainer.dispatchEvent(new Event('scroll'));
                const shown = { opacity: controls.style.opacity, pointerEvents: controls.style.pointerEvents };

                controls.getBoundingClientRect = () => ({ top: 50 });
                scrollContainer.dispatchEvent(new Event('scroll'));
                const hidden = { opacity: controls.style.opacity, pointerEvents: controls.style.pointerEvents };

                return { transitionProperty, shown, hidden };
            }
            """
        )
        self.assertEqual(audio_visibility["transitionProperty"], "opacity")
        self.assertEqual(audio_visibility["shown"], {"opacity": "1", "pointerEvents": "auto"})
        self.assertEqual(audio_visibility["hidden"], {"opacity": "0", "pointerEvents": "none"})

        audio_padding = self.page.locator(".audio-controls").evaluate(
            "element => ({ top: getComputedStyle(element).paddingTop, right: getComputedStyle(element).paddingRight })"
        )
        self.assertGreater(float(audio_padding["top"].removesuffix("px")), 0)
        self.assertGreater(
            float(audio_padding["right"].removesuffix("px")),
            float(audio_padding["top"].removesuffix("px")),
        )

        self.open_page(self.video_project_path)
        transition_property = self.page.locator(".video-controls").evaluate(
            "element => getComputedStyle(element).transitionProperty"
        )
        wrapper = self.page.locator(".video-wrapper").first
        controls = wrapper.locator(".video-controls")

        wrapper.evaluate("element => element.classList.add('hide-controls')")
        self.page.wait_for_timeout(350)
        hidden = controls.evaluate(
            """
            element => ({
                opacity: getComputedStyle(element).opacity,
                pointerEvents: getComputedStyle(element).pointerEvents,
            })
            """
        )
        wrapper.evaluate("element => element.classList.remove('hide-controls')")
        self.page.wait_for_timeout(350)
        shown = controls.evaluate(
            """
            element => ({
                opacity: getComputedStyle(element).opacity,
                pointerEvents: getComputedStyle(element).pointerEvents,
            })
            """
        )

        self.assertEqual(transition_property, "opacity")
        video_padding = controls.evaluate(
            "element => ({ top: getComputedStyle(element).paddingTop, right: getComputedStyle(element).paddingRight })"
        )
        self.assertEqual(video_padding, audio_padding)
        self.assertEqual(hidden, {"opacity": "0", "pointerEvents": "none"})
        self.assertEqual(shown, {"opacity": "1", "pointerEvents": "auto"})
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

    def test_shared_scrollbars_preserve_desktop_and_mobile_scroll_ownership(self):
        self.page.set_viewport_size({"width": 1280, "height": 720})
        self.open_page("index.html")
        overview = self.page.evaluate(
            """
            () => {
                const element = document.querySelector('.overview-layout');
                element.style.height = '200px';
                const spacer = document.createElement('div');
                spacer.style.height = '2000px';
                element.appendChild(spacer);
                element.scrollTop = 100;
                const style = getComputedStyle(element);
                return {
                    overflowY: style.overflowY,
                    scrollbarWidth: style.scrollbarWidth,
                    webkitWidth: getComputedStyle(element, '::-webkit-scrollbar').width,
                    scrollTop: element.scrollTop,
                };
            }
            """
        )
        self.assertEqual(overview["overflowY"], "auto")
        self.assertEqual(overview["scrollbarWidth"], "thin")
        scrollbar_width = overview["webkitWidth"]
        self.assertGreater(float(scrollbar_width.removesuffix("px")), 0)
        self.assertGreater(overview["scrollTop"], 0)

        self.open_page(self.creator_path)
        desktop = self.page.evaluate(
            """
            () => {
                const column = document.querySelector('.right-column');
                column.style.maxHeight = '200px';
                const spacer = document.createElement('div');
                spacer.style.height = '2000px';
                spacer.style.flex = '0 0 2000px';
                column.appendChild(spacer);
                column.scrollTop = 100;
                const style = getComputedStyle(column);
                return {
                    overflowY: style.overflowY,
                    scrollbarWidth: style.scrollbarWidth,
                    webkitWidth: getComputedStyle(column, '::-webkit-scrollbar').width,
                    scrollTop: column.scrollTop,
                };
            }
            """
        )
        self.assertEqual(desktop["overflowY"], "auto")
        self.assertEqual(desktop["scrollbarWidth"], "thin")
        self.assertEqual(desktop["webkitWidth"], scrollbar_width)
        self.assertGreater(desktop["scrollTop"], 0)

        self.page.set_viewport_size({"width": 390, "height": 844})
        self.open_page(self.creator_path)
        mobile = self.page.evaluate(
            """
            () => {
                const content = document.querySelector('.detail-content');
                const column = document.querySelector('.right-column');
                content.style.height = '250px';
                content.style.flex = 'none';
                const spacer = document.createElement('div');
                spacer.style.height = '2000px';
                spacer.style.flex = '0 0 2000px';
                content.appendChild(spacer);
                content.scrollTop = 100;
                const style = getComputedStyle(content);
                return {
                    overflowY: style.overflowY,
                    scrollbarWidth: style.scrollbarWidth,
                    webkitWidth: getComputedStyle(content, '::-webkit-scrollbar').width,
                    scrollTop: content.scrollTop,
                    columnOverflow: getComputedStyle(column).overflowY,
                };
            }
            """
        )
        self.assertEqual(mobile["overflowY"], "auto")
        self.assertEqual(mobile["scrollbarWidth"], "thin")
        self.assertEqual(mobile["webkitWidth"], scrollbar_width)
        self.assertGreater(mobile["scrollTop"], 0)
        self.assertEqual(mobile["columnOverflow"], "visible")
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
                            const pageContent = document.querySelector('.page-content');
                            const content = document.querySelector('.detail-content');
                            const left = document.querySelector('.left-column');
                            const right = document.querySelector('.right-column');
                            const layoutRect = layout.getBoundingClientRect();
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
                                viewportBottomSpace: innerHeight - layoutRect.bottom,
                                outerBottomPadding: parseFloat(getComputedStyle(pageContent).paddingBottom),
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
                    self.assertAlmostEqual(
                        mobile_layout["viewportBottomSpace"],
                        mobile_layout["outerBottomPadding"],
                        delta=0.25,
                    )
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
