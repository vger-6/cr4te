import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from PIL import Image

from cr4te.config_manager import load_config
from cr4te.enums.portrait_discovery import PortraitDiscovery
from cr4te.library_scan import CreatorScan, iter_media_files, media_groups_from_buckets, rel_to_input


def write_image(path: Path, size: tuple[int, int] = (120, 90)) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color=(80, 120, 160)).save(path)


class LibraryScanTests(unittest.TestCase):
    def scan(
        self,
        creator_dir: Path,
        input_dir: Path,
        discovery: PortraitDiscovery = PortraitDiscovery.NAMED,
    ) -> CreatorScan:
        config = load_config()
        config.media_rules.portrait_discovery = discovery
        scan = CreatorScan(creator_dir, input_dir, config.media_rules)
        for media_path in iter_media_files(creator_dir, config.media_rules):
            scan.add_media(media_path)
        return scan

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
            scan = self.scan(creator_dir, input_dir)

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

    def test_direct_portrait_and_cover_names_win_over_nested_matches(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp) / "Artists"
            creator_dir = input_dir / "Ada"
            project_dir = creator_dir / "Project"

            write_image(creator_dir / "nested" / "portrait.jpg", (80, 160))
            write_image(creator_dir / "portrait.jpg", (80, 160))
            write_image(creator_dir / "portrait.png", (80, 160))
            write_image(project_dir / "nested" / "cover.jpg")
            write_image(project_dir / "cover.jpg")
            write_image(project_dir / "cover.png")

            scan = self.scan(creator_dir, input_dir)

            self.assertEqual(rel_to_input(scan.selected_portrait(), input_dir), "Ada/portrait.jpg")
            self.assertEqual(rel_to_input(scan.selected_cover("Project"), input_dir), "Ada/Project/cover.jpg")

    def test_nested_portrait_and_cover_names_are_selected_lexicographically(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp) / "Artists"
            creator_dir = input_dir / "Ada"
            project_dir = creator_dir / "Project"

            write_image(creator_dir / "z" / "portrait.jpg", (80, 160))
            write_image(creator_dir / "a" / "portrait.png", (80, 160))
            write_image(project_dir / "z" / "cover.jpg")
            write_image(project_dir / "a" / "cover.png")

            config = load_config()
            scan = CreatorScan(creator_dir, input_dir, config.media_rules)
            for media_path in reversed(list(iter_media_files(creator_dir, config.media_rules))):
                scan.add_media(media_path)

            self.assertEqual(rel_to_input(scan.selected_portrait(), input_dir), "Ada/a/portrait.png")
            self.assertEqual(rel_to_input(scan.selected_cover("Project"), input_dir), "Ada/Project/a/cover.png")

    def test_named_portrait_discovery_never_selects_an_unrelated_image(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp) / "Artists"
            creator_dir = input_dir / "Ada"
            write_image(creator_dir / "photo.jpg", (80, 160))

            scan = self.scan(creator_dir, input_dir, PortraitDiscovery.NAMED)

            self.assertIsNone(scan.selected_portrait())

    def test_auto_portrait_discovery_selects_portrait_orientation_but_not_landscape_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp) / "Artists"
            portrait_creator_dir = input_dir / "Ada"
            landscape_creator_dir = input_dir / "Bob"
            write_image(portrait_creator_dir / "photo.jpg", (80, 160))
            write_image(landscape_creator_dir / "photo.jpg", (160, 80))

            portrait_scan = self.scan(portrait_creator_dir, input_dir, PortraitDiscovery.AUTO)
            landscape_scan = self.scan(landscape_creator_dir, input_dir, PortraitDiscovery.AUTO)

            self.assertEqual(rel_to_input(portrait_scan.selected_portrait(), input_dir), "Ada/photo.jpg")
            self.assertIsNone(landscape_scan.selected_portrait())

    def test_named_portrait_is_assigned_to_role_and_not_gallery_media(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp) / "Artists"
            creator_dir = input_dir / "Ada"
            write_image(creator_dir / "portrait.jpg", (80, 160))

            config = load_config()
            scan = self.scan(creator_dir, input_dir)
            creator_groups = media_groups_from_buckets(scan.creator_buckets, config.media_rules)

            self.assertEqual(rel_to_input(scan.selected_portrait(), input_dir), "Ada/portrait.jpg")
            self.assertEqual(creator_groups[0].images, [])

    def test_cover_falls_back_to_landscape_then_any_image(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp) / "Artists"
            creator_dir = input_dir / "Ada"
            landscape_project = creator_dir / "Landscape Project"
            portrait_project = creator_dir / "Portrait Project"
            write_image(landscape_project / "z-portrait.jpg", (80, 160))
            write_image(landscape_project / "a-landscape.jpg", (160, 80))
            write_image(portrait_project / "only.jpg", (80, 160))

            scan = self.scan(creator_dir, input_dir)

            self.assertEqual(
                rel_to_input(scan.selected_cover("Landscape Project"), input_dir),
                "Ada/Landscape Project/a-landscape.jpg",
            )
            self.assertEqual(
                rel_to_input(scan.selected_cover("Portrait Project"), input_dir),
                "Ada/Portrait Project/only.jpg",
            )


if __name__ == "__main__":
    unittest.main()
