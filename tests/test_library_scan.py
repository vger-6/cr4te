import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from PIL import Image

from cr4te.config_manager import load_config
from cr4te.enums.orientation import Orientation
from cr4te.enums.portrait_discovery import PortraitDiscovery
from cr4te.library_scan import CreatorScan, iter_media_files, rel_to_input


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

            scan = self.scan(creator_dir, input_dir)

            self.assertEqual(rel_to_input(scan.selected_portrait(), input_dir), "Ada/portrait.jpg")
            self.assertEqual(rel_to_input(scan.selected_cover("Project"), input_dir), "Ada/Project/cover.jpg")

            creator_groups = scan.creator_media_groups()
            self.assertEqual(len(creator_groups), 1)
            self.assertEqual(creator_groups[0].images, ["Ada/gallery.jpg"])

            project_groups = scan.project_media_groups("Project")
            self.assertEqual(len(project_groups), 1)
            self.assertEqual(project_groups[0].images, ["Ada/Project/scene.jpg"])
            self.assertEqual(project_groups[0].videos[0].file, "Ada/Project/video.mp4")
            self.assertEqual(project_groups[0].videos[0].poster, "Ada/Project/video.jpg")

    def test_media_groups_prioritize_root_then_configured_metadata_folder(self):
        """Covers SITE-019."""
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp) / "Artists"
            creator_dir = input_dir / "Ada"
            project_dir = creator_dir / "Project"

            for path in (
                creator_dir / "root.md",
                creator_dir / "archive" / "nested" / "notes.md",
                creator_dir / "archive" / "notes.md",
                creator_dir / "meta" / "notes.md",
                project_dir / "root.md",
                project_dir / "meta" / "notes.md",
                project_dir / "a" / "notes.md",
                project_dir / "a" / "nested" / "notes.md",
                project_dir / "b" / "notes.md",
            ):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("Notes", encoding="utf-8")

            scan = self.scan(creator_dir, input_dir)

            creator_groups = scan.creator_media_groups()
            project_groups = scan.project_media_groups("Project")

            self.assertEqual(
                [group.rel_dir_path for group in creator_groups],
                ["Ada", "Ada/meta"],
            )
            self.assertEqual(
                [group.rel_dir_path for group in project_groups],
                ["Ada/Project", "Ada/Project/meta", "Ada/Project/a", "Ada/Project/a/nested", "Ada/Project/b"],
            )

    def test_media_groups_prioritize_custom_metadata_folder_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp) / "Artists"
            creator_dir = input_dir / "Ada"
            project_dir = creator_dir / "Project"

            for path in (
                project_dir / "root.md",
                project_dir / "a" / "notes.md",
                project_dir / "details" / "notes.md",
            ):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("Notes", encoding="utf-8")

            config = load_config()
            config.media_rules.metadata_folder_name = "details"
            scan = CreatorScan(creator_dir, input_dir, config.media_rules)
            for media_path in iter_media_files(creator_dir, config.media_rules):
                scan.add_media(media_path)

            groups = scan.project_media_groups("Project")

            self.assertEqual(
                [group.rel_dir_path for group in groups],
                ["Ada/Project", "Ada/Project/details", "Ada/Project/a"],
            )

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

    def test_named_portrait_and_cover_matching_is_case_insensitive(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp) / "Artists"
            creator_dir = input_dir / "Ada"
            project_dir = creator_dir / "Project"
            portrait_path = creator_dir / "PORTRAIT.jpg"
            cover_path = project_dir / "COVER.jpg"
            write_image(portrait_path, (80, 160))
            write_image(cover_path)

            scan = self.scan(creator_dir, input_dir)

            self.assertEqual(scan.selected_portrait(), portrait_path)
            self.assertEqual(scan.selected_cover("Project"), cover_path)

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

            scan = self.scan(creator_dir, input_dir)
            creator_groups = scan.creator_media_groups()

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

    def test_portrait_fallback_searches_projects_and_may_share_a_fallback_cover(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp) / "Artists"
            creator_dir = input_dir / "Ada"
            project_dir = creator_dir / "Project"
            write_image(project_dir / "photo.jpg", (80, 160))

            scan = self.scan(creator_dir, input_dir, PortraitDiscovery.AUTO)

            self.assertEqual(rel_to_input(scan.selected_portrait(), input_dir), "Ada/Project/photo.jpg")
            self.assertEqual(rel_to_input(scan.selected_cover("Project"), input_dir), "Ada/Project/photo.jpg")
            self.assertEqual(scan.project_media_groups("Project")[0].images, [])

    def test_selected_cover_fallback_is_excluded_but_unselected_candidates_remain(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp) / "Artists"
            creator_dir = input_dir / "Ada"
            project_dir = creator_dir / "Project"
            write_image(project_dir / "a-landscape.jpg", (160, 80))
            write_image(project_dir / "b-landscape.jpg", (160, 80))

            config = load_config()
            config.media_rules.image_gallery_sample_max = 1
            scan = CreatorScan(creator_dir, input_dir, config.media_rules)
            for media_path in iter_media_files(creator_dir, config.media_rules):
                scan.add_media(media_path)

            self.assertEqual(rel_to_input(scan.selected_cover("Project"), input_dir), "Ada/Project/a-landscape.jpg")
            self.assertEqual(scan.project_media_groups("Project")[0].images, ["Ada/Project/b-landscape.jpg"])

    def test_all_named_role_candidates_are_excluded_from_galleries(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp) / "Artists"
            creator_dir = input_dir / "Ada"
            project_dir = creator_dir / "Project"
            write_image(creator_dir / "portrait.jpg", (80, 160))
            write_image(creator_dir / "nested" / "portrait.png", (80, 160))
            write_image(project_dir / "cover.jpg")
            write_image(project_dir / "nested" / "cover.png")
            write_image(project_dir / "gallery.jpg")

            scan = self.scan(creator_dir, input_dir)

            self.assertEqual(scan.creator_media_groups()[0].images, [])
            project_images = [image for group in scan.project_media_groups("Project") for image in group.images]
            self.assertEqual(project_images, ["Ada/Project/gallery.jpg"])

    def test_video_posters_use_common_order_and_all_candidates_are_excluded(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp) / "Artists"
            creator_dir = input_dir / "Ada"
            project_dir = creator_dir / "Project"
            write_image(project_dir / "clip.jpg")
            write_image(project_dir / "clip.jpeg")
            write_image(project_dir / "CLIP.png")
            (project_dir / "clip.mp4").write_bytes(b"video")

            scan = self.scan(creator_dir, input_dir)
            group = scan.project_media_groups("Project")[0]

            self.assertEqual(group.videos[0].poster, "Ada/Project/clip.jpeg")
            self.assertEqual(group.images, [])

    def test_poster_candidates_are_not_used_as_fallbacks_but_may_match_named_roles(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp) / "Artists"
            creator_dir = input_dir / "Ada"
            project_dir = creator_dir / "Project"
            poster_path = project_dir / "clip.jpg"
            write_image(poster_path, (80, 160))
            (project_dir / "clip.mp4").write_bytes(b"video")

            fallback_scan = self.scan(creator_dir, input_dir, PortraitDiscovery.AUTO)
            self.assertIsNone(fallback_scan.selected_portrait())
            self.assertIsNone(fallback_scan.selected_cover("Project"))

            config = load_config()
            config.media_rules.portrait_discovery = PortraitDiscovery.AUTO
            config.media_rules.portrait_basename = "clip"
            config.media_rules.cover_basename = "clip"
            named_scan = CreatorScan(creator_dir, input_dir, config.media_rules)
            for media_path in iter_media_files(creator_dir, config.media_rules):
                named_scan.add_media(media_path)

            self.assertEqual(named_scan.selected_portrait(), poster_path)
            self.assertEqual(named_scan.selected_cover("Project"), poster_path)

    def test_special_image_resolution_is_independent_of_scan_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp) / "Artists"
            creator_dir = input_dir / "Ada"
            project_dir = creator_dir / "Project"
            write_image(creator_dir / "z" / "portrait.jpg", (80, 160))
            write_image(creator_dir / "a" / "portrait.png", (80, 160))
            write_image(project_dir / "b-landscape.jpg", (160, 80))
            write_image(project_dir / "a-landscape.jpg", (160, 80))
            write_image(project_dir / "clip.jpg")
            write_image(project_dir / "clip.jpeg")
            (project_dir / "clip.mp4").write_bytes(b"video")

            config = load_config()
            media_paths = list(iter_media_files(creator_dir, config.media_rules))
            scans = []
            for paths in (media_paths, reversed(media_paths)):
                scan = CreatorScan(creator_dir, input_dir, config.media_rules)
                for media_path in paths:
                    scan.add_media(media_path)
                scans.append(scan)

            resolved = [
                (
                    scan.selected_portrait(),
                    scan.selected_cover("Project"),
                    scan.project_media_groups("Project"),
                )
                for scan in scans
            ]
            self.assertEqual(resolved[0], resolved[1])

    def test_shared_fallback_image_orientation_is_inspected_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp) / "Artists"
            creator_dir = input_dir / "Ada"
            project_dir = creator_dir / "Project"
            image_path = project_dir / "photo.jpg"
            write_image(image_path, (80, 160))

            with patch(
                "cr4te.library_scan.image_utils.infer_image_orientation",
                return_value=Orientation.PORTRAIT,
            ) as infer_orientation:
                scan = self.scan(creator_dir, input_dir, PortraitDiscovery.AUTO)
                scan.selected_portrait()
                scan.selected_cover("Project")

            infer_orientation.assert_called_once_with(image_path)


if __name__ == "__main__":
    unittest.main()
