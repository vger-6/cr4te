import json
import copy
from enum import Enum
from pathlib import Path
from typing import Dict, Optional

from enums.image_sample_strategy import ImageSampleStrategy
from enums.media_type import MediaType

__all__ = ["load_config", "apply_cli_media_overrides", "update_html_labels"]

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
        
        "type_order": [MediaType.VIDEO.value, MediaType.AUDIO.value, MediaType.IMAGE.value, MediaType.TEXT.value, MediaType.DOCUMENT.value],
    },
    "media_rules": {   
        "image_gallery_max": 20,
        "image_gallery_sample_strategy": ImageSampleStrategy.SPREAD.value,
        
        "max_depth": 2,
        
        "global_exclude_prefix": "_",
        
        "metadata_folder_name": "meta",
        "collaboration_separator": " & ",
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
       
def apply_cli_media_overrides(config: Dict, image_gallery_max: Optional[int] = None, image_sample_strategy: Optional[ImageSampleStrategy] = None) -> Dict:
    """
    Applies CLI overrides for media_rules such as image_gallery_max and image_sample_strategy.
    """
    if image_gallery_max is not None:
        config["media_rules"]["image_gallery_max"] = image_gallery_max
    if image_sample_strategy is not None:
        config["media_rules"]["image_gallery_sample_strategy"] = image_sample_strategy.value
    return config
 
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

