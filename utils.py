import re
import os
from pathlib import Path

def is_collaboration(name: str) -> bool:
    return ' & ' in name
    
def slugify(text: str) -> str:
    return re.sub(r'[^a-zA-Z0-9]+', '_', text.lower()).strip('_')
    
def get_relative_path(file_path: Path, base_path: Path) -> str:
    return Path(os.path.relpath(file_path, base_path)).as_posix()
    
def is_valid_entry(entry: Path) -> bool:
    return not entry.name.startswith('_')
    