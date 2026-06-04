from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from .enums.media_type import MediaType
from .enums.thumb_type import ThumbType
from .enums.visible_fields import CollaborationField, CreatorField, ProjectField
from .schemas.config_schema import ProjectVisibleMetadataRendering, SiteLabels, SiteRendering
from .taxonomy import get_project_facet
from .metadata_fields import MetaField, get_core_meta_field
from .media_cache import MediaInfoCache
from .constants import (
    ASSETS_DIRNAME,
    CR4TE_ASSETS_DIR,
    CR4TE_DEFAULTS_DIR,
    CR4TE_CSS_DIR, 
    CR4TE_JS_DIR,
    OUTPUT_HTML_DIRNAME,
    OUTPUT_SYMLINKS_DIRNAME,
    OUTPUT_THUMBNAILS_DIRNAME,
    INDEX_HTML_FILE_NAME,
    PROJECTS_HTML_FILE_NAME,
    TAGS_HTML_FILE_NAME,
    CREATOR_OVERVIEW_THUMB_FILE_NAME,
    CREATOR_PAGE_PROJECT_THUMB_FILE_NAME,
    PROJECT_OVERVIEW_THUMB_FILE_NAME,
    PORTRAIT_THUMB_FILE_NAME,
    COVER_THUMB_FILE_NAME,
    GALLERY_THUMB_FILE_NAME,
    CREATOR_OVERVIEW_THUMB_HEIGHT,
    CREATOR_PAGE_PROJECT_THUMB_HEIGHT,
    PROJECT_OVERVIEW_THUMB_HEIGHT,
    GALLERY_THUMB_HEIGHT,
    PORTRAIT_THUMB_HEIGHT,
    COVER_THUMB_HEIGHT,
)

