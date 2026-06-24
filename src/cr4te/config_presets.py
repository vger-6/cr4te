from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any

from .enums.domain import Domain
from .enums.image_gallery_building_strategy import ImageGalleryBuildingStrategy
from .enums.image_sample_strategy import ImageSampleStrategy
from .enums.media_type import MediaType
from .enums.portrait_discovery import PortraitDiscovery
from .enums.portrait_visibility import PortraitVisibility
from .enums.visible_fields import CollaborationField, CreatorField, ProjectField
from .taxonomy import get_domain_project_visible_metadata, get_project_facet_label_defaults

ConfigSection = dict[str, Any]

__all__ = [
    "ConfigPreset",
    "DEFAULT_CONFIG",
    "PROJECT_VISIBLE_METADATA_DEFAULTS",
    "get_domain_preset",
]

PROJECT_VISIBLE_METADATA_DEFAULTS = {
    "separator": ", ",
    "searchable": False,
    "clickable": False,
    "tags": False,
}

CREATOR_VISIBLE_FIELDS = [
    CreatorField.NAME,
    CreatorField.BIRTH,
    CreatorField.DEATH,
    CreatorField.NATIONALITIES,
    CreatorField.CIVIL_NAME,
    CreatorField.ALIASES,
    CreatorField.DEBUT_AGE,
    CreatorField.AGE_AT_TIME,
    CreatorField.ACTIVE_SINCE,
]

COLLABORATION_VISIBLE_FIELDS = [
    CollaborationField.NAME,
    CollaborationField.NATIONALITIES,
    CollaborationField.ALIASES,
    CollaborationField.ACTIVE_SINCE,
    CollaborationField.MEMBERS,
    CollaborationField.FOUNDING,
    CollaborationField.DISSOLUTION_DATE,
]

COLLABORATION_VISIBLE_FIELDS_WITHOUT_NAME = [
    field
    for field in COLLABORATION_VISIBLE_FIELDS
    if field != CollaborationField.NAME
]

DEFAULT_ENTITY_LABELS = {
    "creator": "Creator",
    "creators": "Creators",
    "project": "Project",
    "projects": "Projects",
    "tags": "Tags",
    "portrait": "Portrait",
    "cover": "Cover",
    "gallery": "Gallery",
}

DEFAULT_MEDIA_LABELS = {
    "video": "video",
    "videos": "videos",
    "audio_track": "audio track",
    "audio_tracks": "audio tracks",
    "image": "image",
    "images": "images",
    "document": "document",
    "documents": "documents",
    "text_file": "text file",
    "text_files": "text files",
}

DEFAULT_COUNT_LABELS = {
    "project": "project",
    "projects": "projects",
}

DEFAULT_CONTROL_LABELS = {
    "search_placeholder_format": "Search {creators}, {projects}, {tags}...",
    "clear_search": "Clear search",
    "themes": "Themes",
    "fullscreen": "Fullscreen",
    "open_in_new_tab": "Open in new tab",
    "play": "Play",
    "pause": "Pause",
    "stop": "Stop",
    "previous": "Previous",
    "next": "Next",
    "mute": "Mute",
    "unmute": "Unmute",
    "seek": "Seek",
    "volume": "Volume",
    "show_captions": "Show captions",
    "hide_captions": "Hide captions",
}

DEFAULT_PAGE_LABELS = {
    "creator_profile_title": "Profile",
    "creator_about_title": "About",
    "creator_collaboration_projects_title_format": "{projects} with {collaborator}",
    "project_overview_title": "Overview",
    "project_description_title": "Description",
    "audio_section_default_title": "Audio",
    "image_section_default_title": "Images",
}

DEFAULT_EMPTY_STATE_LABELS = {
    "no_creators_format": "No {creators} available",
    "no_projects_format": "No {projects} available",
    "no_tags_format": "No {tags} available",
    "no_projects_or_media_format": "No {projects} or media available",
    "no_search_results": "No results match your search",
    "no_media": "No media available",
}

DEFAULT_ACCESSIBILITY_LABELS = {
    "site_logo_overview_label_format": "cr4te {overview} overview",
    "creator_thumbnail_description_format": "Thumbnail for {creator}",
    "creator_portrait_description_format": "Portrait of {creator}",
    "project_thumbnail_description_format": "Thumbnail for {project}",
    "project_preview_description_format": "Preview of {project}",
}

