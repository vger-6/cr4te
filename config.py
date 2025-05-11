import json
import copy
import re
from enum import Enum
from pathlib import Path
from typing import Dict

from enums.image_sample_strategy import ImageSampleStrategy

# === Default internal config ===
DEFAULT_CONFIG = {
    "html_settings": {
        "nav_creators_label": "Creators",
        "nav_projects_label": "Projects",
        "nav_tags_label": "Tags",
        
        "overview_page_title": "Creators",
        "overview_page_search_placeholder": "Search creators, projects, tags...",
        
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
        "project_page_videos_label": "Videos",
        "project_page_audio_label": "Audio",
        "project_page_images_label": "Images",
        "project_page_documents_label": "Documents",
        
        "tags_page_title": "Tags",
        
        "visible_creator_fields": ["date_of_birth", "nationality", "aliases", "debut_age"],
        "visible_project_fields": ["title", "release_date"],
        
        "project_info_layout": "column"
    },
    "media_rules": {
        "GLOBAL_EXCLUDE_RE": r"^_",
        
        "VIDEO_INCLUDE_RE": r"^[^/\\]+\.mp4$",
        "VIDEO_EXCLUDE_RE": r"$^",
        
        "AUDIO_INCLUDE_RE": r"^[^/\\]+\.m4a$",
        "AUDIO_EXCLUDE_RE": r"$^",
        
        "IMAGE_INCLUDE_RE": r"^[^/\\]+/[^/\\]+\.jpg$",
        "IMAGE_EXCLUDE_RE": r"$^",
        
        "DOCUMENT_INCLUDE_RE": r"^[^/\\]+\.pdf$",
        "DOCUMENT_EXCLUDE_RE": r"$^",
        
        "PORTRAIT_RE": r"^profile\.jpg$",
        "POSTER_RE": r"^cover\.jpg$",
        
        "MAX_IMAGES": 20,
        "IMAGE_SAMPLE_STRATEGY": "spread",
        
        "COLLABORATION_SEPARATOR": " & "
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
    
def get_html_label_presets(preset: HtmlPreset) -> Dict:
    """
    Returns only the labels that are overridden by the selected preset. 
    Other configuration fields remain untouched.
    """
    match preset:
        case HtmlPreset.DIRECTOR:
            return {
                "nav_creators_label": "Directors",
                "nav_projects_label": "Movies",
                "overview_page_title": "Directors",
                "overview_page_search_placeholder": "Search directors, movies, tags...",
                "project_overview_page_title": "Movies",
                "project_overview_page_search_placeholder": "Search movies, tags...",
                "creator_page_projects_title": "Movies",
                "creator_page_collabs_title_prefix": "Codirected with",
                "collaboration_page_projects_title": "Movies",
                "project_page_creator_profile": "Profile",
                "project_page_videos_label": "Movie"
            }
        case HtmlPreset.MUSICIAN:
            return {
                "nav_creators_label": "Musicians",
                "nav_projects_label": "Albums",
                "overview_page_title": "Musicians",
                "overview_page_search_placeholder": "Search musicians, albums, tags...",
                "project_overview_page_title": "Albums",
                "project_overview_page_search_placeholder": "Search albums, tags...",
                "creator_page_projects_title": "Albums",
                "creator_page_collabs_title_prefix": "With",
                "collaboration_page_projects_title": "Albums",
                "project_page_audio_label": "Tracks",
                "project_page_creator_profile": "Profile",
            }
        case HtmlPreset.ARTIST:
            return {
                "nav_creators_label": "Artists",
                "nav_projects_label": "Works",
                "overview_page_title": "Artists",
                "overview_page_search_placeholder": "Search artists, works, tags...",
                "project_overview_page_title": "Works",
                "project_overview_page_search_placeholder": "Search works, tags...",
                "creator_page_projects_title": "Works",
                "creator_page_collabs_title_prefix": "With",
                "collaboration_page_projects_title": "Works",
                "project_page_creator_profile": "Profile"
            }
        case HtmlPreset.AUTHOR:
            return {
                "nav_creators_label": "Author",
                "nav_projects_label": "Books",
                "overview_page_title": "Author",
                "overview_page_search_placeholder": "Search author, books, tags...",
                "project_overview_page_title": "Books",
                "project_overview_page_search_placeholder": "Search books, tags...",
                "creator_page_projects_title": "Books",
                "creator_page_collabs_title_prefix": "With",
                "collaboration_page_projects_title": "Books",
                "project_page_creator_profile": "Profile"
            }
        case HtmlPreset.MODEL:
            return {
                "nav_creators_label": "Models",
                "nav_projects_label": "Scenes",
                "overview_page_title": "Models",
                "overview_page_search_placeholder": "Search models, scenes, tags...",
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

def get_build_rules(mode: BuildMode) -> Dict:
    """
    Returns only the regex-related media_rules fields that are overridden
    by the selected build mode. Other configuration fields remain untouched.
    """
    match mode:
        case BuildMode.FLAT:
            return {
                "GLOBAL_EXCLUDE_RE": r"^_",
                "VIDEO_INCLUDE_RE": r"^[^/\\]+\.mp4$",
                "VIDEO_EXCLUDE_RE": r"$^",
                "AUDIO_INCLUDE_RE": r"^[^/\\]+\.m4a$",
                "AUDIO_EXCLUDE_RE": r"$^",
                "IMAGE_INCLUDE_RE": r"^[^/\\]+\.jpg$",
                "IMAGE_EXCLUDE_RE": r"$^",
                "DOCUMENT_INCLUDE_RE": r"^[^/\\]+\.pdf$",
                "DOCUMENT_EXCLUDE_RE": r"$^"
            }
        case BuildMode.DEEP:
            return {
                "GLOBAL_EXCLUDE_RE": r"^_",
                "VIDEO_INCLUDE_RE": r".*\.mp4$",
                "VIDEO_EXCLUDE_RE": r"$^",
                "AUDIO_INCLUDE_RE": r".*\.m4a$",
                "AUDIO_EXCLUDE_RE": r"$^",
                "IMAGE_INCLUDE_RE": r".*\.jpg$",
                "IMAGE_EXCLUDE_RE": r"$^",
                "DOCUMENT_INCLUDE_RE": r".*\.pdf$",
                "DOCUMENT_EXCLUDE_RE": r"$^"
            }
        case BuildMode.HYBRID:
            return {}  # Use the base/default media_rules
        case _:
            raise ValueError(f"Unknown build mode: {mode}")

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
    overrides = get_html_label_presets(preset) 
    config["html_settings"].update(overrides)
    return config

def update_build_rules(config: Dict, mode_str: str) -> Dict:
    """
    Given a mode string and an existing config dict, apply build-mode-specific
    regex overrides to the media_rules section and return the updated config.
    """
    mode = BuildMode(mode_str)
    overrides = get_build_rules(mode)
    config["media_rules"].update(overrides)
    return config
    
def apply_cli_media_overrides(config: Dict, max_images: int = None, image_strategy: str = None) -> Dict:
    """
    Applies CLI overrides for media_rules such as max_images and image_sample_strategy.
    """
    if max_images is not None :
        config["media_rules"]["MAX_IMAGES"] = max_images
    if image_strategy:
        config["media_rules"]["IMAGE_SAMPLE_STRATEGY"] = image_strategy
    return config
    
def compile_media_rules(media_rules: Dict) -> Dict:
    """
    Compiles all known regex patterns in media_rules into regular expressions.
    Other values (e.g., integers) are preserved as-is.
    """
    regex_keys = {
        "GLOBAL_EXCLUDE_RE", 
        "VIDEO_INCLUDE_RE", "VIDEO_EXCLUDE_RE", 
        "AUDIO_INCLUDE_RE", "AUDIO_EXCLUDE_RE",
        "IMAGE_INCLUDE_RE", "IMAGE_EXCLUDE_RE", 
        "DOCUMENT_INCLUDE_RE", "DOCUMENT_EXCLUDE_RE",
        "PORTRAIT_RE", "POSTER_RE"
    }
    enum_keys = {"IMAGE_SAMPLE_STRATEGY": ImageSampleStrategy}
    
    compiled = {}
    for key, val in media_rules.items():
        if key in regex_keys:
            compiled[key] = re.compile(val)
        elif key in enum_keys:
            compiled[key] = enum_keys[key](val)
        else:
            compiled[key] = val
    return compiled

