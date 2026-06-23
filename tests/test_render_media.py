import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cr4te.build_issues import IssueCode, IssueSeverity
from cr4te.config_manager import apply_cli_overrides, load_config
from cr4te.html_context import HtmlBuildContext
from cr4te.enums.domain import Domain
from cr4te.enums.media_type import MediaType
from cr4te.render_assets import prepare_default_thumbnails
from cr4te.render_media import build_media_group_contexts, sort_media_sections_by_type
from cr4te.render_models import MediaSectionContext
from cr4te.schemas.library_schema import MediaGroup, Video


def write_image(path: Path, size: tuple[int, int] = (120, 80)) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color=(120, 80, 160)).save(path)


class RenderMediaTests(unittest.TestCase):
    def test_sort_media_sections_accepts_enum_and_string_order(self):
        """Covers SITE-030."""
        sections = [
            MediaSectionContext(type=MediaType.DOCUMENT),
            MediaSectionContext(type=MediaType.VIDEO),
            MediaSectionContext(type=MediaType.TEXT),
        ]

        sorted_sections = sort_media_sections_by_type(sections, [MediaType.TEXT, "video"])

        self.assertEqual(
            [section.type for section in sorted_sections],
            [MediaType.TEXT, MediaType.VIDEO, MediaType.DOCUMENT],
        )

    def test_media_group_contexts_are_typed_and_preserve_template_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "input"
            output_dir = Path(tmp) / "site"
            media_dir = root / "Gallery"
            media_dir.mkdir(parents=True)
            write_image(media_dir / "photo.jpg")
            (media_dir / "clip.mp4").write_bytes(b"video")
            (media_dir / "poster.jpg").write_bytes(b"poster")
            (media_dir / "song.mp3").write_bytes(b"audio")
            (media_dir / "book.pdf").write_bytes(b"pdf")
            (media_dir / "notes.md").write_text("# Notes", encoding="utf-8")

            config = apply_cli_overrides(load_config(), domain=Domain.ART)
            ctx = HtmlBuildContext(root, output_dir, config.site_labels, config.site_rendering)
            media_group = MediaGroup(
                is_root=False,
                videos=[Video(file="Gallery/clip.mp4", poster="Gallery/poster.jpg")],
                tracks=["Gallery/song.mp3"],
                images=["Gallery/photo.jpg"],
                documents=["Gallery/book.pdf"],
                texts=["Gallery/notes.md"],
                rel_dir_path="Gallery",
            )

            with patch("cr4te.render_media.audio_utils.get_audio_duration_seconds", return_value=12.5) as duration:
                group = build_media_group_contexts(ctx, [media_group])[0]

            duration.assert_called_once()
            self.assertEqual(group.audio_section_title, "Gallery")
            self.assertEqual(group.image_section_title, "Gallery")
            self.assertEqual(
                [section.type for section in group.sections],
                [
                    MediaType.AUDIO,
                    MediaType.IMAGE,
                    MediaType.TEXT,
                    MediaType.DOCUMENT,
                    MediaType.VIDEO,
                ],
            )

            sections = {section.type: section for section in group.sections}
            self.assertEqual(sections[MediaType.AUDIO].tracks[0].title, "song")
            self.assertEqual(sections[MediaType.AUDIO].tracks[0].duration_seconds, 12.5)
            self.assertEqual(sections[MediaType.AUDIO].total_duration_seconds, 12.5)
            self.assertEqual(sections[MediaType.IMAGE].images[0].caption, "photo")
            self.assertTrue((output_dir / sections[MediaType.IMAGE].images[0].rel_thumbnail_path).exists())
            self.assertIn("Notes", sections[MediaType.TEXT].texts[0].content)
            self.assertEqual(sections[MediaType.DOCUMENT].documents[0].title, "Book")
            self.assertEqual(sections[MediaType.VIDEO].videos[0].title, "Clip")
            self.assertTrue(sections[MediaType.VIDEO].videos[0].rel_poster_path)

    def test_audio_duration_cache_reuses_duplicate_track_reads(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "input"
            output_dir = Path(tmp) / "site"
            media_dir = root / "Gallery"
            media_dir.mkdir(parents=True)
            (media_dir / "song.mp3").write_bytes(b"audio")

            config = apply_cli_overrides(load_config(), domain=Domain.ART)
            ctx = HtmlBuildContext(root, output_dir, config.site_labels, config.site_rendering)
            media_group = MediaGroup(
                is_root=False,
                videos=[],
                tracks=["Gallery/song.mp3", "Gallery/song.mp3"],
                images=[],
                documents=[],
                texts=[],
                rel_dir_path="Gallery",
            )

            with patch("cr4te.render_media.audio_utils.get_audio_duration_seconds", return_value=9) as duration:
                group = build_media_group_contexts(ctx, [media_group])[0]

            duration.assert_called_once()
            audio_section = next(section for section in group.sections if section.type == MediaType.AUDIO)
            self.assertEqual([track.duration_seconds for track in audio_section.tracks], [9, 9])
            self.assertEqual(audio_section.total_duration_seconds, 18)

    def test_missing_media_is_omitted_and_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "input"
            output_dir = Path(tmp) / "site"
            config = apply_cli_overrides(load_config(), domain=Domain.ART)
            ctx = HtmlBuildContext(root, output_dir, config.site_labels, config.site_rendering)
            media_group = MediaGroup(
                is_root=False,
                videos=[Video(file="Gallery/missing.mp4", poster="")],
                tracks=["Gallery/missing.mp3"],
                images=["Gallery/missing.jpg"],
                documents=["Gallery/missing.pdf"],
                texts=["Gallery/missing.md"],
                rel_dir_path="Gallery",
            )

            group = build_media_group_contexts(ctx, [media_group])[0]

            sections = {section.type: section for section in group.sections}
            self.assertEqual(sections[MediaType.VIDEO].videos, [])
            self.assertEqual(sections[MediaType.AUDIO].tracks, [])
            self.assertEqual(sections[MediaType.IMAGE].images, [])
            self.assertEqual(sections[MediaType.DOCUMENT].documents, [])
            self.assertEqual(sections[MediaType.TEXT].texts, [])
            self.assertEqual(len(ctx.issues), 5)
            self.assertTrue(all(issue.code == IssueCode.MISSING_MEDIA for issue in ctx.issues))

    def test_audio_inspection_failure_uses_zero_and_reports_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "input"
            output_dir = Path(tmp) / "site"
            track_path = root / "Gallery" / "song.mp3"
            track_path.parent.mkdir(parents=True)
            track_path.write_bytes(b"audio")
            config = apply_cli_overrides(load_config(), domain=Domain.ART)
            ctx = HtmlBuildContext(root, output_dir, config.site_labels, config.site_rendering)
            media_group = MediaGroup(
                is_root=False,
                videos=[],
                tracks=["Gallery/song.mp3"],
                images=[],
                documents=[],
                texts=[],
                rel_dir_path="Gallery",
            )

            with patch("cr4te.render_media.audio_utils.get_audio_duration_seconds", side_effect=ValueError("bad audio")):
                group = build_media_group_contexts(ctx, [media_group])[0]

            audio_section = next(section for section in group.sections if section.type == MediaType.AUDIO)
            self.assertEqual(audio_section.tracks[0].duration_seconds, 0)
            self.assertEqual(len(ctx.issues), 1)
            self.assertEqual(ctx.issues[0].code, IssueCode.MEDIA_INSPECTION_FAILURE)
            self.assertEqual(ctx.issues[0].severity, IssueSeverity.WARNING)

    def test_unreadable_text_media_is_omitted_and_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "input"
            output_dir = Path(tmp) / "site"
            text_path = root / "Gallery" / "notes.md"
            text_path.parent.mkdir(parents=True)
            text_path.write_text("notes", encoding="utf-8")
            config = apply_cli_overrides(load_config(), domain=Domain.ART)
            ctx = HtmlBuildContext(root, output_dir, config.site_labels, config.site_rendering)
            media_group = MediaGroup(
                is_root=False,
                videos=[],
                tracks=[],
                images=[],
                documents=[],
                texts=["Gallery/notes.md"],
                rel_dir_path="Gallery",
            )

            with patch("cr4te.render_media.text_utils.read_text", side_effect=UnicodeError("bad text")):
                group = build_media_group_contexts(ctx, [media_group])[0]

            text_section = next(section for section in group.sections if section.type == MediaType.TEXT)
            self.assertEqual(text_section.texts, [])
            self.assertEqual(len(ctx.issues), 1)
            self.assertEqual(ctx.issues[0].code, IssueCode.MEDIA_READ_FAILURE)

    def test_unreadable_gallery_image_is_omitted_and_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "input"
            output_dir = Path(tmp) / "site"
            image_path = root / "Gallery" / "broken.jpg"
            image_path.parent.mkdir(parents=True)
            image_path.write_bytes(b"not an image")
            config = apply_cli_overrides(load_config(), domain=Domain.ART)
            ctx = HtmlBuildContext(root, output_dir, config.site_labels, config.site_rendering)
            prepare_default_thumbnails(ctx)
            media_group = MediaGroup(
                is_root=False,
                videos=[],
                tracks=[],
                images=["Gallery/broken.jpg"],
                documents=[],
                texts=[],
                rel_dir_path="Gallery",
            )

            group = build_media_group_contexts(ctx, [media_group])[0]

            image_section = next(section for section in group.sections if section.type == MediaType.IMAGE)
            self.assertEqual(image_section.images, [])
            self.assertEqual(
                {issue.code for issue in ctx.issues},
                {IssueCode.THUMBNAIL_FAILURE, IssueCode.MEDIA_READ_FAILURE},
            )
            self.assertFalse(ctx.symlinks_dir.exists())

    def test_gallery_image_uses_default_when_only_thumbnail_creation_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "input"
            output_dir = Path(tmp) / "site"
            image_path = root / "Gallery" / "photo.jpg"
            write_image(image_path)
            config = apply_cli_overrides(load_config(), domain=Domain.ART)
            ctx = HtmlBuildContext(root, output_dir, config.site_labels, config.site_rendering)
            prepare_default_thumbnails(ctx)
            media_group = MediaGroup(
                is_root=False,
                videos=[],
                tracks=[],
                images=["Gallery/photo.jpg"],
                documents=[],
                texts=[],
                rel_dir_path="Gallery",
            )

            with patch("cr4te.render_assets._regenerate_thumbnail", side_effect=OSError("cannot write")):
                group = build_media_group_contexts(ctx, [media_group])[0]

            image_section = next(section for section in group.sections if section.type == MediaType.IMAGE)
            self.assertEqual(len(image_section.images), 1)
            self.assertEqual(
                image_section.images[0].rel_thumbnail_path,
                "assets/defaults/gallery.png",
            )
            self.assertEqual(len(ctx.issues), 1)
            self.assertEqual(ctx.issues[0].code, IssueCode.THUMBNAIL_FAILURE)


if __name__ == "__main__":
    unittest.main()
