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
    
def get_relative_path(file_path: Path, base_path: Path) -> str:
    if not isinstance(file_path, Path) or not isinstance(base_path, Path):
        raise TypeError("Both file_path and base_path must be pathlib.Path objects")

    return Path(os.path.relpath(file_path, base_path)).as_posix()
    
def read_text(text_path: Path) -> str:
    if text_path.exists() and text_path.is_file():
        return text_path.read_text(encoding='utf-8').strip()
    return ""

def load_json(json_path: Path) -> Dict:
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)
        
#def build_unique_path(target_dir: Path, relative_path: Path) -> Path:
#    def short_hash(path: str, length: int = 8) -> str:
#        return hashlib.sha1(path.encode('utf-8')).hexdigest()[:length]
#
#    # Slugify directory parts
#    slugified_parts = [slugify(part) for part in relative_path.parent.parts]
#    
#    # Slugify filename and extension
#    basename = slugify(relative_path.stem)
#    extension = relative_path.suffix.lower()  # Includes the dot (e.g., ".jpg")
#
#    # Generate short hash
#    hash_suffix = short_hash(str(relative_path))
#
#    final_name = f"{basename}_{hash_suffix}{extension}"
#
#    return target_dir.joinpath(*slugified_parts, final_name)
        
def build_unique_path(relative_path: Path) -> Path:
    original_suffix = relative_path.suffix
    sha1 = hashlib.sha1(str(relative_path).encode("utf-8")).hexdigest()

    chunks = [
        sha1[0:2],
        sha1[2:4],
        sha1[4:6],
        sha1[6:8],
        sha1[8:] + original_suffix
    ]

    return Path(*chunks)
    
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

