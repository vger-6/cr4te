from dataclasses import dataclass
from pathlib import Path
from typing import Dict

from context.base_context import BaseContext

@dataclass
class JsonBuildContext(BaseContext):
    media_rules: Dict

    @property
    def readme_filename(self) -> str:
        return "README.md"

    #@property
    #def metadata_folder_name(self) -> str:
    #    return self.media_rules["metadata_folder_name"]

