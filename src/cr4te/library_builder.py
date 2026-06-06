from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import replace
from pathlib import Path

from pydantic import ValidationError

from .build_issues import BuildIssueError, IssueScope
from .constants import README_FILE_NAME
from .creator_classification import infer_creator_type
from .enums.creator_type import CreatorType
from .library_index import CreatorSummary, LibraryIndex, summarize_creator
from .library_issues import (
    BuildIssuePolicy,
    invalid_collaboration_reference_issue,
    issue_from_exception,
)
from .library_metadata import (
    MetadataLoadError,
    load_json_model,
    metadata_path,
    metadata_relative_path,
    normalize_metadata_date,
)
from .library_scan import (
    CreatorScan,
    MediaBucket,
    iter_creator_dirs,
    iter_media_files,
    iter_project_dirs,
    media_groups_from_buckets,
    rel_to_input,
)
from .schemas.config_schema import MediaRules
from .schemas.library_schema import Creator, Project
from .schemas.metadata_file_schema import CreatorMetadata, ProjectMetadata
from .utils import text_utils

__all__ = [
    "build_library_index",
    "load_indexed_creator",
]

logger = logging.getLogger(__name__)


def _build_project(
    creator_dir: Path,
    project_dir: Path,
    project_metadata: ProjectMetadata,
    project_buckets: dict[Path, MediaBucket],
    scan: CreatorScan,
    media_rules: MediaRules,
    input_dir: Path,
) -> Project:
    project_name = project_dir.name
    cover = metadata_relative_path(project_dir, project_metadata.cover, input_dir, "cover")
    if not cover:
        selected_cover = scan.selected_cover(project_name)
        cover = rel_to_input(selected_cover, input_dir) if selected_cover else ""

    return Project(
        title=project_name,
        display_title=project_metadata.display_title.strip() or project_name,
        release_date=normalize_metadata_date(project_metadata.release_date, "release_date", f"{creator_dir.name} - {project_name}"),
        cover=cover,
        info=text_utils.read_text(project_dir / README_FILE_NAME),
        tags=project_metadata.tags,
        facets=project_metadata.facets,
        media_groups=media_groups_from_buckets(project_buckets, media_rules),
    )


def _infer_creator_type(creator_name: str, metadata: CreatorMetadata, media_rules: MediaRules) -> CreatorType:
    if metadata.type:
        return metadata.type
    return infer_creator_type(creator_name, media_rules.collaboration_separators)


