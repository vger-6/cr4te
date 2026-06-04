import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pydantic import ValidationError

from cr4te.library_metadata import (
    MetadataReferenceError,
    MetadataShapeError,
    MetadataValidationError,
    load_json_model,
    metadata_relative_path,
    normalize_metadata_date,
)
from cr4te.schemas.library_schema import Project
from cr4te.schemas.metadata_file_schema import ProjectMetadata
from cr4te.utils.date_utils import format_nice_date, normalize_optional_iso_date


class LibraryMetadataTests(unittest.TestCase):
    def test_normalize_metadata_date_accepts_supported_precision(self):
        self.assertEqual(normalize_metadata_date("2024", "release_date", "Album"), "2024")
        self.assertEqual(normalize_metadata_date("2024-03", "release_date", "Album"), "2024-03")
        self.assertEqual(normalize_metadata_date("2024-03-12", "release_date", "Album"), "2024-03-12")
        self.assertEqual(normalize_metadata_date("", "release_date", "Album"), "")
        self.assertEqual(normalize_metadata_date(None, "release_date", "Album"), "")

    def test_shared_date_validator_accepts_valid_dates_only(self):
        self.assertEqual(normalize_optional_iso_date(" 2024-03 "), "2024-03")

        for invalid_date in ("2024-02-31", "2024-99", "2024-3", "12.03.2024"):
            with self.subTest(invalid_date=invalid_date):
                with self.assertRaises(ValueError):
                    normalize_optional_iso_date(invalid_date)

    def test_date_display_preserves_stored_precision(self):
        self.assertEqual(format_nice_date("2024"), "2024")
        self.assertEqual(format_nice_date("2024-03"), "March 2024")
        self.assertEqual(format_nice_date("2024-03-12"), "March 12, 2024")

    def test_normalize_metadata_date_wraps_invalid_value(self):
        with self.assertRaises(MetadataValidationError) as ctx:
            normalize_metadata_date("12.03.2024", "release_date", "Album")

        self.assertIn("Album: invalid release_date", str(ctx.exception))

    def test_metadata_file_schema_rejects_calendar_invalid_date(self):
        with self.assertRaises(ValidationError):
            ProjectMetadata(release_date="2024-02-31")

        with self.assertRaises(ValidationError):
            ProjectMetadata(release_date="2024-99")

    def test_runtime_schema_rejects_calendar_invalid_date(self):
        base_project = {
            "title": "Album",
            "cover": "",
            "info": "",
            "media_groups": [],
        }

        with self.assertRaises(ValidationError):
            Project(**base_project, release_date="2024-02-31")

        with self.assertRaises(ValidationError):
            Project(**base_project, release_date="2024-99")

    def test_metadata_relative_path_requires_existing_file_inside_input_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp) / "Artists"
            project_dir = input_dir / "Ada" / "Project"
            cover_path = project_dir / "cover.jpg"
            cover_path.parent.mkdir(parents=True)
            cover_path.write_bytes(b"image")

            self.assertEqual(
                metadata_relative_path(project_dir, "cover.jpg", input_dir, "cover"),
                "Ada/Project/cover.jpg",
            )

            outside_path = Path("..") / ".." / ".." / "outside.jpg"
            with self.assertRaises(MetadataReferenceError):
                metadata_relative_path(project_dir, str(outside_path), input_dir, "cover")

    def test_load_json_model_rejects_non_object_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            metadata_path = Path(tmp) / "cr4te.json"
            metadata_path.write_text("[]", encoding="utf-8")

            with self.assertRaises(MetadataShapeError):
                load_json_model(metadata_path, ProjectMetadata)


if __name__ == "__main__":
    unittest.main()
