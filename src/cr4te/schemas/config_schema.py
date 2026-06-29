from typing import Dict, List
from pydantic import BaseModel, ConfigDict, conint, field_validator

from ..enums.image_sample_strategy import ImageSampleStrategy
from ..enums.image_gallery_building_strategy import ImageGalleryBuildingStrategy
from ..enums.media_type import MediaType
from ..enums.portrait_discovery import PortraitDiscovery
from ..enums.portrait_visibility import PortraitVisibility
from ..enums.visible_fields import CollaborationField, CreatorField, ProjectField
from ..utils.format_utils import validate_named_format
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


class CountLabels(StrictConfigModel):
    project: str
    projects: str


class ControlLabels(StrictConfigModel):
    search_placeholder_format: str
    clear_search: str
    themes: str
    fullscreen: str
    open_in_new_tab: str
    play: str
    pause: str
    stop: str
    previous: str
    next: str
    mute: str
    unmute: str
    seek: str
    volume: str
    show_captions: str
    hide_captions: str
    show_more: str
    show_less: str

    @field_validator("search_placeholder_format")
    @classmethod
    def validate_search_placeholder_format(cls, value: str) -> str:
        return validate_named_format(
            value,
            allowed_fields=frozenset({"creators", "projects", "tags"}),
            required_fields=frozenset({"creators", "projects", "tags"}),
        )


class PageLabels(StrictConfigModel):
    creator_profile_title: str
    creator_about_title: str
    creator_collaboration_projects_title_format: str
    project_overview_title: str
    project_description_title: str
    audio_section_default_title: str
    image_section_default_title: str

    @field_validator("creator_collaboration_projects_title_format")
    @classmethod
    def validate_creator_collaboration_projects_title_format(cls, value: str) -> str:
        return validate_named_format(
            value,
            allowed_fields=frozenset({"collaborator", "projects"}),
            required_fields=frozenset({"collaborator"}),
        )


class EmptyStateLabels(StrictConfigModel):
    no_creators_format: str
    no_projects_format: str
    no_tags_format: str
    no_projects_or_media_format: str
    no_search_results: str
    no_media: str

    @field_validator("no_creators_format")
    @classmethod
    def validate_no_creators_format(cls, value: str) -> str:
        return validate_named_format(
            value,
            allowed_fields=frozenset({"creators"}),
            required_fields=frozenset({"creators"}),
        )

    @field_validator("no_projects_format", "no_projects_or_media_format")
    @classmethod
    def validate_project_empty_state_formats(cls, value: str) -> str:
        return validate_named_format(
            value,
            allowed_fields=frozenset({"projects"}),
            required_fields=frozenset({"projects"}),
        )

    @field_validator("no_tags_format")
    @classmethod
    def validate_no_tags_format(cls, value: str) -> str:
        return validate_named_format(
            value,
            allowed_fields=frozenset({"tags"}),
            required_fields=frozenset({"tags"}),
        )


class AccessibilityLabels(StrictConfigModel):
    site_logo_overview_label_format: str
    creator_thumbnail_description_format: str
    creator_portrait_description_format: str
    project_thumbnail_description_format: str
    project_preview_description_format: str

    @field_validator(
        "creator_thumbnail_description_format",
        "creator_portrait_description_format",
    )
    @classmethod
    def validate_creator_description_formats(cls, value: str) -> str:
        return validate_named_format(
            value,
            allowed_fields=frozenset({"creator"}),
            required_fields=frozenset({"creator"}),
        )

    @field_validator(
        "project_thumbnail_description_format",
        "project_preview_description_format",
    )
    @classmethod
    def validate_project_description_formats(cls, value: str) -> str:
        return validate_named_format(
            value,
            allowed_fields=frozenset({"project"}),
            required_fields=frozenset({"project"}),
        )

    @field_validator("site_logo_overview_label_format")
    @classmethod
    def validate_site_logo_overview_label_format(cls, value: str) -> str:
        return validate_named_format(
            value,
            allowed_fields=frozenset({"overview"}),
            required_fields=frozenset({"overview"}),
        )


class MetadataLabels(StrictConfigModel):
    title: str
    release_date: str
    name: str
    members: str
    birth: str
    death: str
    nationality: str
    nationalities: str
    civil_name: str
    alias: str
    aliases: str
    debut_age: str
    age_at_time: str
    active_since: str
    founding: str
    dissolution_date: str
    date_and_place_format: str

    @field_validator("date_and_place_format")
    @classmethod
    def validate_date_and_place_format(cls, value: str) -> str:
        return validate_named_format(
            value,
            allowed_fields=frozenset({"date", "place"}),
            required_fields=frozenset({"date", "place"}),
        )


class ProjectFacetLabels(StrictConfigModel):
    singular: str
    plural: str

    def resolve(self, count: int | None = None) -> str:
        return self.singular if count == 1 else self.plural


class SiteLabels(StrictConfigModel):
    entity: EntityLabels
    media: MediaLabels
    counts: CountLabels
    controls: ControlLabels
    pages: PageLabels
    empty_states: EmptyStateLabels
    accessibility: AccessibilityLabels
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

    @field_validator("aspect_ratio", mode="before")
    @classmethod
    def validate_and_normalize_aspect_ratio(cls, value: object) -> str:
        width, height = parse_aspect_ratio(value)
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
    about_collapsed_lines: conint(gt=0)
    about_collapsed_lines_mobile: conint(gt=0)


class ProjectPageRendering(StrictConfigModel):
    visible_fields: List[ProjectField]
    visible_creator_fields: List[CreatorField]
    visible_collaboration_fields: List[CollaborationField]
    media_gallery_page_size: conint(ge=0)
    description_collapsed_lines: conint(gt=0)
    description_collapsed_lines_mobile: conint(gt=0)


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
    visibility: PortraitVisibility


class SiteRendering(StrictConfigModel):
    document_language: str
    media: MediaRendering
    galleries: GalleryRendering
    creator_page: CreatorPageRendering
    project_page: ProjectPageRendering
    project_metadata: ProjectMetadataRendering
    portraits: PortraitRendering

    @field_validator("document_language")
    @classmethod
    def validate_document_language(cls, value: str) -> str:
        language = value.strip()
        if not language:
            raise ValueError("document_language must not be empty")
        return language


# Media rules schema
class MediaRules(StrictConfigModel):
    max_search_depth: conint(ge=0)
    image_gallery_sample_max: conint(ge=0)
    image_gallery_sample_strategy: ImageSampleStrategy
    global_exclude_prefix: str
    metadata_folder_name: str
    collaboration_separators: List[str]
    portrait_discovery: PortraitDiscovery
    portrait_basename: str
    cover_basename: str

# Top-level config schema
class AppConfig(StrictConfigModel):
    site_labels: SiteLabels
    site_rendering: SiteRendering
    media_rules: MediaRules

