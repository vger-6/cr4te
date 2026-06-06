from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .build_issues import BuildIssue
from .enums.creator_type import CreatorType
from .enums.visible_fields import ProjectField
from .media_counts import MediaCounts, count_media_groups
from .schemas.library_schema import Creator, Project

__all__ = [
    "CreatorSummary",
    "LibraryIndex",
    "ProjectSummary",
    "summarize_creator",
]


@dataclass(frozen=True)
class ProjectSummary:
    title: str
    display_title: str
    release_date: str
    cover: str
    tags: dict[str, list[str]]
    facets: dict[ProjectField, list[str]]
    media_counts: MediaCounts


@dataclass(frozen=True)
class CreatorSummary:
    path: Path
    name: str
    display_name: str
    type: CreatorType
    portrait: str
    aliases: tuple[str, ...]
    collaborations: tuple[str, ...]
    tags: dict[str, list[str]]
    active_since: str
    nationalities: tuple[str, ...]
    info: str
    date_of_birth: str = ""
    place_of_birth: str = ""
    date_of_death: str = ""
    place_of_death: str = ""
    civil_name: str = ""
    founding_date: str = ""
    founding_location: str = ""
    dissolution_date: str = ""
    members: tuple[str, ...] = ()
    media_counts: MediaCounts = field(default_factory=MediaCounts)
    projects: tuple[ProjectSummary, ...] = ()

    @property
    def project_count(self) -> int:
        return len(self.projects)


@dataclass(frozen=True)
class LibraryIndex:
    input_dir: Path
    creators: tuple[CreatorSummary, ...]
    issues: tuple[BuildIssue, ...] = ()

    @property
    def creator_by_name(self) -> dict[str, CreatorSummary]:
        return {creator.name: creator for creator in self.creators}

    @property
    def project_count(self) -> int:
        return sum(creator.project_count for creator in self.creators)


def summarize_creator(creator_dir: Path, creator: Creator) -> CreatorSummary:
    project_summaries = tuple(_summarize_project(project) for project in creator.projects)
    media_counts = count_media_groups(creator.media_groups)
    for project in project_summaries:
        media_counts = media_counts.add(project.media_counts)

    return CreatorSummary(
        path=creator_dir,
        name=creator.name,
        display_name=creator.display_name,
        type=creator.type,
        portrait=creator.portrait,
        aliases=tuple(creator.aliases),
        collaborations=tuple(creator.collaborations),
        tags=creator.tags,
        active_since=creator.active_since,
        nationalities=tuple(creator.nationalities),
        info=creator.info,
        date_of_birth=creator.date_of_birth,
        place_of_birth=creator.place_of_birth,
        date_of_death=creator.date_of_death,
        place_of_death=creator.place_of_death,
        civil_name=creator.civil_name,
        founding_date=creator.founding_date,
        founding_location=creator.founding_location,
        dissolution_date=creator.dissolution_date,
        members=tuple(creator.members),
        media_counts=media_counts,
        projects=project_summaries,
    )


def _summarize_project(project: Project) -> ProjectSummary:
    return ProjectSummary(
        title=project.title,
        display_title=project.display_title,
        release_date=project.release_date,
        cover=project.cover,
        tags=project.tags,
        facets=project.facets,
        media_counts=count_media_groups(project.media_groups),
    )