DEFAULT_METADATA_LABELS = {
    "title": "Title",
    "release_date": "Release Date",
    "name": "Name",
    "members": "Members",
    "birth": "Born",
    "death": "Died",
    "nationality": "Nationality",
    "nationalities": "Nationalities",
    "civil_name": "Civil Name",
    "alias": "Alias",
    "aliases": "Aliases",
    "debut_age": "Debut Age",
    "age_at_time": "Age at Time",
    "active_since": "Active Since",
    "founding": "Founded",
    "dissolution_date": "Dissolved",
    "date_and_place_format": "{date} in {place}",
}

DEFAULT_SITE_LABELS = {
    "entity": DEFAULT_ENTITY_LABELS,
    "media": DEFAULT_MEDIA_LABELS,
    "counts": DEFAULT_COUNT_LABELS,
    "controls": DEFAULT_CONTROL_LABELS,
    "pages": DEFAULT_PAGE_LABELS,
    "empty_states": DEFAULT_EMPTY_STATE_LABELS,
    "accessibility": DEFAULT_ACCESSIBILITY_LABELS,
    "metadata": DEFAULT_METADATA_LABELS,
    "project_facets": get_project_facet_label_defaults(),
}

DEFAULT_CONFIG = {
    "site_labels": DEFAULT_SITE_LABELS,
    "site_rendering": {
        "media": {
            "type_order": [
                MediaType.VIDEO,
                MediaType.AUDIO,
                MediaType.IMAGE,
                MediaType.TEXT,
                MediaType.DOCUMENT,
            ],
        },
        "galleries": {
            "creator_cards": {
                "building_strategy": ImageGalleryBuildingStrategy.ASPECT,
                "aspect_ratio": "2/3",
                "page_size": 100,
                "image_max_height": 300,
            },
            "project_cards": {
                "building_strategy": ImageGalleryBuildingStrategy.ASPECT,
                "aspect_ratio": "3/2",
                "page_size": 100,
                "image_max_height": 300,
                "creator_page_image_max_height": 300,
            },
            "media_groups": {
                "image_max_height": 300,
            },
        },
        "creator_page": {
            "visible_creator_fields": CREATOR_VISIBLE_FIELDS,
            "visible_collaboration_fields": COLLABORATION_VISIBLE_FIELDS,
            "media_gallery_page_size": 15,
        },
        "project_page": {
            "visible_fields": [ProjectField.TITLE, ProjectField.RELEASE_DATE],
            "visible_creator_fields": CREATOR_VISIBLE_FIELDS,
            "visible_collaboration_fields": COLLABORATION_VISIBLE_FIELDS,
            "media_gallery_page_size": 15,
        },
        "project_metadata": {
            "defaults": PROJECT_VISIBLE_METADATA_DEFAULTS,
            "fields": {},
        },
        "portraits": {
            "visibility": PortraitVisibility.ALL,
        },
    },
    "media_rules": {
        "max_search_depth": 5,
        "image_gallery_sample_max": 20,
        "image_gallery_sample_strategy": ImageSampleStrategy.SPREAD,
        "global_exclude_prefix": "_",
        "metadata_folder_name": "meta",
        "collaboration_separators": ["&", ","],
        "portrait_discovery": PortraitDiscovery.NAMED,
        "portrait_basename": "portrait",
        "cover_basename": "cover",
    },
}


@dataclass(frozen=True)
class ConfigPreset:
    site_labels: ConfigSection = field(default_factory=dict)
    site_rendering: ConfigSection = field(default_factory=dict)
    media_rules: ConfigSection = field(default_factory=dict)

    def sections(self) -> dict[str, ConfigSection]:
        return {
            "site_labels": copy.deepcopy(self.site_labels),
            "site_rendering": copy.deepcopy(self.site_rendering),
            "media_rules": copy.deepcopy(self.media_rules),
        }


