from dataclasses import dataclass
from pathlib import Path
from typing import Dict

from context.base_context import BaseContext

README_FILENAME = "README.md"

@dataclass
class JsonBuildContext(BaseContext):
    media_rules: Dict

    @property
    def readme_filename(self) -> str:
        return README_FILENAME

    @property
    def global_exclude_prefix(self) -> str:
        return self.media_rules["global_exclude_prefix"]
        
    @property
    def max_depth(self) -> str:
        return self.media_rules["max_depth"]
        
    @property
    def cover_basename(self) -> str:
        return self.media_rules["cover_basename"]
        
    @property
    def portrait_basename(self) -> str:
        return self.media_rules["portrait_basename"]
        
    @property
    def metadata_folder_name(self) -> str:
        return self.media_rules["metadata_folder_name"]
        
    @property
    def collaboration_separators(self) -> str:
        return self.media_rules["collaboration_separators"]

