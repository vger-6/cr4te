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
from enums.domain_preset import DomainPreset
from enums.image_gallery_building_strategy import ImageGalleryBuildingStrategy

__all__ = ["load_config", "apply_cli_overrides"]

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
        "project_page_creator_profile_title": "Creator Profile",
        "project_page_audio_section_base_title": "Tracks",
        "project_page_image_section_base_title": "Images",
        
        "tags_page_title": "Tags",
        
        "image_gallery_max": 20,
        "image_gallery_sample_strategy": ImageSampleStrategy.SPREAD,
        
        "media_type_order": [MediaType.VIDEO, MediaType.AUDIO, MediaType.IMAGE, MediaType.TEXT, MediaType.DOCUMENT],
        
        "creator_gallery_building_strategy": ImageGalleryBuildingStrategy.ASPECT,
        "creator_gallery_aspect_ratio": "2/3",
        
        "project_gallery_building_strategy": ImageGalleryBuildingStrategy.ASPECT,
        "project_gallery_aspect_ratio": "3/2",
        
        "creator_overview_page_creator_gallery_page_size": 100,
        
        "project_overview_page_project_gallery_page_size": 100,
        
        "creator_page_visible_creator_fields": [f for f in CreatorField],
        "creator_page_image_gallery_page_size" : 15,
        
        "collaboration_page_visible_collaboration_fields": [f for f in CollaborationField],
        
        "project_page_visible_project_fields": [f for f in ProjectField],
        "project_page_image_gallery_page_size" : 15,
        "project_page_image_gallery_captions_visible": False,
    },
    "media_rules": {   
        "max_depth": 5,
        
        "global_exclude_prefix": "_",
        
        "metadata_folder_name": "meta",
        "collaboration_separators": ["&", ","],
        
        "portrait_basename": "portrait",
        "cover_basename": "cover",
    }
}

def _validate_config(config: Dict) -> None:
    try:
        AppConfig(**config)
    except ValidationError as e:
        error_lines = [f"[{name}] {err['loc'][0]}: {err['msg']}" for err in e.errors()]
        formatted = "\n".join(error_lines)
        raise ValueError(f"Validation failed for config:\n{formatted}")      
    
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
       
def apply_cli_overrides(config: Dict, image_gallery_max: Optional[int] = None, image_sample_strategy: Optional[ImageSampleStrategy] = None, domain_preset: Optional[DomainPreset] = None) -> Dict:
    if image_gallery_max is not None:
        config["html_settings"]["image_gallery_max"] = image_gallery_max
    if image_sample_strategy is not None:
        config["html_settings"]["image_gallery_sample_strategy"] = image_sample_strategy
    if domain_preset is not None:
        overrides = _get_domain_presets(domain_preset)
        config["html_settings"].update(overrides)
    
    _validate_config(config)

    return config
 
def _get_domain_presets(preset: DomainPreset) -> Dict:
    """
    Returns all config overrides for the selected domain preset, 
    including labels, media ordering, and gallery settings.
    """
    match preset:
        case DomainPreset.FILM:
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
                "project_page_creator_profile_title": "Profile",
            }
        case DomainPreset.MUSIC:
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
                "project_page_creator_profile_title": "Profile",
                "media_type_order": [MediaType.AUDIO, MediaType.IMAGE, MediaType.TEXT, MediaType.DOCUMENT, MediaType.VIDEO],
                "project_gallery_building_strategy": ImageGalleryBuildingStrategy.ASPECT,
                "project_gallery_aspect_ratio": "1/1",
            }
        case DomainPreset.ART:
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
                "project_page_creator_profile_title": "Profile",
            }
        case DomainPreset.BOOK:
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
                "project_page_creator_profile_title": "Profile",
                "media_type_order": [MediaType.DOCUMENT, MediaType.AUDIO, MediaType.IMAGE, MediaType.TEXT, MediaType.VIDEO],
                "project_gallery_building_strategy": ImageGalleryBuildingStrategy.ASPECT,
                "project_gallery_aspect_ratio": "1000/1414",
            }
        case DomainPreset.MODEL:
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
                "project_page_creator_profile_title": "Model Profile",
                "media_type_order": [MediaType.VIDEO, MediaType.IMAGE, MediaType.TEXT, MediaType.DOCUMENT, MediaType.AUDIO],
            }
        case _:
            raise ValueError(f"Unknown preset: {preset}")