@dataclass
class HtmlBuildContext:
    input_dir: Path
    output_dir: Path
    site_labels: SiteLabels
    site_rendering: SiteRendering
    media_cache: MediaInfoCache = field(default_factory=MediaInfoCache)

    # Output paths
    @property
    def assets_dir(self) -> Path:
        return self.output_dir / ASSETS_DIRNAME

    @property
    def defaults_dir(self) -> Path:
        return self.assets_dir / CR4TE_DEFAULTS_DIR.relative_to(CR4TE_ASSETS_DIR)
    
    @property
    def css_dir(self) -> Path:
        return self.assets_dir / CR4TE_CSS_DIR.relative_to(CR4TE_ASSETS_DIR)
        
    @property
    def js_dir(self) -> Path:
        return self.assets_dir / CR4TE_JS_DIR.relative_to(CR4TE_ASSETS_DIR)
    
    @property
    def thumbs_dir(self) -> Path:
        return self.output_dir / OUTPUT_THUMBNAILS_DIRNAME

    @property
    def html_dir(self) -> Path:
        return self.output_dir / OUTPUT_HTML_DIRNAME

    @property
    def symlinks_dir(self) -> Path:
        return self.output_dir / OUTPUT_SYMLINKS_DIRNAME

    @property
    def index_html_path(self) -> Path:
        return self.output_dir / INDEX_HTML_FILE_NAME

    @property
    def projects_html_path(self) -> Path:
        return self.output_dir / PROJECTS_HTML_FILE_NAME

    @property
    def tags_html_path(self) -> Path:
        return self.output_dir / TAGS_HTML_FILE_NAME

    # Label helpers
    @property
    def audio_section_default_title(self) -> str:
        return self.site_labels.pages.audio_section_default_title

    @property
    def image_section_default_title(self) -> str:
        return self.site_labels.pages.image_section_default_title


    def meta_label(self, field: MetaField, count: int | None = None) -> str:
        if isinstance(field, ProjectField):
            facet = get_project_facet(field)
            if facet:
                return self.site_labels.project_facets[field].resolve(count)

        spec = get_core_meta_field(field)
        if spec:
            return spec.resolve_label(self.site_labels, count)

        raise KeyError(f"No metadata label registered for {field}")

    def meta_filter_label(self, field: CollaborationField | CreatorField | ProjectField) -> str:
        return self.meta_label(field, 2)

    # Rendering visibility and project metadata config
    @property
    def media_type_order(self) -> List[MediaType]:
        return self.site_rendering.media.type_order

    def _project_visible_metadata_config(self, field: ProjectField) -> ProjectVisibleMetadataRendering:
        return self.site_rendering.project_metadata.rendering_for(field)

    def _configured_project_visible_metadata_fields(self) -> List[ProjectField]:
        return self.site_rendering.project_metadata.configured_fields()

    def project_metadata_is_searchable(self, field: ProjectField) -> bool:
        config = self._project_visible_metadata_config(field)
        return bool(config.searchable or config.clickable or config.tags)

    def project_metadata_is_clickable(self, field: ProjectField) -> bool:
        return bool(self._project_visible_metadata_config(field).clickable)

    def project_metadata_has_tags(self, field: ProjectField) -> bool:
        return bool(self._project_visible_metadata_config(field).tags)

    def project_metadata_separator(self, field: ProjectField) -> str:
        return self._project_visible_metadata_config(field).separator

    @property
    def visible_project_metadata_fields(self) -> List[ProjectField]:
        return self._configured_project_visible_metadata_fields()

    @property
    def visible_project_fields(self) -> List[ProjectField]:
        return [
            *self.site_rendering.project_page.visible_fields,
            *self.visible_project_metadata_fields,
        ]

    @property
    def project_searchable_fields(self) -> List[ProjectField]:
        return [
            field
            for field in self._configured_project_visible_metadata_fields()
            if self.project_metadata_is_searchable(field)
        ]

    @property
    def project_tag_fields(self) -> List[ProjectField]:
        return [
            field
            for field in self._configured_project_visible_metadata_fields()
            if self.project_metadata_has_tags(field)
        ]

    @property
    def visible_creator_fields(self) -> List[CreatorField]:
        return self.site_rendering.creator_page.visible_creator_fields

    @property
    def visible_collaboration_fields(self) -> List[CollaborationField]:
        return self.site_rendering.creator_page.visible_collaboration_fields

    @property
    def visible_project_creator_fields(self) -> List[CreatorField]:
        return self.site_rendering.project_page.visible_creator_fields

    @property
    def visible_project_collaboration_fields(self) -> List[CollaborationField]:
        return self.site_rendering.project_page.visible_collaboration_fields

    # Thumbnail config
    def get_default_thumb_path(self, thumb_type: ThumbType) -> Path:
        return self.defaults_dir / {
            ThumbType.CREATOR_OVERVIEW: CREATOR_OVERVIEW_THUMB_FILE_NAME,
            ThumbType.PROJECT_OVERVIEW: PROJECT_OVERVIEW_THUMB_FILE_NAME,
            ThumbType.CREATOR_PAGE_PROJECT: CREATOR_PAGE_PROJECT_THUMB_FILE_NAME,
            ThumbType.PORTRAIT: PORTRAIT_THUMB_FILE_NAME,
            ThumbType.COVER: COVER_THUMB_FILE_NAME,
            ThumbType.GALLERY: GALLERY_THUMB_FILE_NAME,
        }[thumb_type]
        
    def get_generated_thumb_height(self, thumb_type: ThumbType) -> int:
        return {
            ThumbType.CREATOR_OVERVIEW: CREATOR_OVERVIEW_THUMB_HEIGHT,
            ThumbType.PROJECT_OVERVIEW: PROJECT_OVERVIEW_THUMB_HEIGHT,
            ThumbType.CREATOR_PAGE_PROJECT: CREATOR_PAGE_PROJECT_THUMB_HEIGHT,
            ThumbType.PORTRAIT: PORTRAIT_THUMB_HEIGHT,
            ThumbType.COVER: COVER_THUMB_HEIGHT,
            ThumbType.GALLERY: GALLERY_THUMB_HEIGHT,
        }[thumb_type]

    def get_display_image_max_height(self, thumb_type: ThumbType) -> int:
        return {
            ThumbType.CREATOR_OVERVIEW: self.site_rendering.galleries.creator_cards.image_max_height,
            ThumbType.PROJECT_OVERVIEW: self.site_rendering.galleries.project_cards.image_max_height,
            ThumbType.CREATOR_PAGE_PROJECT: self.site_rendering.galleries.project_cards.creator_page_image_max_height,
            ThumbType.PORTRAIT: PORTRAIT_THUMB_HEIGHT,
            ThumbType.COVER: COVER_THUMB_HEIGHT,
            ThumbType.GALLERY: self.site_rendering.galleries.media_groups.image_max_height,
        }[thumb_type]