def _build_creator(
    creator_dir: Path,
    input_dir: Path,
    media_rules: MediaRules,
    policy: BuildIssuePolicy,
) -> Creator:
    metadata = load_json_model(metadata_path(creator_dir), CreatorMetadata)
    scan = CreatorScan(creator_dir, input_dir, media_rules)
    for media_path in iter_media_files(creator_dir, media_rules):
        scan.add_media(media_path)

    creator_name = creator_dir.name
    display_name = metadata.display_name.strip() or creator_name
    creator_type = _infer_creator_type(creator_name, metadata, media_rules)
    portrait = metadata_relative_path(creator_dir, metadata.portrait, input_dir, "portrait")
    if not portrait:
        selected_portrait = scan.selected_portrait()
        portrait = rel_to_input(selected_portrait, input_dir) if selected_portrait else ""

    project_dirs = {project_dir.name: project_dir for project_dir in iter_project_dirs(creator_dir, media_rules)}
    project_names = sorted(set(project_dirs) | set(scan.project_buckets))
    projects = []
    for project_name in project_names:
        if project_name not in project_dirs:
            continue

        project_dir = project_dirs[project_name]
        try:
            project_metadata = load_json_model(metadata_path(project_dir), ProjectMetadata)
            projects.append(_build_project(
                creator_dir,
                project_dir,
                project_metadata,
                scan.project_buckets.get(project_name, {}),
                scan,
                media_rules,
                input_dir,
            ))
        except (MetadataLoadError, ValidationError, ValueError, OSError) as exc:
            policy.handle(issue_from_exception(project_dir, IssueScope.PROJECT, exc), exc)

    if creator_type == CreatorType.COLLABORATION:
        type_metadata = metadata.collaboration
    else:
        type_metadata = metadata.person

    active_since = normalize_metadata_date(type_metadata.active_since, "active_since", creator_name)
    info = text_utils.read_text(creator_dir / README_FILE_NAME)
    media_groups = media_groups_from_buckets(scan.creator_buckets, media_rules)

    if creator_type == CreatorType.COLLABORATION:
        members = metadata.collaboration.members
        if not members:
            members = [name.strip() for name in text_utils.multi_split(creator_name, media_rules.collaboration_separators)]
        return Creator(
            name=creator_name,
            display_name=display_name,
            portrait=portrait,
            type=creator_type,
            aliases=metadata.aliases,
            collaborations=metadata.collaborations,
            tags=metadata.tags,
            active_since=active_since,
            nationalities=type_metadata.nationalities,
            info=info,
            media_groups=media_groups,
            projects=projects,
            founding_date=normalize_metadata_date(metadata.collaboration.founding.date, "founding_date", creator_name),
            founding_location=metadata.collaboration.founding.place,
            dissolution_date=normalize_metadata_date(metadata.collaboration.dissolution_date, "dissolution_date", creator_name),
            members=members,
        )

    return Creator(
        name=creator_name,
        display_name=display_name,
        portrait=portrait,
        type=creator_type,
        aliases=metadata.aliases,
        collaborations=metadata.collaborations,
        tags=metadata.tags,
        active_since=active_since,
        nationalities=type_metadata.nationalities,
        info=info,
        media_groups=media_groups,
        projects=projects,
        date_of_birth=normalize_metadata_date(metadata.person.birth.date, "date_of_birth", creator_name),
        place_of_birth=metadata.person.birth.place,
        date_of_death=normalize_metadata_date(metadata.person.death.date, "date_of_death", creator_name),
        place_of_death=metadata.person.death.place,
        civil_name=metadata.person.civil_name,
    )


def _link_creator_summaries(summaries: list[CreatorSummary], policy: BuildIssuePolicy, input_dir: Path) -> tuple[CreatorSummary, ...]:
    creator_names = {summary.name for summary in summaries}
    reverse_links: dict[str, list[str]] = defaultdict(list)

    for summary in summaries:
        if summary.type != CreatorType.COLLABORATION:
            continue
        for member in summary.members:
            reverse_links[member].append(summary.name)

    linked: list[CreatorSummary] = []
    for summary in summaries:
        if summary.type == CreatorType.COLLABORATION:
            linked.append(summary)
            continue

        manual = [name for name in summary.collaborations if name in creator_names]
        invalid = sorted(set(summary.collaborations) - creator_names)
        if invalid:
            policy.handle(invalid_collaboration_reference_issue(input_dir / summary.name, invalid))

        collaborations = tuple(sorted(set(manual + reverse_links.get(summary.name, []))))
        linked.append(replace(summary, collaborations=collaborations))

    return tuple(linked)


def build_library_index(input_dir: Path, media_rules: MediaRules, strict: bool = False) -> LibraryIndex:
    input_dir = input_dir.resolve()

    summaries: list[CreatorSummary] = []
    policy = BuildIssuePolicy(strict=strict)
    for creator_dir in iter_creator_dirs(input_dir, media_rules):
        try:
            logger.info(f"Indexing: {creator_dir.name}")
            creator = _build_creator(creator_dir, input_dir, media_rules, policy)
            summaries.append(summarize_creator(creator_dir, creator))
        except BuildIssueError:
            raise
        except (MetadataLoadError, ValidationError, ValueError, OSError) as exc:
            policy.handle(issue_from_exception(creator_dir, IssueScope.CREATOR, exc), exc)

    return LibraryIndex(
        input_dir=input_dir,
        creators=_link_creator_summaries(summaries, policy, input_dir),
        issues=tuple(policy.issues),
    )


def load_indexed_creator(index: LibraryIndex, summary: CreatorSummary, media_rules: MediaRules) -> Creator:
    policy = BuildIssuePolicy(strict=False)
    creator = _build_creator(summary.path, index.input_dir, media_rules, policy)
    return creator.model_copy(update={"collaborations": list(summary.collaborations)})
