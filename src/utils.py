import re
import os
import platform
import json
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

