import sys
import tempfile
import types
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cr4te.media_cache import ImageDimensions
from cr4te.utils import path_utils, text_utils
from cr4te.utils.audio_utils import get_audio_duration_seconds
from cr4te.utils.date_utils import calculate_age_from_strings, format_age, parse_date
from cr4te.utils.format_utils import format_named, validate_named_format
from cr4te.utils.image_utils import create_centered_text_image, generate_thumbnail
from cr4te.utils.json_utils import load_json
from cr4te.utils.sorting_utils import dated_title_sort_key


class DateUtilsTests(unittest.TestCase):
    def test_parse_date_uses_first_available_precision(self):
        self.assertEqual(parse_date("2024"), datetime(2024, 1, 1))
        self.assertEqual(parse_date("2024-03"), datetime(2024, 3, 1))
        self.assertEqual(parse_date("2024-03-12"), datetime(2024, 3, 12))
        self.assertIsNone(parse_date(""))
        self.assertIsNone(parse_date(None))

    def test_parse_date_returns_none_for_invalid_dates(self):
        with self.assertLogs("cr4te.utils.date_utils", level="WARNING"):
            self.assertIsNone(parse_date("2024-02-31"))

    def test_calculate_age_from_strings_uses_reference_date(self):
        self.assertEqual(calculate_age_from_strings("1990-04-20", "2024-04-19"), 33)
        self.assertEqual(calculate_age_from_strings("1990-04-20", "2024-04-20"), 34)
        self.assertEqual(calculate_age_from_strings("1990", "2024"), 34)
        self.assertIsNone(calculate_age_from_strings("", "2024"))

    def test_format_age_suppresses_missing_or_negative_age(self):
        self.assertEqual(format_age(0), "0 y.o.")
        self.assertEqual(format_age(34), "34 y.o.")
        self.assertEqual(format_age(None), "")
        self.assertEqual(format_age(-1), "")


class PathUtilsTests(unittest.TestCase):
    def test_relative_path_from_resolves_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "site" / "assets" / "cover.jpg"
            base = root / "site" / "pages"
            target.parent.mkdir(parents=True)
            base.mkdir(parents=True)

            self.assertEqual(path_utils.relative_path_from(target, base), Path("..") / "assets" / "cover.jpg")

    def test_build_unique_path_preserves_suffix_and_depth(self):
        unique = path_utils.build_unique_path(Path("creator") / "Ada Lovelace.html", depth=3)

        self.assertEqual(len(unique.parts), 4)
        self.assertEqual([len(part) for part in unique.parts[:-1]], [2, 2, 2])
        self.assertEqual(unique.suffix, ".html")

    def test_build_unique_path_hashes_posix_path_representation(self):
        native_path = Path("creator") / "Ada Lovelace.html"
        posix_path = Path("creator/Ada Lovelace.html")

        self.assertEqual(path_utils.build_unique_path(native_path), path_utils.build_unique_path(posix_path))

    def test_build_unique_path_rejects_unsupported_depth(self):
        for depth in (0, 21):
            with self.subTest(depth=depth):
                with self.assertRaises(ValueError):
                    path_utils.build_unique_path(Path("project.html"), depth=depth)

    def test_tag_path(self):
        self.assertEqual(path_utils.tag_path(Path("thumbs") / "cover.jpg", "card"), Path("thumbs") / "cover_card.jpg")


class TextUtilsTests(unittest.TestCase):
    def test_read_text_returns_stripped_file_contents_or_empty_string(self):
        with tempfile.TemporaryDirectory() as tmp:
            text_path = Path(tmp) / "README.md"
            text_path.write_text("  Hello\n", encoding="utf-8")

            self.assertEqual(text_utils.read_text(text_path), "Hello")
            self.assertEqual(text_utils.read_text(Path(tmp) / "missing.md"), "")

    def test_markdown_to_html_supports_tables_and_line_breaks(self):
        html = text_utils.markdown_to_html("| A |\n|---|\n| B |\n\none\ntwo")

        self.assertIn("<table>", html)
        self.assertIn("<br", html)

    def test_multi_split_handles_multi_character_separators(self):
        self.assertEqual(
            text_utils.multi_split("Ada and Bea & Cy", [" and ", " & "]),
            ["Ada", "Bea", "Cy"],
        )
        self.assertEqual(text_utils.multi_split("Ada", []), ["Ada"])

    def test_slugify_normalizes_text(self):
        self.assertEqual(text_utils.slugify("Ada Lovelace!"), "ada_lovelace")
        with self.assertRaises(ValueError):
            text_utils.slugify(None)


