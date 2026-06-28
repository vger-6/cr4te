import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cr4te.build_issues import BuildIssueError, BuildIssuePolicy, IssueCode
from cr4te.config_manager import apply_cli_overrides, load_config
from cr4te.html_context import HtmlBuildContext
from cr4te.enums.domain import Domain
from cr4te.enums.portrait_visibility import PortraitVisibility
from cr4te.enums.thumb_type import ThumbType
from cr4te.output_preparation import copy_static_assets, prepare_output_dirs
from cr4te.render_assets import (
    build_default_thumbnail_specs,
    prepare_default_thumbnails,
    resolve_thumbnail_or_default,
    stage_media_file,
)


def freshness_sidecar_path(thumb_path: Path) -> Path:
    return thumb_path.with_suffix(f"{thumb_path.suffix}.json")


def read_freshness_metadata(thumb_path: Path) -> dict[str, object]:
    return json.loads(freshness_sidecar_path(thumb_path).read_text(encoding="utf-8"))


class MediaStagingTests(unittest.TestCase):
    def test_disabled_portraits_omit_portrait_default_thumbnails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = apply_cli_overrides(load_config(), portrait_visibility=PortraitVisibility.DISABLED)
            ctx = HtmlBuildContext(
                root / "input",
                root / "output",
                config.site_labels,
                config.site_rendering,
            )

            thumb_types = {spec.thumb_type for spec in build_default_thumbnail_specs(ctx)}

            self.assertNotIn(ThumbType.CREATOR_OVERVIEW, thumb_types)
            self.assertNotIn(ThumbType.PORTRAIT, thumb_types)
            self.assertIn(ThumbType.COVER, thumb_types)

    def test_details_portraits_prepare_detail_default_but_not_overview_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = apply_cli_overrides(load_config(), portrait_visibility=PortraitVisibility.DETAILS)
            ctx = HtmlBuildContext(root / "input", root / "output", config.site_labels, config.site_rendering)

            thumb_types = {spec.thumb_type for spec in build_default_thumbnail_specs(ctx)}

            self.assertNotIn(ThumbType.CREATOR_OVERVIEW, thumb_types)
            self.assertIn(ThumbType.PORTRAIT, thumb_types)

    def test_stage_media_file_uses_hardlink_when_symlink_is_unavailable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "input" / "Noomi" / "image.jpg"
            target_dir = root / "output" / "symlinks"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"image bytes")
            config = apply_cli_overrides(load_config(), domain=Domain.ART)
            ctx = HtmlBuildContext(root / "input", root / "output", config.site_labels, config.site_rendering)

            def fake_hardlink(src, dst):
                Path(dst).write_bytes(Path(src).read_bytes())

            with (
                patch("cr4te.render_assets.os.symlink", side_effect=OSError("no symlink")),
                patch("cr4te.render_assets.os.link", side_effect=fake_hardlink),
            ):
                staged = stage_media_file(ctx, Path("Noomi/image.jpg"))

            self.assertTrue(staged.exists())
            self.assertEqual(staged.read_bytes(), b"image bytes")
            self.assertTrue(staged.is_relative_to(target_dir))
            self.assertEqual(ctx.asset_statistics.hard_links_created, 1)
            self.assertEqual(ctx.asset_statistics.symbolic_links_created, 0)

    def test_stage_media_file_counts_created_and_reused_symbolic_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "input" / "Noomi" / "image.jpg"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"image bytes")
            config = apply_cli_overrides(load_config(), domain=Domain.ART)
            ctx = HtmlBuildContext(root / "input", root / "output", config.site_labels, config.site_rendering)

            def fake_symlink(src, dst):
                Path(dst).write_bytes(Path(src).read_bytes())

            with patch("cr4te.render_assets.os.symlink", side_effect=fake_symlink):
                first_staged = stage_media_file(ctx, Path("Noomi/image.jpg"))
                reused_staged = stage_media_file(ctx, Path("Noomi/image.jpg"))

            self.assertEqual(first_staged, reused_staged)
            self.assertEqual(ctx.asset_statistics.symbolic_links_created, 1)
            self.assertEqual(ctx.asset_statistics.media_links_reused, 1)

    def test_stage_media_file_aborts_when_links_are_unavailable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "input" / "Noomi" / "image.jpg"
            target_dir = root / "output" / "symlinks"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"image bytes")
            config = apply_cli_overrides(load_config(), domain=Domain.ART)
            ctx = HtmlBuildContext(root / "input", root / "output", config.site_labels, config.site_rendering)

            with (
                patch("cr4te.render_assets.os.symlink", side_effect=OSError("no symlink")),
                patch("cr4te.render_assets.os.link", side_effect=OSError("no hardlink")),
            ):
                with self.assertRaises(BuildIssueError) as caught:
                    stage_media_file(ctx, Path("Noomi/image.jpg"))

            self.assertEqual(caught.exception.issue.code, IssueCode.MEDIA_STAGING_FAILURE)
            self.assertIn("will not copy media files automatically", caught.exception.issue.message)
            staged_files = [path for path in target_dir.rglob("*") if path.is_file()]
            self.assertEqual(staged_files, [])

    def test_missing_media_is_reported_and_not_staged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = apply_cli_overrides(load_config(), domain=Domain.ART)
            ctx = HtmlBuildContext(root / "input", root / "output", config.site_labels, config.site_rendering)

            staged = stage_media_file(ctx, Path("Noomi/missing.jpg"))

            self.assertIsNone(staged)
            self.assertEqual(len(ctx.issues), 1)
            self.assertEqual(ctx.issues[0].code, IssueCode.MISSING_MEDIA)

    def test_missing_thumbnail_source_counts_default_use(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = apply_cli_overrides(load_config(), domain=Domain.ART)
            ctx = HtmlBuildContext(root / "input", root / "output", config.site_labels, config.site_rendering)

            thumbnail = resolve_thumbnail_or_default(ctx, None, ThumbType.GALLERY)

            self.assertEqual(thumbnail, ctx.get_default_thumb_path(ThumbType.GALLERY))
            self.assertEqual(ctx.asset_statistics.default_thumbnail_uses, 1)

    def test_generated_thumbnail_stores_authoritative_source_freshness_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "input"
            output_dir = Path(tmp) / "site"
            image_path = root / "Noomi" / "image.png"
            image_path.parent.mkdir(parents=True)
            Image.new("RGB", (120, 80), color=(120, 80, 160)).save(image_path)

            config = apply_cli_overrides(load_config(), domain=Domain.ART)
            ctx = HtmlBuildContext(root, output_dir, config.site_labels, config.site_rendering)
            prepare_output_dirs(ctx)

            thumb_path = resolve_thumbnail_or_default(ctx, "Noomi/image.png", ThumbType.GALLERY)

            source_stat = image_path.stat()
            self.assertEqual(
                read_freshness_metadata(thumb_path),
                {
                    "version": 1,
                    "source_path": "Noomi/image.png",
                    "source_size": source_stat.st_size,
                    "source_mtime_ns": source_stat.st_mtime_ns,
                    "thumb_type": "gallery",
                    "generated_height": ctx.get_generated_thumb_height(ThumbType.GALLERY),
                    "thumbnail_suffix": ".png",
                },
            )
            self.assertEqual(ctx.asset_statistics.source_thumbnails_generated, 1)
            self.assertEqual(ctx.asset_statistics.source_freshness_checks, 1)

    def test_existing_thumbnail_is_reused_when_source_freshness_matches(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "input"
            output_dir = Path(tmp) / "site"
            image_path = root / "Noomi" / "image.png"
            image_path.parent.mkdir(parents=True)
            Image.new("RGB", (120, 80), color=(120, 80, 160)).save(image_path)

            config = apply_cli_overrides(load_config(), domain=Domain.ART)
            ctx = HtmlBuildContext(root, output_dir, config.site_labels, config.site_rendering)
            prepare_output_dirs(ctx)

            thumb_path = resolve_thumbnail_or_default(ctx, "Noomi/image.png", ThumbType.GALLERY)

            with patch("cr4te.render_assets.image_utils.generate_thumbnail") as generate_thumbnail:
                reused_path = resolve_thumbnail_or_default(ctx, "Noomi/image.png", ThumbType.GALLERY)

            generate_thumbnail.assert_not_called()
            self.assertEqual(reused_path, thumb_path)
            self.assertEqual(ctx.asset_statistics.source_thumbnails_generated, 1)
            self.assertEqual(ctx.asset_statistics.source_thumbnails_reused, 1)
            self.assertEqual(ctx.asset_statistics.source_freshness_checks, 2)

    def test_thumbnail_is_regenerated_when_freshness_sidecar_is_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "input"
            output_dir = Path(tmp) / "site"
            image_path = root / "Noomi" / "image.png"
            image_path.parent.mkdir(parents=True)
            Image.new("RGB", (120, 80), color=(120, 80, 160)).save(image_path)

            config = apply_cli_overrides(load_config(), domain=Domain.ART)
            ctx = HtmlBuildContext(root, output_dir, config.site_labels, config.site_rendering)
            prepare_output_dirs(ctx)

            thumb_path = resolve_thumbnail_or_default(ctx, "Noomi/image.png", ThumbType.GALLERY)
            freshness_sidecar_path(thumb_path).unlink()

            replacement_thumb = Image.new("RGB", (32, 32), color=(20, 120, 80))
            with patch(
                "cr4te.render_assets.image_utils.generate_thumbnail",
                return_value=replacement_thumb,
            ) as generate_thumbnail:
                regenerated_path = resolve_thumbnail_or_default(ctx, "Noomi/image.png", ThumbType.GALLERY)

            self.assertEqual(regenerated_path, thumb_path)
            generate_thumbnail.assert_called_once_with(image_path, ctx.get_generated_thumb_height(ThumbType.GALLERY))
            self.assertEqual(ctx.asset_statistics.source_freshness_checks, 2)
            self.assertEqual(ctx.asset_statistics.source_thumbnails_generated, 2)
            self.assertEqual(read_freshness_metadata(thumb_path)["source_path"], "Noomi/image.png")

    def test_thumbnail_is_regenerated_when_freshness_sidecar_is_unreadable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "input"
            output_dir = Path(tmp) / "site"
            image_path = root / "Noomi" / "image.png"
            image_path.parent.mkdir(parents=True)
            Image.new("RGB", (120, 80), color=(120, 80, 160)).save(image_path)

            config = apply_cli_overrides(load_config(), domain=Domain.ART)
            ctx = HtmlBuildContext(root, output_dir, config.site_labels, config.site_rendering)
            prepare_output_dirs(ctx)

            thumb_path = resolve_thumbnail_or_default(ctx, "Noomi/image.png", ThumbType.GALLERY)
            sidecar_path = freshness_sidecar_path(thumb_path)
            sidecar_path.write_bytes(b"\xff")

            replacement_thumb = Image.new("RGB", (32, 32), color=(20, 120, 80))
            with patch("cr4te.render_assets.image_utils.generate_thumbnail", return_value=replacement_thumb) as generate_thumbnail:
                resolve_thumbnail_or_default(ctx, "Noomi/image.png", ThumbType.GALLERY)

            generate_thumbnail.assert_called_once_with(image_path, ctx.get_generated_thumb_height(ThumbType.GALLERY))
            self.assertEqual(read_freshness_metadata(thumb_path)["source_path"], "Noomi/image.png")

    def test_thumbnail_is_reused_when_content_changes_with_same_size_and_mtime(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "input"
            output_dir = Path(tmp) / "site"
            image_path = root / "Noomi" / "image.png"
            image_path.parent.mkdir(parents=True)
            Image.new("RGB", (120, 80), color=(120, 80, 160)).save(image_path)

            config = apply_cli_overrides(load_config(), domain=Domain.ART)
            ctx = HtmlBuildContext(root, output_dir, config.site_labels, config.site_rendering)
            prepare_output_dirs(ctx)

            thumb_path = resolve_thumbnail_or_default(ctx, "Noomi/image.png", ThumbType.GALLERY)
            original_metadata = read_freshness_metadata(thumb_path)
            source_stat = image_path.stat()
            image_bytes = bytearray(image_path.read_bytes())
            image_bytes[-1] = (image_bytes[-1] + 1) % 256
            image_path.write_bytes(image_bytes)
            os.utime(image_path, ns=(source_stat.st_atime_ns, source_stat.st_mtime_ns))

            with patch("cr4te.render_assets.image_utils.generate_thumbnail") as generate_thumbnail:
                reused_path = resolve_thumbnail_or_default(ctx, "Noomi/image.png", ThumbType.GALLERY)

            generate_thumbnail.assert_not_called()
            self.assertEqual(reused_path, thumb_path)
            self.assertEqual(read_freshness_metadata(thumb_path), original_metadata)
            self.assertEqual(ctx.asset_statistics.source_thumbnails_generated, 1)
            self.assertEqual(ctx.asset_statistics.source_thumbnails_reused, 1)
            self.assertEqual(ctx.asset_statistics.source_freshness_checks, 2)

    def test_thumbnail_is_regenerated_when_source_size_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "input"
            output_dir = Path(tmp) / "site"
            image_path = root / "Noomi" / "image.png"
            image_path.parent.mkdir(parents=True)
            Image.new("RGB", (120, 80), color=(120, 80, 160)).save(image_path)

            config = apply_cli_overrides(load_config(), domain=Domain.ART)
            ctx = HtmlBuildContext(root, output_dir, config.site_labels, config.site_rendering)
            prepare_output_dirs(ctx)

            thumb_path = resolve_thumbnail_or_default(ctx, "Noomi/image.png", ThumbType.GALLERY)
            image_path.write_bytes(image_path.read_bytes() + b"changed-size")

            replacement_thumb = Image.new("RGB", (32, 32), color=(20, 120, 80))
            with patch("cr4te.render_assets.image_utils.generate_thumbnail", return_value=replacement_thumb) as generate_thumbnail:
                regenerated_path = resolve_thumbnail_or_default(ctx, "Noomi/image.png", ThumbType.GALLERY)

            self.assertEqual(regenerated_path, thumb_path)
            generate_thumbnail.assert_called_once_with(image_path, ctx.get_generated_thumb_height(ThumbType.GALLERY))
            self.assertEqual(ctx.asset_statistics.source_thumbnails_generated, 2)
            self.assertEqual(ctx.asset_statistics.source_freshness_checks, 2)
            self.assertEqual(read_freshness_metadata(thumb_path)["source_size"], image_path.stat().st_size)

    def test_thumbnail_is_regenerated_when_source_mtime_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "input"
            output_dir = Path(tmp) / "site"
            image_path = root / "Noomi" / "image.png"
            image_path.parent.mkdir(parents=True)
            Image.new("RGB", (120, 80), color=(120, 80, 160)).save(image_path)

            config = apply_cli_overrides(load_config(), domain=Domain.ART)
            ctx = HtmlBuildContext(root, output_dir, config.site_labels, config.site_rendering)
            prepare_output_dirs(ctx)

            thumb_path = resolve_thumbnail_or_default(ctx, "Noomi/image.png", ThumbType.GALLERY)
            source_stat = image_path.stat()
            newer_ns = source_stat.st_mtime_ns + 1_000_000_000
            os.utime(image_path, ns=(source_stat.st_atime_ns, newer_ns))

            replacement_thumb = Image.new("RGB", (32, 32), color=(20, 120, 80))
            with patch("cr4te.render_assets.image_utils.generate_thumbnail", return_value=replacement_thumb) as generate_thumbnail:
                regenerated_path = resolve_thumbnail_or_default(ctx, "Noomi/image.png", ThumbType.GALLERY)

            self.assertEqual(regenerated_path, thumb_path)
            generate_thumbnail.assert_called_once_with(image_path, ctx.get_generated_thumb_height(ThumbType.GALLERY))
            self.assertEqual(ctx.asset_statistics.source_thumbnails_generated, 2)
            self.assertEqual(ctx.asset_statistics.source_freshness_checks, 2)
            self.assertEqual(read_freshness_metadata(thumb_path)["source_mtime_ns"], image_path.stat().st_mtime_ns)

    def test_thumbnail_is_regenerated_when_recipe_metadata_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "input"
            output_dir = Path(tmp) / "site"
            image_path = root / "Noomi" / "image.png"
            image_path.parent.mkdir(parents=True)
            Image.new("RGB", (120, 80), color=(120, 80, 160)).save(image_path)

            config = apply_cli_overrides(load_config(), domain=Domain.ART)
            ctx = HtmlBuildContext(root, output_dir, config.site_labels, config.site_rendering)
            prepare_output_dirs(ctx)

            thumb_path = resolve_thumbnail_or_default(ctx, "Noomi/image.png", ThumbType.GALLERY)
            metadata = read_freshness_metadata(thumb_path)
            metadata["generated_height"] = 1
            freshness_sidecar_path(thumb_path).write_text(json.dumps(metadata), encoding="utf-8")

            replacement_thumb = Image.new("RGB", (32, 32), color=(20, 120, 80))
            with patch("cr4te.render_assets.image_utils.generate_thumbnail", return_value=replacement_thumb) as generate_thumbnail:
                regenerated_path = resolve_thumbnail_or_default(ctx, "Noomi/image.png", ThumbType.GALLERY)

            self.assertEqual(regenerated_path, thumb_path)
            generate_thumbnail.assert_called_once_with(image_path, ctx.get_generated_thumb_height(ThumbType.GALLERY))
            self.assertEqual(ctx.asset_statistics.source_thumbnails_generated, 2)
            self.assertEqual(read_freshness_metadata(thumb_path)["generated_height"], ctx.get_generated_thumb_height(ThumbType.GALLERY))

    def test_thumbnail_failure_uses_default_and_reports_issue(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "input"
            output_dir = Path(tmp) / "site"
            image_path = root / "Noomi" / "image.png"
            image_path.parent.mkdir(parents=True)
            image_path.write_bytes(b"not an image")

            config = apply_cli_overrides(load_config(), domain=Domain.ART)
            ctx = HtmlBuildContext(root, output_dir, config.site_labels, config.site_rendering)
            prepare_output_dirs(ctx)
            prepare_default_thumbnails(ctx)

            thumb_path = resolve_thumbnail_or_default(ctx, "Noomi/image.png", ThumbType.GALLERY)

            self.assertEqual(thumb_path, ctx.get_default_thumb_path(ThumbType.GALLERY))
            self.assertEqual(len(ctx.issues), 1)
            self.assertEqual(ctx.issues[0].code, IssueCode.THUMBNAIL_FAILURE)
            self.assertEqual(ctx.asset_statistics.default_thumbnail_uses, 1)

    def test_thumbnail_failure_raises_in_strict_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "input"
            output_dir = Path(tmp) / "site"
            image_path = root / "Noomi" / "image.png"
            image_path.parent.mkdir(parents=True)
            image_path.write_bytes(b"not an image")

            config = apply_cli_overrides(load_config(), domain=Domain.ART)
            ctx = HtmlBuildContext(
                root,
                output_dir,
                config.site_labels,
                config.site_rendering,
                issue_policy=BuildIssuePolicy(strict=True),
            )
            prepare_output_dirs(ctx)
            prepare_default_thumbnails(ctx)

            with self.assertRaises(BuildIssueError) as caught:
                resolve_thumbnail_or_default(ctx, "Noomi/image.png", ThumbType.GALLERY)

            self.assertEqual(caught.exception.issue.code, IssueCode.THUMBNAIL_FAILURE)

    def test_output_preparation_copies_static_files_and_default_thumbnails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "input"
            output_dir = Path(tmp) / "site"
            root.mkdir()
            config = apply_cli_overrides(load_config(), domain=Domain.ART)
            config.site_rendering.galleries.project_cards.aspect_ratio = "7/5"
            ctx = HtmlBuildContext(root, output_dir, config.site_labels, config.site_rendering)

            prepare_output_dirs(ctx)
            copy_static_assets(ctx)
            prepare_default_thumbnails(ctx)

            self.assertTrue((ctx.css_dir / "base.css").exists())
            self.assertTrue((ctx.js_dir / "utils.js").exists())
            self.assertTrue((ctx.assets_dir / "favicon.svg").exists())
            self.assertTrue((ctx.themes_dir / "frozen-aurora.css").exists())

            specs = build_default_thumbnail_specs(ctx)
            self.assertEqual(len(specs), 6)
            specs_by_type = {spec.thumb_type: spec for spec in specs}
            self.assertEqual(specs_by_type[ThumbType.PROJECT_OVERVIEW].width_ratio, 7)
            self.assertEqual(specs_by_type[ThumbType.PROJECT_OVERVIEW].height_ratio, 5)
            self.assertEqual(specs_by_type[ThumbType.COVER].width_ratio, 7)
            self.assertEqual(specs_by_type[ThumbType.COVER].height_ratio, 5)
            for spec in specs:
                expected_height = ctx.get_generated_thumb_height(spec.thumb_type)
                with Image.open(ctx.get_default_thumb_path(spec.thumb_type)) as image:
                    self.assertEqual(image.height, expected_height)
                    self.assertEqual(image.width, spec.width_for_height(expected_height))


if __name__ == "__main__":
    unittest.main()
