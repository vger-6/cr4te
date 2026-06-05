import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cr4te.config_manager import apply_cli_overrides, load_config
from cr4te.html_context import HtmlBuildContext
from cr4te.enums.domain import Domain
from cr4te.enums.thumb_type import ThumbType
from cr4te.output_preparation import copy_static_assets, prepare_output_dirs
from cr4te.render_assets import (
    MediaStagingError,
    build_default_thumbnail_specs,
    prepare_default_thumbnails,
    resolve_thumbnail_or_default,
    stage_media_file,
)


class MediaStagingTests(unittest.TestCase):
    def test_stage_media_file_uses_hardlink_when_symlink_is_unavailable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "input" / "Noomi" / "image.jpg"
            target_dir = root / "output" / "symlinks"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"image bytes")

            def fake_hardlink(src, dst):
                Path(dst).write_bytes(Path(src).read_bytes())

            with (
                patch("cr4te.render_assets.os.symlink", side_effect=OSError("no symlink")),
                patch("cr4te.render_assets.os.link", side_effect=fake_hardlink),
            ):
                staged = stage_media_file(root / "input", Path("Noomi/image.jpg"), target_dir)

            self.assertTrue(staged.exists())
            self.assertEqual(staged.read_bytes(), b"image bytes")
            self.assertTrue(staged.is_relative_to(target_dir))

    def test_stage_media_file_aborts_when_links_are_unavailable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "input" / "Noomi" / "image.jpg"
            target_dir = root / "output" / "symlinks"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"image bytes")

            with (
                patch("cr4te.render_assets.os.symlink", side_effect=OSError("no symlink")),
                patch("cr4te.render_assets.os.link", side_effect=OSError("no hardlink")),
            ):
                with self.assertRaisesRegex(MediaStagingError, "will not copy media files automatically"):
                    stage_media_file(root / "input", Path("Noomi/image.jpg"), target_dir)

            staged_files = [path for path in target_dir.rglob("*") if path.is_file()]
            self.assertEqual(staged_files, [])

    def test_existing_thumbnail_is_reused_when_source_is_not_newer(self):
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
            thumb_mtime_ns = thumb_path.stat().st_mtime_ns
            os.utime(image_path, ns=(thumb_mtime_ns - 1, thumb_mtime_ns - 1))
            os.utime(image_path.parent, ns=(thumb_mtime_ns - 1, thumb_mtime_ns - 1))

            with (
                patch("cr4te.render_assets.file_utils.calculate_sha256") as calculate_sha256,
                patch("cr4te.render_assets.image_utils.generate_thumbnail") as generate_thumbnail,
            ):
                reused_path = resolve_thumbnail_or_default(ctx, "Noomi/image.png", ThumbType.GALLERY)

            calculate_sha256.assert_not_called()
            generate_thumbnail.assert_not_called()
            self.assertEqual(reused_path, thumb_path)

    def test_thumbnail_is_regenerated_when_source_is_newer(self):
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
            sidecar_path = thumb_path.with_suffix(".png.sha256")
            sidecar_path.write_text("stale-source-hash", encoding="ascii")
            stale_thumb_ns = 1_700_000_000_000_000_000
            newer_source_ns = stale_thumb_ns + 1_000_000_000
            os.utime(thumb_path, ns=(stale_thumb_ns, stale_thumb_ns))

            Image.new("RGB", (40, 80), color=(20, 120, 80)).save(image_path)
            os.utime(image_path, ns=(newer_source_ns, newer_source_ns))

            with patch("cr4te.render_assets.file_utils.calculate_sha256") as calculate_sha256:
                regenerated_path = resolve_thumbnail_or_default(ctx, "Noomi/image.png", ThumbType.GALLERY)

            calculate_sha256.assert_not_called()
            self.assertEqual(regenerated_path, thumb_path)
            self.assertFalse(sidecar_path.exists())
            with Image.open(thumb_path) as image:
                self.assertEqual(image.height, ctx.get_generated_thumb_height(ThumbType.GALLERY))
                self.assertEqual(image.width, 225)

    def test_thumbnail_is_regenerated_when_source_folder_is_newer_and_sidecar_is_missing(self):
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
            stale_thumb_ns = 1_700_000_000_000_000_000
            older_source_ns = stale_thumb_ns - 1_000_000_000
            newer_folder_ns = stale_thumb_ns + 1_000_000_000
            os.utime(thumb_path, ns=(stale_thumb_ns, stale_thumb_ns))
            os.utime(image_path, ns=(older_source_ns, older_source_ns))
            os.utime(image_path.parent, ns=(newer_folder_ns, newer_folder_ns))

            replacement_thumb = Image.new("RGB", (32, 32), color=(20, 120, 80))
            with (
                patch("cr4te.render_assets.file_utils.calculate_sha256", return_value="new-source-hash") as calculate_sha256,
                patch(
                    "cr4te.render_assets.image_utils.generate_thumbnail",
                    return_value=replacement_thumb,
                ) as generate_thumbnail,
            ):
                regenerated_path = resolve_thumbnail_or_default(ctx, "Noomi/image.png", ThumbType.GALLERY)

            self.assertEqual(regenerated_path, thumb_path)
            calculate_sha256.assert_called_once_with(image_path)
            generate_thumbnail.assert_called_once_with(image_path, ctx.get_generated_thumb_height(ThumbType.GALLERY))
            self.assertEqual(
                thumb_path.with_suffix(".png.sha256").read_text(encoding="ascii"),
                "new-source-hash",
            )

    def test_thumbnail_is_regenerated_when_source_folder_is_newer_and_hash_changed(self):
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
            sidecar_path = thumb_path.with_suffix(".png.sha256")
            sidecar_path.write_text("old-source-hash", encoding="ascii")
            stale_thumb_ns = 1_700_000_000_000_000_000
            os.utime(thumb_path, ns=(stale_thumb_ns, stale_thumb_ns))
            os.utime(image_path, ns=(stale_thumb_ns - 1_000_000_000, stale_thumb_ns - 1_000_000_000))
            os.utime(image_path.parent, ns=(stale_thumb_ns + 1_000_000_000, stale_thumb_ns + 1_000_000_000))

            replacement_thumb = Image.new("RGB", (32, 32), color=(20, 120, 80))
            with (
                patch("cr4te.render_assets.file_utils.calculate_sha256", return_value="new-source-hash"),
                patch("cr4te.render_assets.image_utils.generate_thumbnail", return_value=replacement_thumb),
            ):
                resolve_thumbnail_or_default(ctx, "Noomi/image.png", ThumbType.GALLERY)

            self.assertEqual(sidecar_path.read_text(encoding="ascii"), "new-source-hash")

    def test_thumbnail_is_reused_when_source_folder_is_newer_and_hash_matches(self):
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
            thumb_path.with_suffix(".png.sha256").write_text("same-source-hash", encoding="ascii")
            stale_thumb_ns = 1_700_000_000_000_000_000
            os.utime(thumb_path, ns=(stale_thumb_ns, stale_thumb_ns))
            os.utime(image_path, ns=(stale_thumb_ns - 1_000_000_000, stale_thumb_ns - 1_000_000_000))
            os.utime(image_path.parent, ns=(stale_thumb_ns + 1_000_000_000, stale_thumb_ns + 1_000_000_000))

            with (
                patch("cr4te.render_assets.file_utils.calculate_sha256", return_value="same-source-hash"),
                patch("cr4te.render_assets.image_utils.generate_thumbnail") as generate_thumbnail,
            ):
                reused_path = resolve_thumbnail_or_default(ctx, "Noomi/image.png", ThumbType.GALLERY)

            self.assertEqual(reused_path, thumb_path)
            generate_thumbnail.assert_not_called()
            self.assertGreater(thumb_path.stat().st_mtime_ns, stale_thumb_ns)

    def test_output_preparation_copies_static_files_and_default_thumbnails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "input"
            output_dir = Path(tmp) / "site"
            root.mkdir()
            config = apply_cli_overrides(load_config(), domain=Domain.ART)
            ctx = HtmlBuildContext(root, output_dir, config.site_labels, config.site_rendering)

            prepare_output_dirs(ctx)
            copy_static_assets(ctx)
            prepare_default_thumbnails(ctx)

            self.assertTrue((ctx.css_dir / "base.css").exists())
            self.assertTrue((ctx.js_dir / "utils.js").exists())
            self.assertTrue((ctx.assets_dir / "favicon.svg").exists())

            specs = build_default_thumbnail_specs(ctx)
            self.assertEqual(len(specs), 6)
            for spec in specs:
                expected_height = ctx.get_generated_thumb_height(spec.thumb_type)
                with Image.open(ctx.get_default_thumb_path(spec.thumb_type)) as image:
                    self.assertEqual(image.height, expected_height)
                    self.assertEqual(image.width, spec.width_for_height(expected_height))


if __name__ == "__main__":
    unittest.main()