class FormatUtilsTests(unittest.TestCase):
    def test_format_named_interpolates_named_values(self):
        self.assertEqual(
            format_named("{project} by {creator}", project="Notes", creator="Ada"),
            "Notes by Ada",
        )

    def test_validate_named_format_accepts_optional_and_reordered_placeholders(self):
        self.assertEqual(
            validate_named_format(
                "{collaborator}: {projects}",
                allowed_fields=frozenset({"collaborator", "projects"}),
                required_fields=frozenset({"collaborator"}),
            ),
            "{collaborator}: {projects}",
        )
        self.assertEqual(
            validate_named_format(
                "With {collaborator}",
                allowed_fields=frozenset({"collaborator", "projects"}),
                required_fields=frozenset({"collaborator"}),
            ),
            "With {collaborator}",
        )

    def test_validate_named_format_rejects_unsafe_or_ambiguous_fields(self):
        invalid_formats = (
            "{0}",
            "{creator.name}",
            "{creator!r}",
            "{creator:>10}",
            "{creator} and {creator}",
            "Portrait",
        )

        for value in invalid_formats:
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_named_format(
                    value,
                    allowed_fields=frozenset({"creator"}),
                    required_fields=frozenset({"creator"}),
                )


class ImageUtilsExtraTests(unittest.TestCase):
    def test_generate_thumbnail_preserves_aspect_ratio_for_target_height(self):
        with tempfile.TemporaryDirectory() as tmp:
            image_path = Path(tmp) / "wide.jpg"
            Image.new("RGB", (200, 100), color=(120, 80, 160)).save(image_path)

            thumbnail = generate_thumbnail(image_path, target_height=50)

            self.assertEqual(thumbnail.size, (100, 50))

    def test_create_centered_text_image_writes_png(self):
        with tempfile.TemporaryDirectory() as tmp:
            image_path = Path(tmp) / "placeholder.png"

            create_centered_text_image(200, 100, "Missing", image_path)

            self.assertTrue(image_path.exists())
            with Image.open(image_path) as image:
                self.assertEqual(ImageDimensions(*image.size), ImageDimensions(width=200, height=100))


class AudioUtilsTests(unittest.TestCase):
    def test_get_audio_duration_seconds_reads_mutagen_info(self):
        fake_audio = types.SimpleNamespace(info=types.SimpleNamespace(length=42.5))
        fake_mutagen = types.SimpleNamespace(File=lambda path: fake_audio)

        with patch.dict(sys.modules, {"mutagen": fake_mutagen}):
            self.assertEqual(get_audio_duration_seconds(Path("track.mp3")), 42.5)

    def test_get_audio_duration_seconds_raises_when_mutagen_fails(self):
        fake_mutagen = types.SimpleNamespace(File=lambda path: (_ for _ in ()).throw(RuntimeError("bad audio")))

        with patch.dict(sys.modules, {"mutagen": fake_mutagen}):
            with self.assertRaises(RuntimeError):
                get_audio_duration_seconds(Path("track.mp3"))


class JsonUtilsTests(unittest.TestCase):
    def test_load_json_reads_object_from_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            json_path = Path(tmp) / "config.json"
            json_path.write_text('{"site": {"title": "Demo"}}', encoding="utf-8")

            self.assertEqual(load_json(json_path), {"site": {"title": "Demo"}})


class SortingUtilsTests(unittest.TestCase):
    def test_dated_title_sort_key_orders_dates_then_case_insensitive_titles(self):
        dated_b = dated_title_sort_key(datetime(2024, 1, 1), "Beta")
        dated_a = dated_title_sort_key(datetime(2024, 1, 1), "alpha")
        undated = dated_title_sort_key(None, "Aardvark")

        self.assertEqual(sorted([undated, dated_b, dated_a]), [dated_a, dated_b, undated])


if __name__ == "__main__":
    unittest.main()
