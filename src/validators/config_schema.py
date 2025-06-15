from enum import Enum
from typing import List

from pydantic import BaseModel, conint, validator

from enums.image_sample_strategy import ImageSampleStrategy
from enums.media_type import MediaType
from enums.visible_fields import CreatorField, CollaborationField, ProjectField

# HTML settings schema
class HtmlSettings(BaseModel):
    nav_creators_label: str
    nav_projects_label: str
    nav_tags_label: str

    creator_overview_page_title: str
    creator_overview_page_search_placeholder: str

    project_overview_page_title: str
    project_overview_page_search_placeholder: str

    creator_page_profile_title: str
    creator_page_about_title: str
    creator_page_tags_title: str
    creator_page_projects_title: str
    creator_page_collabs_title_prefix: str

    collaboration_page_profile_title: str
    collaboration_page_about_title: str
    collaboration_page_tags_title: str
    collaboration_page_members_title: str
    collaboration_page_projects_title: str

    project_page_overview_title: str
    project_page_description_title: str
    project_page_tags_title: str
    project_page_creator_profile: str
    project_page_audio_section_base_title: str
    project_page_image_section_base_title: str

    tags_page_title: str
    
    creator_overview_page_image_page_size: conint(ge=0)
    
    project_overview_page_image_page_size: conint(ge=0)

    creator_page_visible_creator_fields: List[CreatorField]
    creator_page_image_page_size: conint(ge=0)
    
    collaboration_page_visible_collaboration_fields: List[CollaborationField]
    project_page_visible_project_fields: List[ProjectField]

    project_page_image_page_size: conint(ge=0)
    
    project_page_show_image_captions: bool

    image_gallery_max: conint(ge=0)
    image_gallery_sample_strategy: ImageSampleStrategy

    type_order: List[MediaType]

# Media rules schema
class MediaRules(BaseModel):
    max_depth: conint(ge=0)
    global_exclude_prefix: str
    metadata_folder_name: str
    collaboration_separator: str

# Top-level config schema
class AppConfig(BaseModel):
    html_settings: HtmlSettings
    media_rules: MediaRules

