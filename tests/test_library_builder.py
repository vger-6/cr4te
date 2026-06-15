import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from PIL import Image

from cr4te.config_manager import apply_cli_overrides, load_config
from cr4te.build_issues import BuildIssueError, IssueCode, IssueScope, IssueSeverity
from cr4te.enums.creator_type import CreatorType
from cr4te.enums.domain import Domain
from cr4te.enums.portrait_discovery import PortraitDiscovery
from cr4te.enums.visible_fields import ProjectField
from cr4te.library_builder import build_library_index, load_indexed_creator


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def write_image(path: Path, size: tuple[int, int] = (120, 90)) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color=(80, 120, 160)).save(path)


class LibraryBuilderTests(unittest.TestCase):
    def build_config(self, domain: Domain = Domain.ART):
        return apply_cli_overrides(load_config(), domain=domain)

    def test_creator_metadata_file_builds_typed_library(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "Artists"
            creator_dir = root / "Noomi"
            project_dir = creator_dir / "Landscapes"
            playlist_dir = project_dir / "Travel Playlist"

            write_image(creator_dir / "portrait.jpg", (80, 160))
            write_image(creator_dir / "img_001.jpg")
            write_image(project_dir / "cover.jpg")
            write_image(project_dir / "cloud.jpg")
            playlist_dir.mkdir(parents=True)
            (playlist_dir / "01 track.mp3").write_bytes(b"not real audio")
            (creator_dir / "README.md").write_text("Creator **bio**", encoding="utf-8")
            (project_dir / "README.md").write_text("Project **notes**", encoding="utf-8")

            write_json(
                creator_dir / "cr4te.json",
                {
                    "display_name": "Displayed Noomi",
                    "type": "person",
                    "person": {
                        "active_since": "2020",
                        "birth": {"date": "1990-04", "place": "Berlin"},
                        "nationalities": ["German"],
                    },
                    "tags": {"Genre": ["Landscape"]},
                },
            )
            write_json(
                project_dir / "cr4te.json",
                {
                    "display_title": "Displayed Landscapes",
                    "release_date": "2024-03-12",
                    "tags": {"Mood": ["Quiet"]},
                    "facets": {
                        "mediums": ["Photography"],
                        "periods": ["Contemporary"],
                    },
                },
            )
            original_creator_json = (creator_dir / "cr4te.json").read_text(encoding="utf-8")

            index = build_library_index(root, self.build_config().media_rules)
            self.assertEqual(len(index.creators), 1)
            summary = index.creator_by_name["Noomi"]
            creator = load_indexed_creator(index, summary, self.build_config().media_rules)
            self.assertEqual(creator.name, "Noomi")
            self.assertEqual(creator.display_name, "Displayed Noomi")
            self.assertEqual(creator.type, CreatorType.PERSON)
            self.assertEqual(creator.date_of_birth, "1990-04")
            self.assertEqual(creator.place_of_birth, "Berlin")
            self.assertEqual(creator.active_since, "2020")
            self.assertEqual(creator.info, "Creator **bio**")
            self.assertEqual(creator.portrait, "Noomi/portrait.jpg")
            self.assertEqual(creator.media_groups[0].images, ["Noomi/img_001.jpg"])

            self.assertEqual(len(creator.projects), 1)
            project = creator.projects[0]
            self.assertEqual(project.title, "Landscapes")
            self.assertEqual(project.display_title, "Displayed Landscapes")
            self.assertEqual(project.release_date, "2024-03-12")
            self.assertEqual(project.cover, "Noomi/Landscapes/cover.jpg")
            self.assertEqual(project.info, "Project **notes**")
            self.assertEqual(project.facets[ProjectField.MEDIUMS], ["Photography"])
            self.assertEqual(project.facets[ProjectField.PERIODS], ["Contemporary"])

            rel_paths = [group.rel_dir_path for group in project.media_groups]
            self.assertIn("Noomi/Landscapes", rel_paths)
            self.assertIn("Noomi/Landscapes/Travel Playlist", rel_paths)
            self.assertTrue(all("\\" not in path for path in rel_paths))
            self.assertEqual((creator_dir / "cr4te.json").read_text(encoding="utf-8"), original_creator_json)

    def test_named_portrait_is_discovered_and_assigned_in_built_library(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "Artists"
            creator_dir = root / "Noomi"
            write_image(creator_dir / "portrait.jpg", (80, 160))
            config = self.build_config()

            index = build_library_index(root, config.media_rules)
            summary = index.creator_by_name["Noomi"]
            creator = load_indexed_creator(index, summary, config.media_rules)

            self.assertEqual(summary.portrait, "Noomi/portrait.jpg")
            self.assertEqual(creator.portrait, "Noomi/portrait.jpg")
            self.assertEqual(creator.media_groups[0].images, [])

    def test_auto_selected_portrait_is_not_duplicated_in_gallery_media(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "Artists"
            creator_dir = root / "Noomi"
            write_image(creator_dir / "photo.jpg", (80, 160))
            config = self.build_config()
            config.media_rules.portrait_discovery = PortraitDiscovery.AUTO

            index = build_library_index(root, config.media_rules)
            summary = index.creator_by_name["Noomi"]
            creator = load_indexed_creator(index, summary, config.media_rules)

            self.assertEqual(summary.portrait, "Noomi/photo.jpg")
            self.assertEqual(creator.media_groups[0].images, [])

    def test_shared_portrait_and_cover_fallback_is_not_duplicated_in_gallery_media(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "Artists"
            project_dir = root / "Noomi" / "Landscapes"
            write_image(project_dir / "photo.jpg", (80, 160))
            config = self.build_config()
            config.media_rules.portrait_discovery = PortraitDiscovery.AUTO

            index = build_library_index(root, config.media_rules)
            creator = load_indexed_creator(index, index.creator_by_name["Noomi"], config.media_rules)

            self.assertEqual(creator.portrait, "Noomi/Landscapes/photo.jpg")
            self.assertEqual(creator.projects[0].cover, "Noomi/Landscapes/photo.jpg")
            self.assertEqual(creator.projects[0].media_groups[0].images, [])

    def test_library_index_keeps_lightweight_creator_and_project_summaries(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "Artists"
            creator_dir = root / "Noomi"
            project_dir = creator_dir / "Landscapes"
            write_image(creator_dir / "portrait.jpg", (80, 160))
            write_image(creator_dir / "creator-image.jpg")
            write_image(project_dir / "cover.jpg")
            write_image(project_dir / "project-image.jpg")
            write_json(
                creator_dir / "cr4te.json",
                {
                    "display_name": "   ",
                },
            )
            write_json(
                project_dir / "cr4te.json",
                {
                    "display_title": "   ",
                    "facets": {"mediums": ["Photography"]},
                },
            )

            index = build_library_index(root, self.build_config().media_rules)

            self.assertEqual(len(index.creators), 1)
            summary = index.creator_by_name["Noomi"]
            self.assertEqual(summary.display_name, "Noomi")
            self.assertEqual(summary.project_count, 1)
            self.assertEqual(summary.media_counts.image, 2)
            self.assertFalse(hasattr(summary, "media_groups"))
            self.assertEqual(summary.projects[0].media_counts.image, 1)
            self.assertEqual(summary.projects[0].display_title, "Landscapes")
            self.assertFalse(hasattr(summary.projects[0], "media_groups"))

            creator = load_indexed_creator(index, summary, self.build_config().media_rules)
            self.assertEqual(creator.name, "Noomi")
            self.assertTrue(creator.media_groups)
            self.assertTrue(creator.projects[0].media_groups)

    def test_library_index_does_not_discover_or_carry_themes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "Artists"
            theme_path = Path(tmp) / "themes" / "invalid.css"
            root.mkdir()
            theme_path.parent.mkdir(parents=True)
            theme_path.write_text(".theme-other {}", encoding="utf-8")

            index = build_library_index(root, self.build_config().media_rules)

            self.assertEqual(index.creators, ())
            self.assertEqual(index.issues, ())
            self.assertFalse(hasattr(index, "themes"))

    def test_collaboration_links_are_computed_in_memory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "Artists"
            for name in ("Ada", "Bob", "Ada & Bob"):
                (root / name).mkdir(parents=True)

            write_json(
                root / "Ada & Bob" / "cr4te.json",
                {
                    "display_name": "The Pair",
                    "type": "collaboration",
                    "collaboration": {"members": ["Ada", "Bob"]},
                },
            )

            index = build_library_index(root, self.build_config().media_rules)
            creators = {name: load_indexed_creator(index, index.creator_by_name[name], self.build_config().media_rules) for name in index.creator_by_name}

            self.assertEqual(creators["Ada & Bob"].type, CreatorType.COLLABORATION)
            self.assertEqual(creators["Ada & Bob"].display_name, "The Pair")
            self.assertEqual(creators["Ada & Bob"].members, ["Ada", "Bob"])
            self.assertEqual(creators["Ada"].collaborations, ["Ada & Bob"])
            self.assertEqual(creators["Bob"].collaborations, ["Ada & Bob"])
            self.assertEqual((root / "Ada" / "cr4te.json").exists(), False)

    def test_collaboration_members_default_from_folder_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "Artists"
            for name in ("Ada", "Bob", "Ada & Bob"):
                (root / name).mkdir(parents=True)

            write_json(root / "Ada & Bob" / "cr4te.json", {"type": "collaboration"})

            index = build_library_index(root, self.build_config().media_rules)
            collaboration = load_indexed_creator(
                index,
                index.creator_by_name["Ada & Bob"],
                self.build_config().media_rules,
            )

            self.assertEqual(collaboration.type, CreatorType.COLLABORATION)
            self.assertEqual(collaboration.members, ["Ada", "Bob"])

    def test_invalid_collaboration_reference_is_reported_as_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "Artists"
            write_json(root / "Ada" / "cr4te.json", {"collaborations": ["Missing Duo"]})

            index = build_library_index(root, self.build_config().media_rules, strict=True)

            self.assertEqual([summary.name for summary in index.creators], ["Ada"])
            self.assertEqual(index.creators[0].collaborations, ())
            self.assertEqual(len(index.issues), 1)
            issue = index.issues[0]
            self.assertEqual(issue.scope, IssueScope.CREATOR)
            self.assertEqual(issue.code, IssueCode.INVALID_COLLABORATION_REFERENCE)
            self.assertEqual(issue.severity, IssueSeverity.WARNING)
            self.assertIn("Missing Duo", issue.message)

    def test_invalid_metadata_is_reported_as_issue_in_best_effort_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "Artists"
            (root / "Good").mkdir(parents=True)
            bad_dir = root / "Bad"
            bad_dir.mkdir(parents=True)
            (bad_dir / "cr4te.json").write_text("[1, 2, 3]", encoding="utf-8")

            index = build_library_index(root, self.build_config().media_rules)

            self.assertEqual([summary.name for summary in index.creators], ["Good"])
            self.assertEqual(len(index.issues), 1)
            self.assertEqual(index.issues[0].path, bad_dir)
            self.assertEqual(index.issues[0].scope, IssueScope.CREATOR)
            self.assertEqual(index.issues[0].code, IssueCode.INVALID_METADATA_SHAPE)
            self.assertIn("JSON object", index.issues[0].message)

    def test_invalid_metadata_raises_in_strict_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "Artists"
            bad_dir = root / "Bad"
            bad_dir.mkdir(parents=True)
            (bad_dir / "cr4te.json").write_text("{not json", encoding="utf-8")

            with self.assertRaises(BuildIssueError) as caught:
                build_library_index(root, self.build_config().media_rules, strict=True)
            self.assertEqual(caught.exception.issue.code, IssueCode.INVALID_JSON)
            self.assertEqual(caught.exception.issue.scope, IssueScope.CREATOR)

    def test_invalid_creator_date_is_reported_as_metadata_issue(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "Artists"
            bad_dir = root / "Bad Date"
            write_json(
                bad_dir / "cr4te.json",
                {"person": {"birth": {"date": "April 1990"}}},
            )

            index = build_library_index(root, self.build_config().media_rules)

            self.assertEqual(index.creators, ())
            self.assertEqual(len(index.issues), 1)
            self.assertEqual(index.issues[0].path, bad_dir)
            self.assertEqual(index.issues[0].scope, IssueScope.CREATOR)
            self.assertEqual(index.issues[0].code, IssueCode.INVALID_METADATA)
            self.assertIn("yyyy", index.issues[0].message)

    def test_extra_creator_metadata_field_is_reported_as_issue(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "Artists"
            bad_dir = root / "Noomi"
            write_json(bad_dir / "cr4te.json", {"info": "Use README.md instead"})

            index = build_library_index(root, self.build_config().media_rules)

            self.assertEqual(index.creators, ())
            self.assertEqual(len(index.issues), 1)
            self.assertEqual(index.issues[0].path, bad_dir)
            self.assertEqual(index.issues[0].scope, IssueScope.CREATOR)
            self.assertEqual(index.issues[0].code, IssueCode.INVALID_METADATA)
            self.assertIn("info", index.issues[0].message)
            self.assertIn("Extra inputs", index.issues[0].message)

    def test_invalid_project_metadata_skips_project_not_creator_in_best_effort_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "Artists"
            good_project = root / "Noomi" / "Good Project"
            bad_project = root / "Noomi" / "Bad Project"
            good_project.mkdir(parents=True)
            bad_project.mkdir(parents=True)
            write_json(good_project / "cr4te.json", {})
            (bad_project / "cr4te.json").write_text("[1, 2, 3]", encoding="utf-8")

            index = build_library_index(root, self.build_config().media_rules)

            self.assertEqual(len(index.creators), 1)
            self.assertEqual(index.creators[0].name, "Noomi")
            self.assertEqual([project.title for project in index.creators[0].projects], ["Good Project"])
            self.assertEqual(len(index.issues), 1)
            self.assertEqual(index.issues[0].path, bad_project)
            self.assertEqual(index.issues[0].scope, IssueScope.PROJECT)
            self.assertEqual(index.issues[0].code, IssueCode.INVALID_METADATA_SHAPE)

    def test_invalid_project_release_date_is_reported_as_project_issue(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "Artists"
            good_project = root / "Noomi" / "Good Project"
            bad_project = root / "Noomi" / "Bad Date"
            good_project.mkdir(parents=True)
            bad_project.mkdir(parents=True)
            write_json(good_project / "cr4te.json", {})
            write_json(bad_project / "cr4te.json", {"release_date": "Spring 2024"})

            index = build_library_index(root, self.build_config().media_rules)

            self.assertEqual(len(index.creators), 1)
            self.assertEqual([project.title for project in index.creators[0].projects], ["Good Project"])
            self.assertEqual(len(index.issues), 1)
            self.assertEqual(index.issues[0].path, bad_project)
            self.assertEqual(index.issues[0].scope, IssueScope.PROJECT)
            self.assertEqual(index.issues[0].code, IssueCode.INVALID_METADATA)
            self.assertIn("yyyy", index.issues[0].message)

    def test_extra_project_metadata_field_is_reported_as_issue(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "Artists"
            good_project = root / "Noomi" / "Good Project"
            bad_project = root / "Noomi" / "Bad Project"
            good_project.mkdir(parents=True)
            bad_project.mkdir(parents=True)
            write_json(good_project / "cr4te.json", {})
            write_json(bad_project / "cr4te.json", {"info": "Use README.md instead"})

            index = build_library_index(root, self.build_config().media_rules)

            self.assertEqual(len(index.creators), 1)
            self.assertEqual([project.title for project in index.creators[0].projects], ["Good Project"])
            self.assertEqual(len(index.issues), 1)
            self.assertEqual(index.issues[0].path, bad_project)
            self.assertEqual(index.issues[0].scope, IssueScope.PROJECT)
            self.assertEqual(index.issues[0].code, IssueCode.INVALID_METADATA)
            self.assertIn("info", index.issues[0].message)
            self.assertIn("Extra inputs", index.issues[0].message)

    def test_invalid_project_metadata_raises_in_strict_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "Artists"
            bad_project = root / "Noomi" / "Bad Project"
            bad_project.mkdir(parents=True)
            (bad_project / "cr4te.json").write_text("[1, 2, 3]", encoding="utf-8")

            with self.assertRaises(BuildIssueError) as caught:
                build_library_index(root, self.build_config().media_rules, strict=True)
            self.assertEqual(caught.exception.issue.scope, IssueScope.PROJECT)
            self.assertEqual(caught.exception.issue.code, IssueCode.INVALID_METADATA_SHAPE)

    def test_project_cover_metadata_field_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "Artists"
            project_dir = root / "Noomi" / "Bad Cover"
            project_dir.mkdir(parents=True)
            write_json(project_dir / "cr4te.json", {"cover": "cover.jpg"})

            index = build_library_index(root, self.build_config().media_rules)

            self.assertEqual(len(index.creators), 1)
            self.assertEqual(index.creators[0].projects, ())
            self.assertEqual(len(index.issues), 1)
            self.assertEqual(index.issues[0].scope, IssueScope.PROJECT)
            self.assertEqual(index.issues[0].code, IssueCode.INVALID_METADATA)
            self.assertIn("cover", index.issues[0].message)
            self.assertIn("Extra inputs", index.issues[0].message)

    def test_creator_portrait_metadata_field_is_rejected_in_strict_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "Artists"
            creator_dir = root / "Noomi"
            creator_dir.mkdir(parents=True)
            write_json(creator_dir / "cr4te.json", {"portrait": "portrait.jpg"})

            with self.assertRaises(BuildIssueError) as caught:
                build_library_index(root, self.build_config().media_rules, strict=True)
            self.assertEqual(caught.exception.issue.scope, IssueScope.CREATOR)
            self.assertEqual(caught.exception.issue.code, IssueCode.INVALID_METADATA)

if __name__ == "__main__":
    unittest.main()
