import json
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cr4te.config_manager import apply_cli_overrides, load_config
from cr4te.build_issues import IssueCode, IssueScope
from cr4te.enums.domain import Domain
from cr4te.metadata_manager import delete_metadata_files, reconcile_metadata_files


def write_image(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (120, 90), color=(120, 90, 80)).save(path)


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class MetadataManagerTests(unittest.TestCase):
    def art_config(self):
        return apply_cli_overrides(load_config(), domain=Domain.ART)

    def reconcile_art_metadata(self, root: Path, dry_run: bool = False):
        config = self.art_config()
        return reconcile_metadata_files(
            root,
            config.media_rules,
            config.site_rendering.project_metadata.configured_fields(),
            dry_run=dry_run,
        )

    def test_reconcile_metadata_creates_creator_and_project_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "Artists"
            creator_dir = root / "Noomi"
            project_dir = creator_dir / "Landscapes"
            write_image(creator_dir / "portrait.jpg")
            write_image(project_dir / "cover.jpg")

            result = self.reconcile_art_metadata(root)

            self.assertEqual(len(result.created), 2)
            metadata = read_json(creator_dir / "cr4te.json")

            self.assertEqual(metadata["display_name"], "Noomi")
            self.assertNotIn("name", metadata)
            self.assertEqual(metadata["type"], "person")
            self.assertNotIn("portrait", metadata)
            self.assertIn("nationalities", metadata["person"])
            self.assertNotIn("collaboration", metadata)
            self.assertNotIn("info", metadata)
            self.assertNotIn("media_groups", metadata)
            self.assertNotIn("projects", metadata)

            project_metadata = read_json(project_dir / "cr4te.json")
            self.assertEqual(project_metadata["display_title"], "Landscapes")
            self.assertNotIn("title", project_metadata)
            self.assertNotIn("cover", project_metadata)
            self.assertEqual(project_metadata["facets"]["mediums"], [])
            self.assertEqual(project_metadata["facets"]["materials"], [])
            self.assertNotIn("info", project_metadata)

    def test_reconcile_metadata_preserves_display_values_and_adds_missing_project_facets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "Artists"
            project_dir = root / "Noomi" / "Landscapes"
            project_dir.mkdir(parents=True)
            metadata_path = root / "Noomi" / "cr4te.json"
            project_metadata_path = project_dir / "cr4te.json"
            write_json(
                metadata_path,
                {
                    "display_name": "Custom",
                    "type": "person",
                    "person": {"birth": {"date": "1990"}},
                },
            )
            write_json(
                project_metadata_path,
                {
                    "display_title": "Custom Title",
                    "facets": {"mediums": ["Photography"]},
                },
            )

            result = self.reconcile_art_metadata(root)

            synced = read_json(metadata_path)
            self.assertEqual(len(result.updated), 2)
            self.assertEqual(synced["display_name"], "Custom")
            self.assertEqual(synced["person"]["birth"]["date"], "1990")
            project_synced = read_json(project_metadata_path)
            self.assertEqual(project_synced["display_title"], "Custom Title")
            self.assertEqual(project_synced["facets"]["mediums"], ["Photography"])
            self.assertEqual(project_synced["facets"]["materials"], [])
            self.assertEqual(project_synced["facets"]["exhibitions"], [])
            self.assertEqual(project_synced["facets"]["periods"], [])

    def test_reconcile_metadata_prunes_empty_inactive_type_branch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "Artists"
            creator_dir = root / "Noomi & Ada"
            metadata_path = creator_dir / "cr4te.json"
            write_json(
                metadata_path,
                {
                    "type": "collaboration",
                    "person": {
                        "active_since": "",
                        "birth": {"date": "", "place": ""},
                        "death": {"date": "", "place": ""},
                        "civil_name": "",
                        "nationalities": [],
                    },
                },
            )

            self.reconcile_art_metadata(root)

            synced = read_json(metadata_path)
            self.assertNotIn("person", synced)
            self.assertEqual(synced["collaboration"]["members"], ["Noomi", "Ada"])

    def test_reconcile_metadata_prunes_inactive_type_branch_with_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "Artists"
            metadata_path = root / "Noomi & Ada" / "cr4te.json"
            write_json(
                metadata_path,
                {
                    "type": "collaboration",
                    "person": {
                        "birth": {"date": "1990", "place": ""},
                    },
                },
            )

            self.reconcile_art_metadata(root)

            synced = read_json(metadata_path)
            self.assertNotIn("person", synced)
            self.assertIn("collaboration", synced)

    def test_reconcile_metadata_prunes_collaboration_branch_after_switching_to_person(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "Artists"
            metadata_path = root / "Noomi" / "cr4te.json"
            write_json(
                metadata_path,
                {
                    "type": "person",
                    "collaboration": {
                        "members": ["Noomi", "Ada"],
                        "founding": {"date": "2020", "place": "Paris"},
                    },
                },
            )

            self.reconcile_art_metadata(root)

            synced = read_json(metadata_path)
            self.assertNotIn("collaboration", synced)
            self.assertIn("person", synced)

    def test_reconcile_metadata_prunes_empty_stale_facets_but_keeps_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "Artists"
            project_dir = root / "Noomi" / "Landscapes"
            project_dir.mkdir(parents=True)
            project_metadata_path = project_dir / "cr4te.json"
            write_json(
                project_metadata_path,
                {
                    "facets": {
                        "actors": [],
                        "genres": ["Essay Film"],
                        "mediums": ["Photography"],
                    }
                },
            )

            self.reconcile_art_metadata(root)

            facets = read_json(project_metadata_path)["facets"]
            self.assertNotIn("actors", facets)
            self.assertEqual(facets["genres"], ["Essay Film"])
            self.assertEqual(facets["mediums"], ["Photography"])
            self.assertEqual(facets["materials"], [])

    def test_reconcile_metadata_moves_matching_nested_project_metadata_to_project_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "Artists"
            project_dir = root / "Noomi" / "New Name"
            project_dir.mkdir(parents=True)
            metadata_path = root / "Noomi" / "cr4te.json"
            write_json(
                metadata_path,
                {
                    "type": "person",
                    "person": {},
                    "projects": {
                        "New Name": {
                            "display_title": "Custom Project Title",
                            "release_date": "2024",
                            "tags": {"Mood": ["Quiet"]},
                            "facets": {"mediums": ["Photography"]},
                        }
                    },
                },
            )

            self.reconcile_art_metadata(root)

            metadata = read_json(metadata_path)
            self.assertNotIn("projects", metadata)
            project_metadata = read_json(project_dir / "cr4te.json")
            self.assertEqual(project_metadata["display_title"], "Custom Project Title")
            self.assertEqual(project_metadata["release_date"], "2024")
            self.assertEqual(project_metadata["tags"], {"Mood": ["Quiet"]})
            self.assertEqual(project_metadata["facets"]["mediums"], ["Photography"])

    def test_dry_run_reports_changes_without_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "Artists"
            (root / "Noomi").mkdir(parents=True)

            result = self.reconcile_art_metadata(root, dry_run=True)

            self.assertEqual(len(result.created), 1)
            self.assertFalse((root / "Noomi" / "cr4te.json").exists())

    def test_invalid_metadata_reconciliation_returns_structured_issue(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "Artists"
            metadata_path = root / "Noomi" / "cr4te.json"
            metadata_path.parent.mkdir(parents=True)
            metadata_path.write_text("{invalid", encoding="utf-8")

            result = self.reconcile_art_metadata(root)

            self.assertEqual(result.skipped, [metadata_path])
            self.assertEqual(len(result.issues), 1)
            self.assertEqual(result.issues[0].scope, IssueScope.CREATOR)
            self.assertEqual(result.issues[0].code, IssueCode.INVALID_JSON)
            self.assertEqual(
                result.summary_line(),
                "Metadata summary: created=0, updated=0, unchanged=0, skipped=1",
            )

    def test_delete_metadata_files_recurses_through_projects(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "Artists"
            creator_meta = root / "Noomi" / "cr4te.json"
            project_meta = root / "Noomi" / "Landscapes" / "cr4te.json"
            write_json(creator_meta, {})
            write_json(project_meta, {})

            delete_metadata_files(root, dry_run=True)
            self.assertTrue(creator_meta.exists())
            self.assertTrue(project_meta.exists())

            delete_metadata_files(root)
            self.assertFalse(creator_meta.exists())
            self.assertFalse(project_meta.exists())


if __name__ == "__main__":
    unittest.main()
