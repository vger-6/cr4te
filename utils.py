import re
import os
from pathlib import Path
    
def slugify(text: str) -> str:
    if not isinstance(text, str):
        raise ValueError("slugify expects a string")
        
    return re.sub(r'[^a-zA-Z0-9]+', '_', text.lower()).strip('_')
    
def get_relative_path(file_path: Path, base_path: Path) -> str:
    if not isinstance(file_path, Path) or not isinstance(base_path, Path):
        raise TypeError("Both file_path and base_path must be pathlib.Path objects")

    return Path(os.path.relpath(file_path, base_path)).as_posix()    
