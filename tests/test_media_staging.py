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
from cr4te.output_preparation import copy_static_assets, prepare_output_dirs
from cr4te.render_assets import (
    MediaStagingError,
    build_default_thumbnail_specs,
    prepare_default_thumbnails,
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
