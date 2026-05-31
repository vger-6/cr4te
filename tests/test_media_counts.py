import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cr4te.media_counts import MediaCounts, count_media_groups
from cr4te.schemas.library_schema import MediaGroup, Video


def media_group(**overrides) -> MediaGroup:
    data = {
        "is_root": False,
        "videos": [],
        "tracks": [],
        "images": [],
        "documents": [],
        "texts": [],
        "rel_dir_path": "",
    }
    data.update(overrides)
    return MediaGroup(**data)


class MediaCountsTests(unittest.TestCase):
    def test_count_media_groups_accumulates_each_media_kind(self):
        counts = count_media_groups(
            [
                media_group(
                    videos=[Video(file="clip.mp4", poster="clip.jpg")],
                    tracks=["song.mp3", "live.flac"],
                    images=["cover.jpg"],
                ),
                media_group(
                    documents=["notes.pdf", "booklet.pdf"],
                    texts=["lyrics.txt"],
                ),
            ]
        )

        self.assertEqual(counts, MediaCounts(video=1, audio=2, image=1, document=2, text=1))


if __name__ == "__main__":
    unittest.main()
