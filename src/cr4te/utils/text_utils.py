import re
import markdown
from pathlib import Path
from typing import List

__all__ = ["markdown_to_html", "read_text", "slugify", "multi_split"]

def markdown_to_html(text: str) -> str:
    return markdown.markdown(text, extensions=["nl2br", "tables"])
    
def read_text(text_path: Path) -> str:
    if text_path.exists() and text_path.is_file():
        return text_path.read_text(encoding='utf-8').strip()
    return ""
    
def slugify(text: str) -> str:
    if not isinstance(text, str):
        raise ValueError("slugify expects a string")

    return re.sub(r'[^\w]+', '_', text.lower()).strip('_')  # \w includes a-zA-Z0-9_
    
def multi_split(text: str, separators: List[str]) -> List[str]:
    """
    Splits the input text using any of the provided multi-character separators.
    """
    if not separators:
        return [text]  # fallback: no split
    pattern = "|".join(re.escape(sep) for sep in separators)
    return [part.strip() for part in re.split(pattern, text) if part]
