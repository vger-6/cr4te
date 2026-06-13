import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cr4te.enums.orientation import Orientation
from cr4te.media_cache import ImageDimensions
from cr4te.utils.image_utils import infer_image_orientation, parse_aspect_ratio, read_image_dimensions


class ImageUtilsTests(unittest.TestCase):
    def test_parse_aspect_ratio_accepts_positive_integer_width_and_height(self):
        valid_ratios = {
            "3/2": (3, 2),
            "2/3": (2, 3),
            "1/1": (1, 1),
            " 03 / 002 ": (3, 2),
            "1000/1414": (1000, 1414),
        }

        for value, expected in valid_ratios.items():
            with self.subTest(value=value):
                self.assertEqual(parse_aspect_ratio(value), expected)

    def test_parse_aspect_ratio_rejects_values_outside_the_supported_format(self):
        invalid_ratios = (
            "3",
            "3/2/1",
            "3.0/2",
            "3:2",
            "wide/tall",
            "0/2",
            "3/0",
            "-3/2",
            "3/-2",
            "+3/2",
            "",
            None,
            ["3", "2"],
        )

        for value in invalid_ratios:
            with self.subTest(value=value), self.assertRaisesRegex(
                ValueError,
                r"Aspect ratio must use two positive integers in width/height format, for example 3/2\.",
            ):
                parse_aspect_ratio(value)

    def test_read_image_dimensions_and_orientation_use_same_threshold(self):
        with tempfile.TemporaryDirectory() as tmp:
            image_path = Path(tmp) / "portrait.jpg"
            Image.new("RGB", (100, 130), color=(120, 80, 160)).save(image_path)

            dimensions = read_image_dimensions(image_path)

            self.assertEqual(dimensions, ImageDimensions(width=100, height=130))
            self.assertEqual(infer_image_orientation(image_path), Orientation.PORTRAIT)

    def test_unreadable_image_dimensions_raise_and_orientation_falls_back_to_landscape(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing_path = Path(tmp) / "missing.jpg"

            with self.assertRaises(FileNotFoundError):
                read_image_dimensions(missing_path)

            self.assertEqual(infer_image_orientation(missing_path), Orientation.LANDSCAPE)


if __name__ == "__main__":
    unittest.main()
