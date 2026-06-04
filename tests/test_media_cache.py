import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cr4te.enums.orientation import Orientation
from cr4te.media_cache import ImageDimensions, MediaInfoCache


class MediaInfoCacheTests(unittest.TestCase):
    def test_image_dimensions_are_reused_and_bounded(self):
        cache = MediaInfoCache(max_entries=1)
        calls = []

        def load(width: int):
            def _loader():
                calls.append(width)
                return ImageDimensions(width=width, height=width + 10)

            return _loader

        first = cache.image_dimensions(Path("a.jpg"), load(100))
        second = cache.image_dimensions(Path("a.jpg"), load(200))
        third = cache.image_dimensions(Path("b.jpg"), load(300))
        fourth = cache.image_dimensions(Path("a.jpg"), load(400))

        self.assertEqual(first, second)
        self.assertEqual(third.width, 300)
        self.assertEqual(fourth.width, 400)
        self.assertEqual(calls, [100, 300, 400])
        self.assertEqual(cache.image_dimension_count, 1)

    def test_cache_can_be_disabled(self):
        cache = MediaInfoCache(max_entries=0)
        calls = []

        def loader():
            calls.append("load")
            return 12.5

        self.assertEqual(cache.audio_duration_seconds(Path("song.mp3"), loader), 12.5)
        self.assertEqual(cache.audio_duration_seconds(Path("song.mp3"), loader), 12.5)

        self.assertEqual(calls, ["load", "load"])
        self.assertEqual(cache.audio_duration_count, 0)

    def test_image_dimensions_resolve_orientation(self):
        self.assertEqual(ImageDimensions(width=100, height=130).orientation, Orientation.PORTRAIT)
        self.assertEqual(ImageDimensions(width=100, height=120).orientation, Orientation.LANDSCAPE)
        self.assertEqual(ImageDimensions().orientation, Orientation.LANDSCAPE)


if __name__ == "__main__":
    unittest.main()
