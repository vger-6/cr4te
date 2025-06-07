import json
import copy
import re
from enum import Enum
from pathlib import Path
from typing import Dict

from .enums.image_sample_strategy import ImageSampleStrategy
from .enums.media_type import MediaType

__all__ = ["load_config", "update_build_rules", "apply_cli_media_overrides", "compile_media_rules", "update_html_labels"]

# === Default internal config ===
DEFAULT_CONFIG = {
    "html_settings": {
        "nav_creators_label": "Creators",
        "nav_projects_label": "Projects",
        "nav_tags_label": "Tags",
        
        "creator_overview_page_title": "Creators",
        "creator_overview_page_search_placeholder": "Search creators, projects, tags...",
        
        "project_overview_page_title": "Projects",
        "project_overview_page_search_placeholder": "Search projects, tags...",
        
        "creator_page_profile_title": "Profile",
        "creator_page_about_title": "About",
        "creator_page_tags_title": "Tags",
        "creator_page_projects_title": "Projects",
        "creator_page_collabs_title_prefix": "Projects with",
        
        "collaboration_page_profile_title": "Profile",
        "collaboration_page_about_title": "About",
        "collaboration_page_tags_title": "Tags",
        "collaboration_page_members_title": "Members",
        "collaboration_page_projects_title": "Projects",
        
        "project_page_overview_title": "Overview",
        "project_page_description_title": "Description",
        "project_page_tags_title": "Tags",
        "project_page_creator_profile": "Creator Profile",
        "project_page_audio_section_base_title": "Tracks",
        "project_page_image_section_base_title": "Images",
        
        "tags_page_title": "Tags",
        
        "creator_page_visible_creator_fields": ["date_of_birth", "nationality", "aliases", "debut_age"],
        "collaboration_page_visible_collaboration_fields": ["name", "members", "founded", "nationality", "active_since"],
        "project_page_visible_project_fields": ["title", "release_date"],
        
        "project_page_image_pagination_limit" : 15,
        "project_page_show_image_captions": False,
        
        "project_page_type_order": [MediaType.VIDEO.value, MediaType.AUDIO.value, MediaType.IMAGE.value, MediaType.TEXT.value, MediaType.DOCUMENT.value]
    },
    "media_rules": {
        "global_exclude_re": r"^_",
        
        "video_include_re": r"(?i)^[^/\\]+\.(mp4|m4v)$",
        "audio_include_re": r"(?i)^[^/\\]+\.(mp3|m4a)$",
        "image_include_re": r"(?i)^[^/\\]+/[^/\\]+\.(jpg|jpeg|png)$",        
        "image_exclude_re": r"(?i)(^|.*/)cover\.(jpg|jpeg|png)$",
        "document_include_re": r"(?i)^[^/\\]+\.pdf$",
        "text_include_re": r"(?i)^[^/\\]+\.md$",
        "text_exclude_re": r"(?i)(^|.*/)readme\.md$",
        
        "portrait_re": r"^portrait\.(jpg|jpeg|png)$",
        "cover_re": r"^cover\.(jpg|jpeg|png)$",
        
        "image_gallery_max": 20,
        "image_gallery_sample_strategy": "spread",
        
        "collaboration_separator": " & "
    }
}

class HtmlPreset(str, Enum):
    ARTIST = "artist"
    MUSICIAN = "musician"
    DIRECTOR = "director"
    AUTHOR = "author"
    MODEL = "model"

class BuildMode(str, Enum):
    FLAT = "flat"
    HYBRID = "hybrid"
    DEEP = "deep"
    
def load_config(config_path: Path = None) -> Dict:
    config = copy.deepcopy(DEFAULT_CONFIG)

    if config_path:
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
            config["html_settings"].update(user_config.get("html_settings", {}))
            config["media_rules"].update(user_config.get("media_rules", {}))
            print(f"Loaded configuration from {config_path}")
        except Exception as e:
            print(f"Warning: Could not load config file {config_path}: {e}")
            print("Proceeding with default internal configuration.")

    return config
    
def update_html_labels(config: Dict, preset_str: str) -> Dict:
    preset = HtmlPreset(preset_str)
    overrides = _get_html_label_presets(preset) 
    config["html_settings"].update(overrides)
    return config
    
def _get_build_rules(mode: BuildMode) -> Dict:
    """
    Returns only the regex-related media_rules fields that are overridden
    by the selected build mode. Other configuration fields remain untouched.
    """
    match mode:
        case BuildMode.FLAT:
            return {
                "global_exclude_re": r"^_",
                "video_include_re": r"(?i)^[^/\\]+\.(mp4|m4v)$",
                "audio_include_re": r"(?i)^[^/\\]+\.(mp3|m4a)$",
                "image_include_re": r"(?i)^[^/\\]+\.(jpg|jpeg|png)$",
                "image_exclude_re": r"(?i)(^|.*/)cover\.(jpg|jpeg|png)$",
                "document_include_re": r"(?i)^[^/\\]+\.pdf$",
                "text_include_re": r"(?i)^[^/\\]+\.md$",
                "text_exclude_re": r"(?i)(^|.*/)readme\.md$",
            }
        case BuildMode.DEEP:
            return {
                "global_exclude_re": r"^_",
                "video_include_re": r"(?i).*\.(mp4|m4v)$",
                "audio_include_re": r"(?i).*\.(mp3|m4a)$",
                "image_include_re": r"(?i).*\.(jpg|jpeg|png)$",
                "image_exclude_re": r"(?i)(^|.*/)cover\.(jpg|jpeg|png)$",
                "document_include_re": r"(?i).*\.pdf$",
                "text_include_re": r"(?i).*\.md$",
                "text_exclude_re": r"(?i)(^|.*/)readme\.md$",
            }
        case BuildMode.HYBRID:
            return {}  # Use the base/default media_rules
        case _:
            raise ValueError(f"Unknown build mode: {mode}")

