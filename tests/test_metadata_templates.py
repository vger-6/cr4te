import sys
import unittest
from pathlib import Path

from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cr4te.enums.creator_type import CreatorType
from cr4te.enums.visible_fields import ProjectField
from cr4te.metadata_templates import (
    CollaborationMetadataTemplate,
    CreatorMetadataTemplate,
    ProjectMetadataTemplate,
)
from cr4te.schemas.metadata_file_schema import CreatorMetadata, ProjectMetadata


class MetadataTemplateTests(unittest.TestCase):
    def test_creator_template_serializes_only_active_person_branch(self):
        template = CreatorMetadataTemplate(
            display_name="Noomi",
            type=CreatorType.PERSON,
        )

        data = template.as_json()

        self.assertEqual(data["type"], "person")
        self.assertEqual(data["display_name"], "Noomi")
        self.assertNotIn("portrait", data)
        self.assertIn("person", data)
        self.assertNotIn("collaboration", data)
        self.assertNotIn("name", data)
        self.assertNotIn("projects", data)
        CreatorMetadata(**data)

    def test_creator_template_serializes_only_active_collaboration_branch(self):
        template = CreatorMetadataTemplate(
            display_name="Noomi & Ada",
            type=CreatorType.COLLABORATION,
            collaboration=CollaborationMetadataTemplate(members=["Noomi", "Ada"]),
        )

        data = template.as_json()

        self.assertEqual(data["type"], "collaboration")
        self.assertEqual(data["display_name"], "Noomi & Ada")
        self.assertEqual(data["collaboration"]["members"], ["Noomi", "Ada"])
        self.assertNotIn("name", data)
        self.assertNotIn("person", data)
        CreatorMetadata(**data)

    def test_project_template_serializes_facet_enum_keys_as_json_keys(self):
        template = ProjectMetadataTemplate(
            display_title="Landscapes",
            facet_fields=(ProjectField.MEDIUMS, ProjectField.MATERIALS),
        )

        data = template.as_json()

        self.assertNotIn("cover", data)
        self.assertEqual(data["display_title"], "Landscapes")
        self.assertEqual(data["facets"], {"mediums": [], "materials": []})
        self.assertNotIn("title", data)
        ProjectMetadata(**data)

    def test_metadata_templates_match_metadata_file_schema(self):
        person = CreatorMetadataTemplate(display_name="Noomi", type=CreatorType.PERSON).as_json()
        collaboration = CreatorMetadataTemplate(
            display_name="Noomi & Ada",
            type=CreatorType.COLLABORATION,
            collaboration=CollaborationMetadataTemplate(members=["Noomi", "Ada"]),
        ).as_json()
        project = ProjectMetadataTemplate(
            display_title="Landscapes",
            facet_fields=(ProjectField.MEDIUMS, ProjectField.MATERIALS),
        ).as_json()

        self.assertIsInstance(CreatorMetadata(**person), CreatorMetadata)
        self.assertIsInstance(CreatorMetadata(**collaboration), CreatorMetadata)
        self.assertIsInstance(ProjectMetadata(**project), ProjectMetadata)

    def test_metadata_schemas_reject_portrait_and_cover_paths(self):
        with self.assertRaises(ValidationError):
            CreatorMetadata(portrait="portrait.jpg")

        with self.assertRaises(ValidationError):
            ProjectMetadata(cover="cover.jpg")


if __name__ == "__main__":
    unittest.main()
