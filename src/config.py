import json
import copy
from enum import Enum
from pathlib import Path
from typing import Dict, Optional

from pydantic import ValidationError

import utils
from validators.config_schema import AppConfig
from enums.visible_fields import CreatorField, CollaborationField, ProjectField
from enums.image_sample_strategy import ImageSampleStrategy
from enums.media_type import MediaType
from enums.label_preset import LabelPreset

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
        
        "creator_page_visible_creator_fields": [CreatorField.DATE_OF_BIRTH, CreatorField.NATIONALITY, CreatorField.ALIASES, CreatorField.DEBUT_AGE],
        "collaboration_page_visible_collaboration_fields": [CollaborationField.NAME, CollaborationField.MEMBERS, CollaborationField.FOUNDED, CollaborationField.NATIONALITY, CollaborationField.ACTIVE_SINCE],
        "project_page_visible_project_fields": [ProjectField.TITLE, ProjectField.RELEASE_DATE],
        
        "project_page_image_pagination_limit" : 15,
        "project_page_show_image_captions": False,
        
        "image_gallery_max": 20,
        "image_gallery_sample_strategy": ImageSampleStrategy.SPREAD,
        
        "type_order": [MediaType.VIDEO, MediaType.AUDIO, MediaType.IMAGE, MediaType.TEXT, MediaType.DOCUMENT],
    },
    "media_rules": {   
        "max_depth": 2,
        
        "global_exclude_prefix": "_",
        
        "metadata_folder_name": "meta",
        "collaboration_separator": " & ",
    }
}

def _validate_config(config: Dict) -> None:
    try:
        AppConfig(**config)
    except ValidationError as e:
        raise ValueError(f"Invalid config: {e}")
    
def load_config(user_config_path: Path = None) -> Dict:
    config = copy.deepcopy(DEFAULT_CONFIG)
 
    if user_config_path:
        try:
            user_config = utils.load_json(user_config_path)
            config["html_settings"].update(user_config.get("html_settings", {}))
            config["media_rules"].update(user_config.get("media_rules", {}))
            print(f"Loaded configuration from {user_config_path}")
        except Exception as e:
            print(f"Warning: Could not load config file {user_config_path}: {e}")
            print("Proceeding with default internal configuration.")

    _validate_config(config)

    return config
    
def update_html_labels(config: Dict, preset_str: str) -> Dict:
    preset = LabelPreset(preset_str)
    overrides = _get_html_label_presets(preset) 
    config["html_settings"].update(overrides)
    
    _validate_config(config)

    return config
       
def apply_cli_media_overrides(config: Dict, image_gallery_max: Optional[int] = None, image_sample_strategy: Optional[ImageSampleStrategy] = None) -> Dict:
    if image_gallery_max is not None:
        config["html_settings"]["image_gallery_max"] = image_gallery_max
    if image_sample_strategy is not None:
        config["html_settings"]["image_gallery_sample_strategy"] = image_sample_strategy
    
    _validate_config(config)

    return config
 
def _get_html_label_presets(preset: LabelPreset) -> Dict:
    """
    Returns only the labels that are overridden by the selected preset. 
    Other configuration fields remain untouched.
    """
    match preset:
        case LabelPreset.FILM:
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
        case LabelPreset.MUSIC:
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
        case LabelPreset.ART:
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
        case LabelPreset.BOOK:
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
        case LabelPreset.MODEL:
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

