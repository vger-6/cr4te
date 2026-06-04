import sys
import unittest
from pathlib import Path

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
            name="Noomi",
            type=CreatorType.PERSON,
            portrait="portrait.jpg",
        )

        data = template.as_json()

        self.assertEqual(data["type"], "person")
        self.assertEqual(data["portrait"], "portrait.jpg")
        self.assertIn("person", data)
        self.assertNotIn("collaboration", data)
        self.assertNotIn("projects", data)
        CreatorMetadata(**data)

    def test_creator_template_serializes_only_active_collaboration_branch(self):
        template = CreatorMetadataTemplate(
            name="Noomi & Ada",
            type=CreatorType.COLLABORATION,
            collaboration=CollaborationMetadataTemplate(members=["Noomi", "Ada"]),
        )

        data = template.as_json()

        self.assertEqual(data["type"], "collaboration")
        self.assertEqual(data["collaboration"]["members"], ["Noomi", "Ada"])
        self.assertNotIn("person", data)
        CreatorMetadata(**data)

    def test_project_template_serializes_facet_enum_keys_as_json_keys(self):
        template = ProjectMetadataTemplate(
            title="Landscapes",
            cover="cover.jpg",
            facet_fields=(ProjectField.MEDIUMS, ProjectField.MATERIALS),
        )

        data = template.as_json()

        self.assertEqual(data["cover"], "cover.jpg")
        self.assertEqual(data["facets"], {"mediums": [], "materials": []})
        ProjectMetadata(**data)

    def test_metadata_templates_match_metadata_file_schema(self):
        person = CreatorMetadataTemplate(name="Noomi", type=CreatorType.PERSON).as_json()
        collaboration = CreatorMetadataTemplate(
            name="Noomi & Ada",
            type=CreatorType.COLLABORATION,
            collaboration=CollaborationMetadataTemplate(members=["Noomi", "Ada"]),
        ).as_json()
        project = ProjectMetadataTemplate(
            title="Landscapes",
            facet_fields=(ProjectField.MEDIUMS, ProjectField.MATERIALS),
        ).as_json()

        self.assertIsInstance(CreatorMetadata(**person), CreatorMetadata)
        self.assertIsInstance(CreatorMetadata(**collaboration), CreatorMetadata)
        self.assertIsInstance(ProjectMetadata(**project), ProjectMetadata)


if __name__ == "__main__":
    unittest.main()
