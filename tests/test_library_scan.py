import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from PIL import Image

from cr4te.config_manager import load_config
from cr4te.library_scan import CreatorScan, iter_media_files, media_groups_from_buckets, rel_to_input


def write_image(path: Path, size: tuple[int, int] = (120, 90)) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color=(80, 120, 160)).save(path)


class LibraryScanTests(unittest.TestCase):
    def test_scan_buckets_media_and_selects_portrait_cover(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp) / "Artists"
            creator_dir = input_dir / "Ada"
            project_dir = creator_dir / "Project"

            write_image(creator_dir / "portrait.jpg", (80, 160))
            write_image(creator_dir / "gallery.jpg")
            write_image(project_dir / "cover.jpg")
            write_image(project_dir / "scene.jpg")
            write_image(project_dir / "video.jpg")
            (project_dir / "video.mp4").write_bytes(b"video")
            (project_dir / "README.md").write_text("Project notes", encoding="utf-8")

            media_rules = load_config().media_rules
            scan = CreatorScan(creator_dir, input_dir, media_rules)
            for media_path in iter_media_files(creator_dir, media_rules):
                scan.add_media(media_path)

            self.assertEqual(rel_to_input(scan.selected_portrait(), input_dir), "Ada/portrait.jpg")
            self.assertEqual(rel_to_input(scan.selected_cover("Project"), input_dir), "Ada/Project/cover.jpg")

            creator_groups = media_groups_from_buckets(scan.creator_buckets, media_rules)
            self.assertEqual(len(creator_groups), 1)
            self.assertEqual(creator_groups[0].images, ["Ada/gallery.jpg"])

            project_groups = media_groups_from_buckets(scan.project_buckets["Project"], media_rules)
            self.assertEqual(len(project_groups), 1)
            self.assertEqual(project_groups[0].images, ["Ada/Project/scene.jpg"])
            self.assertEqual(project_groups[0].videos[0].file, "Ada/Project/video.mp4")
            self.assertEqual(project_groups[0].videos[0].poster, "Ada/Project/video.jpg")


if __name__ == "__main__":
    unittest.main()