def update_build_rules(config: Dict, mode_str: str) -> Dict:
    """
    Given a mode string and an existing config dict, apply build-mode-specific
    regex overrides to the media_rules section and return the updated config.
    """
    mode = BuildMode(mode_str)
    overrides = _get_build_rules(mode)
    config["media_rules"].update(overrides)
    return config
    
def apply_cli_media_overrides(config: Dict, image_gallery_max: int = None, image_sample_strategy: str = None) -> Dict:
    """
    Applies CLI overrides for media_rules such as image_gallery_max and image_sample_strategy.
    """
    if image_gallery_max is not None :
        config["media_rules"]["image_gallery_max"] = image_gallery_max
    if image_sample_strategy:
        config["media_rules"]["image_gallery_sample_strategy"] = image_sample_strategy
    return config
    
def compile_media_rules(media_rules: Dict) -> Dict:
    """
    Compiles all known regex patterns in media_rules into regular expressions.
    Other values (e.g., integers) are preserved as-is.
    """
    regex_keys = {
        "global_exclude_re",
        "video_include_re",
        "audio_include_re",
        "image_include_re",
        "image_exclude_re",
        "document_include_re",
        "text_include_re",
        "text_exclude_re",
        "portrait_re", 
        "cover_re"
    }
    enum_keys = {"image_gallery_sample_strategy": ImageSampleStrategy}
    
    compiled = {}
    for key, val in media_rules.items():
        if key in regex_keys:
            compiled[key] = re.compile(val)
        elif key in enum_keys:
            compiled[key] = enum_keys[key](val)
        else:
            compiled[key] = val
    return compiled
    
def _get_html_label_presets(preset: HtmlPreset) -> Dict:
    """
    Returns only the labels that are overridden by the selected preset. 
    Other configuration fields remain untouched.
    """
    match preset:
        case HtmlPreset.DIRECTOR:
            return {
                "nav_creators_label": "Directors",
                "nav_projects_label": "Movies",
                "creator_overview_page_title": "Directors",
                "creator_overview_page_search_placeholder": "Search directors, movies, tags...",
                "project_overview_page_title": "Movies",
                "project_overview_page_search_placeholder": "Search movies, tags...",
                "creator_page_projects_title": "Movies",
                "project_page_audio_section_base_title": "Soundtrack",
                "creator_page_collabs_title_prefix": "Codirected with",
                "collaboration_page_projects_title": "Movies",
                "project_page_creator_profile": "Profile",
            }
        case HtmlPreset.MUSICIAN:
            return {
                "nav_creators_label": "Musicians",
                "nav_projects_label": "Albums",
                "creator_overview_page_title": "Musicians",
                "creator_overview_page_search_placeholder": "Search musicians, albums, tags...",
                "project_overview_page_title": "Albums",
                "project_overview_page_search_placeholder": "Search albums, tags...",
                "creator_page_projects_title": "Albums",
                "creator_page_collabs_title_prefix": "With",
                "collaboration_page_projects_title": "Albums",
                "project_page_creator_profile": "Profile",
            }
        case HtmlPreset.ARTIST:
            return {
                "nav_creators_label": "Artists",
                "nav_projects_label": "Works",
                "creator_overview_page_title": "Artists",
                "creator_overview_page_search_placeholder": "Search artists, works, tags...",
                "project_overview_page_title": "Works",
                "project_overview_page_search_placeholder": "Search works, tags...",
                "creator_page_projects_title": "Works",
                "project_page_audio_section_base_title": "Audio",
                "creator_page_collabs_title_prefix": "With",
                "collaboration_page_projects_title": "Works",
                "project_page_creator_profile": "Profile"
            }
        case HtmlPreset.AUTHOR:
            return {
                "nav_creators_label": "Author",
                "nav_projects_label": "Books",
                "creator_overview_page_title": "Author",
                "creator_overview_page_search_placeholder": "Search author, books, tags...",
                "project_overview_page_title": "Books",
                "project_overview_page_search_placeholder": "Search books, tags...",
                "creator_page_projects_title": "Books",
                "project_page_audio_section_base_title": "Audio",
                "creator_page_collabs_title_prefix": "With",
                "collaboration_page_projects_title": "Books",
                "project_page_creator_profile": "Profile"
            }
        case HtmlPreset.MODEL:
            return {
                "nav_creators_label": "Models",
                "nav_projects_label": "Scenes",
                "creator_overview_page_title": "Models",
                "creator_overview_page_search_placeholder": "Search models, scenes, tags...",
                "project_overview_page_title": "Scenes",
                "project_overview_page_search_placeholder": "Search scenes, tags...",
                "creator_page_projects_title": "Scenes",
                "creator_page_collabs_title_prefix": "Scenes with",
                "collaboration_page_members_title": "Featuring",
                "collaboration_page_projects_title": "Scenes",
                "project_page_creator_profile": "Model Profile"
            }
        case _:
            raise ValueError(f"Unknown preset: {preset}")

