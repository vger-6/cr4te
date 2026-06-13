from __future__ import annotations

from dataclasses import dataclass, field

from .enums.media_type import MediaType
from .enums.orientation import Orientation
from .media_counts import MediaCounts

__all__ = [
    "CollaborationProjectsContext",
    "CreatorStats",
    "CreatorLinkContext",
    "CreatorOverviewEntry",
    "CreatorPageContext",
    "CreatorProfileContext",
    "DocumentContext",
    "GalleryImageContext",
    "MediaGroupContext",
    "MediaSectionContext",
    "MediaCounts",
    "MetaEntry",
    "NavigationItem",
    "PageShellContext",
    "ProjectCardContext",
    "ProjectOverviewEntry",
    "ProjectPageContext",
    "TagCollection",
    "TagGroup",
    "TextContext",
    "ThumbnailContext",
    "TrackContext",
    "VideoContext",
]


@dataclass(frozen=True)
class CreatorStats:
    project_count: int
    media_counts: MediaCounts


@dataclass(frozen=True)
class TagGroup:
    category: str
    tags: tuple[str, ...]


@dataclass(frozen=True)
class TagCollection:
    groups: tuple[TagGroup, ...] = ()

    def __bool__(self) -> bool:
        return bool(self.groups)

    def as_dict(self) -> dict[str, list[str]]:
        return {
            group.category: list(group.tags)
            for group in self.groups
        }


@dataclass(frozen=True)
class MetaEntry:
    label: str
    values: list[str]
    separator: str = ", "
    hrefs: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class NavigationItem:
    label: str
    href: str
    current: bool = False


@dataclass(frozen=True)
class PageShellContext:
    title: str
    layout_stylesheet: str
    navigation_items: tuple[NavigationItem, ...]


@dataclass(frozen=True)
class ThumbnailContext:
    rel_thumbnail_path: str
    image_wrapper_width: int
    image_wrapper_height: int


@dataclass(frozen=True)
class GalleryImageContext:
    rel_thumbnail_path: str
    image_wrapper_width: int
    image_wrapper_height: int
    rel_path: str
    caption: str


@dataclass(frozen=True)
class VideoContext:
    rel_path: str
    title: str
    rel_poster_path: str = ""


@dataclass(frozen=True)
class TrackContext:
    rel_path: str
    title: str
    duration_seconds: float


@dataclass(frozen=True)
class DocumentContext:
    rel_path: str
    title: str


@dataclass(frozen=True)
class TextContext:
    content: str
    title: str


@dataclass(frozen=True)
class MediaSectionContext:
    type: MediaType
    videos: list[VideoContext] = field(default_factory=list)
    tracks: list[TrackContext] = field(default_factory=list)
    images: list[GalleryImageContext] = field(default_factory=list)
    documents: list[DocumentContext] = field(default_factory=list)
    texts: list[TextContext] = field(default_factory=list)
    total_duration_seconds: float = 0.0


@dataclass(frozen=True)
class MediaGroupContext:
    audio_section_title: str
    image_section_title: str
    sections: list[MediaSectionContext]


@dataclass(frozen=True)
class CreatorProfileContext:
    name: str
    rel_html_path: str
    rel_portrait_path: str
    meta_entries: list[MetaEntry] = field(default_factory=list)
    age_at_release: int | None = None


@dataclass(frozen=True)
class CreatorLinkContext:
    name: str
    rel_thumbnail_path: str
    meta_entries: list[MetaEntry] = field(default_factory=list)


@dataclass(frozen=True)
class ProjectCardContext:
    title: str
    rel_html_path: str
    rel_thumbnail_path: str
    image_wrapper_width: int
    image_wrapper_height: int
    media_counts: MediaCounts


@dataclass(frozen=True)
class CollaborationProjectsContext:
    label: str
    projects: list[ProjectCardContext]


@dataclass(frozen=True)
class CreatorPageContext:
    type: str
    name: str
    rel_portrait_path: str
    portrait_orientation: Orientation | None
    info_html: str
    tags: TagCollection
    projects: list[ProjectCardContext]
    media_groups: list[MediaGroupContext]
    collaborations: list[CollaborationProjectsContext]
    creator_stats: CreatorStats
    meta_entries: list[MetaEntry]
    members: list[CreatorLinkContext] = field(default_factory=list)


@dataclass(frozen=True)
class ProjectPageContext:
    title: str
    release_date: str
    meta_entries: list[MetaEntry]
    rel_thumbnail_path: str
    thumbnail_orientation: Orientation
    info_html: str
    tags: TagCollection
    media_groups: list[MediaGroupContext]
    creator: CreatorProfileContext | None = None
    collaboration: CreatorProfileContext | None = None
    participants: list[CreatorProfileContext] = field(default_factory=list)


@dataclass(frozen=True)
class CreatorOverviewEntry:
    name: str
    rel_html_path: str
    search_text: str
    rel_thumbnail_path: str
    image_wrapper_width: int
    image_wrapper_height: int
    project_count: int
    media_counts: MediaCounts
    project_count_summary: str
    media_count_summary: str


@dataclass(frozen=True)
class ProjectOverviewEntry:
    title: str
    rel_html_path: str
    rel_thumbnail_path: str
    image_wrapper_width: int
    image_wrapper_height: int
    creator_name: str
    search_text: str
    media_counts: MediaCounts
