import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cr4te.creator_classification import infer_creator_type
from cr4te.enums.creator_type import CreatorType


class CreatorClassificationTests(unittest.TestCase):
    def test_infer_creator_type_uses_configured_collaboration_separators(self):
        separators = (" & ", " x ")

        self.assertEqual(infer_creator_type("Noomi & Ada", separators), CreatorType.COLLABORATION)
        self.assertEqual(infer_creator_type("Noomi x Ada", separators), CreatorType.COLLABORATION)
        self.assertEqual(infer_creator_type("Noomi Ada", separators), CreatorType.PERSON)


if __name__ == "__main__":
    unittest.main()
