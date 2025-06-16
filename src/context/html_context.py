from dataclasses import dataclass
from pathlib import Path
from typing import Dict
from enum import Enum

from enums.thumb_type import ThumbType
from context.base_context import BaseContext
from constants import (
    SCRIPT_DIR,
    CR4TE_DEFAULTS_DIR,
    CR4TE_CSS_DIR, 
    CR4TE_JS_DIR,
)

# === Output folder names ===
CREATORS_DIRNAME = "creators"
PROJECTS_DIRNAME = "projects"
THUMBNAILS_DIRNAME = "thumbnails"

@dataclass
class HtmlBuildContext(BaseContext):
    output_dir: Path
    html_settings: Dict
    
    @property
    def defaults_dir(self) -> Path:
        return self.output_dir / CR4TE_DEFAULTS_DIR.relative_to(SCRIPT_DIR)
    
    @property
    def css_dir(self) -> Path:
        return self.output_dir / CR4TE_CSS_DIR.relative_to(SCRIPT_DIR)
        
    @property
    def js_dir(self) -> Path:
        return self.output_dir / CR4TE_JS_DIR.relative_to(SCRIPT_DIR)
    
    @property
    def thumbs_dir(self) -> Path:
        return self.output_dir / THUMBNAILS_DIRNAME

    @property
    def creators_dir(self) -> Path:
        return self.output_dir / CREATORS_DIRNAME

    @property
    def projects_dir(self) -> Path:
        return self.output_dir / PROJECTS_DIRNAME

    @property
    def media_dir(self) -> Path:
        return self.output_dir / "media"

    @property
    def images_dir(self) -> Path:
        return self.media_dir / "images"

    @property
    def videos_dir(self) -> Path:
        return self.media_dir / "videos"

    @property
    def tracks_dir(self) -> Path:
        return self.media_dir / "tracks"

    @property
    def documents_dir(self) -> Path:
        return self.media_dir / "documents"

    @property
    def index_html_path(self) -> Path:
        return self.output_dir / "index.html"

    @property
    def projects_html_path(self) -> Path:
        return self.output_dir / "projects.html"

    @property
    def tags_html_path(self) -> Path:
        return self.output_dir / "tags.html"

    def thumb_default(self, thumb_type: ThumbType) -> Path:
        return self.defaults_dir / {
            ThumbType.THUMB: "thumb.png",
            ThumbType.PORTRAIT: "portrait.png",
            ThumbType.COVER: "cover.png",
            ThumbType.GALLERY: "thumb.png",
        }[thumb_type]
        
    def thumb_height(self, thumb_type: ThumbType) -> int:
        return {
            ThumbType.THUMB: 300,
            ThumbType.PORTRAIT: 450,
            ThumbType.COVER: 600,
            ThumbType.GALLERY: 450,
        }[thumb_type]

