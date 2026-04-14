from dataclasses import dataclass
from pathlib import Path

@dataclass
class BaseContext:
    input_dir: Path
