import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cr4te.enums.orientation import Orientation
from cr4te.media_cache import ImageDimensions
from cr4te.utils.image_utils import infer_image_orientation, read_image_dimensions


class ImageUtilsTests(unittest.TestCase):
    def test_read_image_dimensions_and_orientation_use_same_threshold(self):
        with tempfile.TemporaryDirectory() as tmp:
            image_path = Path(tmp) / "portrait.jpg"
            Image.new("RGB", (100, 130), color=(120, 80, 160)).save(image_path)

            dimensions = read_image_dimensions(image_path)

            self.assertEqual(dimensions, ImageDimensions(width=100, height=130))
            self.assertEqual(infer_image_orientation(image_path), Orientation.PORTRAIT)

    def test_unreadable_image_dimensions_fall_back_to_landscape(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing_path = Path(tmp) / "missing.jpg"

            with self.assertLogs("cr4te.utils.image_utils", level="WARNING"):
                dimensions = read_image_dimensions(missing_path)

            self.assertEqual(dimensions, ImageDimensions())
            self.assertEqual(dimensions.orientation, Orientation.LANDSCAPE)


if __name__ == "__main__":
    unittest.main()
