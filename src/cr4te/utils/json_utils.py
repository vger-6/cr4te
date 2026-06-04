import json
from pathlib import Path
from typing import Dict

__all__ = ["load_json"]

def load_json(json_path: Path) -> Dict:
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)
