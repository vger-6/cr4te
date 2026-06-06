import platform
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from ..enums.orientation import Orientation
from ..media_cache import ImageDimensions

__all__ = [
    "create_centered_text_image",
    "generate_thumbnail",
    "infer_image_orientation",
    "read_image_dimensions",
]


def read_image_dimensions(image_path: Path) -> ImageDimensions:
    with Image.open(image_path) as img:
        return ImageDimensions(width=img.width, height=img.height)


def infer_image_orientation(image_path: Path) -> Orientation:
    try:
        return read_image_dimensions(image_path).orientation
    except Exception:
        return Orientation.LANDSCAPE


def generate_thumbnail(source_path: Path, target_height: int) -> Image:
    with Image.open(source_path) as img:
        aspect_ratio = img.width / img.height
        target_width = int(target_height * aspect_ratio)
        return img.resize((target_width, target_height), Image.LANCZOS)


def create_centered_text_image(width: int, height: int, text: str, output_path: Path) -> None:
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
        font = ImageFont.truetype(font_path, size=int(height * 0.1))  # Adjustable font size
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

