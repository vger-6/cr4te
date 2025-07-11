import re
import os
import platform
import json
import hashlib
from pathlib import Path
from typing import Dict
from PIL import Image, ImageDraw, ImageFont

def slugify(text: str) -> str:
    if not isinstance(text, str):
        raise ValueError("slugify expects a string")

    return re.sub(r'[^\w]+', '_', text.lower()).strip('_')  # \w includes a-zA-Z0-9_
    
def relative_path_from(file_path: Path, base_path: Path) -> Path: 
    file_path = file_path.resolve()
    base_path = base_path.resolve()

    return Path(os.path.relpath(file_path, base_path))
    
def read_text(text_path: Path) -> str:
    if text_path.exists() and text_path.is_file():
        return text_path.read_text(encoding='utf-8').strip()
    return ""

def load_json(json_path: Path) -> Dict:
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)
        
def build_unique_path(input_path: Path, depth: int = 4) -> Path:
    """
    Build a unique path based on a SHA-1 hash of the input path.

    Parameters:
        input_path (Path): The original relative path.
        depth (int): Number of directory levels (each 2 characters). Must be 1–20.

    Returns:
        Path: A unique, nested path ending with the hashed filename + original suffix.
    """
    if not (1 <= depth <= 20):
        raise ValueError("depth must be between 1 and 20 (inclusive)")

    original_suffix = input_path.suffix
    sha1 = hashlib.sha1(str(input_path).encode("utf-8")).hexdigest()

    chunks = [sha1[i * 2: i * 2 + 2] for i in range(depth)]
    remaining = sha1[depth * 2:] + original_suffix
    chunks.append(remaining)

    return Path(*chunks)
    
def get_path_to_root(depth: int) -> str:
    """
    Returns a relative path that navigates up `depth` directories.

    Parameters:
        depth (int): Number of directory levels to go up.

    Returns:
        str: Relative path to root, like "../../.."
    """
    if depth < 0:
        raise ValueError("depth must be non-negative")
    return "../" * depth
    
def tag_path(input_path: Path, tag: str) -> Path:
    return input_path.with_name(f"{input_path.stem}_{tag}{input_path.suffix}")

def create_centered_text_image(width: int, height: int, text: str, output_path: Path)->None:
    # Create an image with grey background
    image = Image.new("RGB", (width, height), color="grey")
    draw = ImageDraw.Draw(image)
    
    system = platform.system()
    font_path = None
    if system == "Windows":
        font_path = "arial.ttf"
    elif system == "Linux":
        font_path = "DejaVuSans.ttf"

    # Load default or fallback font
    try:
        font = ImageFont.truetype(font_path, size=int(height*0.1))  # Adjustable font size
    except IOError:
        font = ImageFont.load_default()

    # Get bounding box of the text
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    # Calculate position to center the text
    text_x = (width - text_width) / 2
    text_y = (height - text_height) / 2

    # Draw text
    draw.text((text_x, text_y), text, font=font, fill="white")

    # Save the image
    image.save(output_path, format="PNG")

