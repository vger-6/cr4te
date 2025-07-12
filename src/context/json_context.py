from dataclasses import dataclass
from typing import Dict, List

from context.base_context import BaseContext

README_FILE_NAME = "README.md"

@dataclass
class JsonBuildContext(BaseContext):
    media_rules: Dict

    @property
    def readme_file_name(self) -> str:
        return README_FILE_NAME

    @property
    def global_exclude_prefix(self) -> str:
        return self.media_rules["global_exclude_prefix"]
        
    @property
    def max_search_depth(self) -> int:
        return self.media_rules["max_search_depth"]
        
    @property
    def cover_basename(self) -> str:
        return self.media_rules["cover_basename"]
        
    @property
    def portrait_basename(self) -> str:
        return self.media_rules["portrait_basename"]
        
    @property
    def auto_find_portrait(self) -> bool:
        return self.media_rules["auto_find_portraits"]
        
    @property
    def metadata_folder_name(self) -> str:
        return self.media_rules["metadata_folder_name"]
        
    @property
    def collaboration_separators(self) -> List[str]:
        return self.media_rules["collaboration_separators"]