def get_domain_preset(domain: Domain) -> ConfigPreset:
    match domain:
        case Domain.CREATOR:
            return ConfigPreset()
        case Domain.FILM:
            return ConfigPreset(
                site_labels={
                    "entity": {
                        "creator": "Director",
                        "creators": "Directors",
                        "project": "Movie",
                        "projects": "Movies",
                    },
                    "counts": {"project": "movie", "projects": "movies"},
                    "metadata": {"members": "Directors'"},
                    "pages": {
                        "audio_section_default_title": "Soundtrack",
                        "creator_collaboration_projects_title_format": "Codirected with {collaborator}",
                    },
                },
                site_rendering={
                    "creator_page": {
                        "visible_collaboration_fields": COLLABORATION_VISIBLE_FIELDS_WITHOUT_NAME,
                    },
                    "galleries": {"project_cards": {"aspect_ratio": "2/3"}},
                    "project_page": {
                        "visible_collaboration_fields": COLLABORATION_VISIBLE_FIELDS_WITHOUT_NAME,
                    },
                    "project_metadata": {"fields": get_domain_project_visible_metadata(Domain.FILM)},
                },
            )
        case Domain.MUSIC:
            return ConfigPreset(
                site_labels={
                    "entity": {
                        "creator": "Musician",
                        "creators": "Musicians",
                        "project": "Album",
                        "projects": "Albums",
                    },
                    "counts": {"project": "album", "projects": "albums"},
                    "pages": {
                        "audio_section_default_title": "Tracks",
                    },
                },
                site_rendering={
                    "media": {
                        "type_order": [
                            MediaType.AUDIO,
                            MediaType.IMAGE,
                            MediaType.TEXT,
                            MediaType.DOCUMENT,
                            MediaType.VIDEO,
                        ],
                    },
                    "galleries": {
                        "project_cards": {
                            "building_strategy": ImageGalleryBuildingStrategy.ASPECT,
                            "aspect_ratio": "1/1",
                        },
                    },
                    "project_metadata": {"fields": get_domain_project_visible_metadata(Domain.MUSIC)},
                },
            )
        case Domain.ART:
            return ConfigPreset(
                site_labels={
                    "entity": {
                        "creator": "Artist",
                        "creators": "Artists",
                        "project": "Work",
                        "projects": "Works",
                    },
                    "counts": {"project": "work", "projects": "works"},
                },
                site_rendering={
                    "media": {
                        "type_order": [
                            MediaType.AUDIO,
                            MediaType.IMAGE,
                            MediaType.TEXT,
                            MediaType.DOCUMENT,
                            MediaType.VIDEO,
                        ],
                    },
                    "galleries": {"project_cards": {"aspect_ratio": "1/1"}},
                    "project_metadata": {"fields": get_domain_project_visible_metadata(Domain.ART)},
                },
            )
        case Domain.BOOK:
            return ConfigPreset(
                site_labels={
                    "entity": {
                        "creator": "Author",
                        "creators": "Authors",
                        "project": "Book",
                        "projects": "Books",
                    },
                    "counts": {"project": "book", "projects": "books"},
                    "metadata": {"members": "Authors"},
                    "pages": {
                        "audio_section_default_title": "Audio",
                    },
                },
                site_rendering={
                    "creator_page": {
                        "visible_collaboration_fields": COLLABORATION_VISIBLE_FIELDS_WITHOUT_NAME,
                    },
                    "media": {
                        "type_order": [
                            MediaType.DOCUMENT,
                            MediaType.AUDIO,
                            MediaType.IMAGE,
                            MediaType.TEXT,
                            MediaType.VIDEO,
                        ],
                    },
                    "galleries": {
                        "project_cards": {
                            "building_strategy": ImageGalleryBuildingStrategy.ASPECT,
                            "aspect_ratio": "1000/1414",
                        },
                    },
                    "project_page": {
                        "visible_collaboration_fields": COLLABORATION_VISIBLE_FIELDS_WITHOUT_NAME,
                    },
                    "project_metadata": {"fields": get_domain_project_visible_metadata(Domain.BOOK)},
                },
                media_rules={
                    "collaboration_separators": ["&"],
                }
            )
        case Domain.MODEL:
            return ConfigPreset(
                site_labels={
                    "entity": {
                        "creator": "Model",
                        "creators": "Models",
                        "project": "Scene",
                        "projects": "Scenes",
                    },
                    "counts": {"project": "scene", "projects": "scenes"},
                    "metadata": {"members": "Models"},
                },
                site_rendering={
                    "creator_page": {
                        "visible_collaboration_fields": COLLABORATION_VISIBLE_FIELDS_WITHOUT_NAME,
                    },
                    "media": {
                        "type_order": [
                            MediaType.VIDEO,
                            MediaType.IMAGE,
                            MediaType.TEXT,
                            MediaType.DOCUMENT,
                            MediaType.AUDIO,
                        ],
                    },
                    "project_page": {
                        "visible_collaboration_fields": COLLABORATION_VISIBLE_FIELDS_WITHOUT_NAME,
                    },
                    "project_metadata": {"fields": get_domain_project_visible_metadata(Domain.MODEL)},
                },
            )

    raise ValueError(f"Unknown domain: {domain}")
