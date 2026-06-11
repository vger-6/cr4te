from typing import Dict, List

from pydantic import BaseModel, ConfigDict, conint, field_validator

from ..enums.image_sample_strategy import ImageSampleStrategy
from ..enums.image_gallery_building_strategy import ImageGalleryBuildingStrategy
from ..enums.media_type import MediaType
from ..enums.visible_fields import CollaborationField, CreatorField, ProjectField
from ..utils.image_utils import parse_aspect_ratio

class StrictConfigModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


# Site label schema
class EntityLabels(StrictConfigModel):
    creator: str
    creators: str
    project: str
    projects: str
    tags: str
    portrait: str
    cover: str
    gallery: str


class MediaLabels(StrictConfigModel):
    video: str
    videos: str
    audio_track: str
    audio_tracks: str
    image: str
    images: str
    document: str
    documents: str
    text_file: str
    text_files: str


class ControlLabels(StrictConfigModel):
    search_placeholder: str
    fullscreen: str
    open_in_new_tab: str
    play: str
    pause: str
    stop: str
    previous: str
    next: str
    mute: str
    unmute: str
    show_captions: str
    hide_captions: str


class PageLabels(StrictConfigModel):
    creator_profile_title: str
    creator_about_title: str
    creator_collabs_title_prefix: str
    project_overview_title: str
    project_description_title: str
    audio_section_default_title: str
    image_section_default_title: str


class MetadataLabels(StrictConfigModel):
    title: str
    release_date: str
    name: str
    members: str
    date_of_birth: str
    place_of_birth: str
    date_of_death: str
    place_of_death: str
    nationality: str
    nationalities: str
    civil_name: str
    alias: str
    aliases: str
    debut_age: str
    age_at_time: str
    active_since: str
    founding_date: str
    founding_location: str
    dissolution_date: str


class ProjectFacetLabels(StrictConfigModel):
    singular: str
    plural: str

    def resolve(self, count: int | None = None) -> str:
        return self.singular if count == 1 else self.plural


class SiteLabels(StrictConfigModel):
    entity: EntityLabels
    media: MediaLabels
    controls: ControlLabels
    pages: PageLabels
    metadata: MetadataLabels
    project_facets: Dict[ProjectField, ProjectFacetLabels]


# Site rendering schema
class ProjectVisibleMetadataRendering(StrictConfigModel):
    separator: str = ", "
    searchable: bool = False
    clickable: bool = False
    tags: bool = False


class GalleryLayoutRendering(StrictConfigModel):
    building_strategy: ImageGalleryBuildingStrategy
    aspect_ratio: str

    # TODO: Is requiring slash-separated aspect ratios here the right choice, or should we reconsider supporting other formats?
    @field_validator("aspect_ratio")
    def validate_aspect_ratio_colon_format(cls, v):
        width, height = parse_aspect_ratio(v)
        return f"{width}/{height}"


class OverviewCardGalleryRendering(GalleryLayoutRendering):
    page_size: conint(ge=0)
    image_max_height: conint(gt=0)


class ProjectCardGalleryRendering(OverviewCardGalleryRendering):
    creator_page_image_max_height: conint(gt=0)


class MediaGroupGalleryRendering(StrictConfigModel):
    image_max_height: conint(gt=0)


class GalleryRendering(StrictConfigModel):
    creator_cards: OverviewCardGalleryRendering
    project_cards: ProjectCardGalleryRendering
    media_groups: MediaGroupGalleryRendering


class MediaRendering(StrictConfigModel):
    type_order: List[MediaType]


class CreatorPageRendering(StrictConfigModel):
    visible_creator_fields: List[CreatorField]
    visible_collaboration_fields: List[CollaborationField]
    media_gallery_page_size: conint(ge=0)


class ProjectPageRendering(StrictConfigModel):
    visible_fields: List[ProjectField]
    visible_creator_fields: List[CreatorField]
    visible_collaboration_fields: List[CollaborationField]
    media_gallery_page_size: conint(ge=0)


class ProjectMetadataRendering(StrictConfigModel):
    defaults: ProjectVisibleMetadataRendering
    fields: Dict[ProjectField, ProjectVisibleMetadataRendering]

    def rendering_for(self, field: ProjectField) -> ProjectVisibleMetadataRendering:
        field_config = self.fields.get(field)
        if field_config is None:
            return self.defaults

        config = self.defaults.model_dump(mode="python")
        config.update(field_config.model_dump(mode="python"))
        return ProjectVisibleMetadataRendering(**config)

    def configured_fields(self) -> List[ProjectField]:
        return list(self.fields)


class PortraitRendering(StrictConfigModel):
    hide: bool


class SiteRendering(StrictConfigModel):
    media: MediaRendering
    galleries: GalleryRendering
    creator_page: CreatorPageRendering
    project_page: ProjectPageRendering
    project_metadata: ProjectMetadataRendering
    portraits: PortraitRendering

# Media rules schema
class MediaRules(StrictConfigModel):
    max_search_depth: conint(ge=0)
    image_gallery_sample_max: conint(ge=0)
    image_gallery_sample_strategy: ImageSampleStrategy
    global_exclude_prefix: str
    metadata_folder_name: str
    collaboration_separators: List[str]
    portrait_basename: str
    cover_basename: str
    auto_find_portraits: bool

# Top-level config schema
class AppConfig(StrictConfigModel):
    site_labels: SiteLabels
    site_rendering: SiteRendering
    media_rules: MediaRules

