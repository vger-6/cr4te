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
from cr4te.enums.media_type import MediaType
from cr4te.render_media import build_media_group_contexts, sort_media_sections_by_type
from cr4te.render_models import MediaSectionContext
from cr4te.schemas.library_schema import MediaGroup, Video


def write_image(path: Path, size: tuple[int, int] = (120, 80)) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color=(120, 80, 160)).save(path)


class RenderMediaTests(unittest.TestCase):
    def test_sort_media_sections_accepts_enum_and_string_order(self):
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


if __name__ == "__main__":
    unittest.main()
