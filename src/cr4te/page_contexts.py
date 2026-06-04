from __future__ import annotations

import logging
from dataclasses import replace
from pathlib import Path
from typing import Callable, Optional

from .constants import INDEX_HTML_FILE_NAME
from .html_context import HtmlBuildContext
from .enums.creator_type import CreatorType
from .enums.thumb_type import ThumbType
from .enums.visible_fields import CollaborationField, CreatorField, ProjectField
from .html_paths import build_rel_creator_html_path, build_rel_project_html_path
from .media_counts import count_media_groups
from .render_assets import build_thumbnail_context, get_image_orientation, resolve_thumbnail_or_default
from .render_media import build_media_group_contexts
from .render_metadata import (
    build_collaboration_meta_entries,
    build_creator_meta_entries,
    build_project_creator_meta_entries,
    build_project_meta_entries,
    calculate_age_at_release,
    calculate_debut_age,
)
from .render_models import (
    CollaborationProjectsContext,
    CreatorLinkContext,
    CreatorPageContext,
    CreatorProfileContext,
    CreatorStats,
    ProjectCardContext,
    ProjectPageContext,
)
from .schemas.library_schema import Creator as CreatorModel, Project as ProjectModel
from .tag_contexts import (
    collect_project_metadata_tags,
    collect_tags_from_creator,
    merge_tag_maps,
)
from .utils.sorting_utils import dated_title_sort_key
from .utils import date_utils, path_utils, text_utils

__all__ = [
    "CreatorLoader",
    "build_creator_page_context",
    "build_project_page_context",
    "compute_creator_stats",
    "sort_project",
]

logger = logging.getLogger(__name__)
CreatorLoader = Callable[[str], Optional[CreatorModel]]

def sort_project(project: ProjectModel) -> tuple:
    return dated_title_sort_key(date_utils.parse_date(project.release_date), project.title)


def compute_creator_stats(creator: CreatorModel) -> CreatorStats:
    project_count = len(creator.projects)
    total_media_counts = count_media_groups(creator.media_groups)

    for project in creator.projects:
        total_media_counts = total_media_counts.add(count_media_groups(project.media_groups))

    return CreatorStats(project_count=project_count, media_counts=total_media_counts)


def build_project_page_context(
    ctx: HtmlBuildContext,
    creator: CreatorModel,
    project: ProjectModel,
    get_creator: CreatorLoader,
) -> ProjectPageContext:
    visible = ctx.visible_project_fields
    thumb_path = resolve_thumbnail_or_default(ctx, project.cover, ThumbType.COVER)

    base_context = ProjectPageContext(
        title=project.title,
        release_date=date_utils.format_nice_date(project.release_date) if ProjectField.RELEASE_DATE in visible else "",
        meta_entries=build_project_meta_entries(ctx, project),
        rel_thumbnail_path=path_utils.relative_path_from(thumb_path, ctx.output_dir).as_posix(),
        thumbnail_orientation=get_image_orientation(ctx, thumb_path),
        info_html=text_utils.markdown_to_html(project.info),
        tags=merge_tag_maps(project.tags),
        media_groups=build_media_group_contexts(ctx, project.media_groups),
    )

    if creator.type == CreatorType.COLLABORATION:
        return replace(
            base_context,
            participants=_collect_participant_entries(ctx, creator, project, get_creator),
            collaboration=_collect_collaborator_entry(ctx, creator),
        )

    return replace(
        base_context,
        creator=_collect_creator_entry(ctx, creator, project),
    )


def build_creator_page_context(
    ctx: HtmlBuildContext,
    creator: CreatorModel,
    get_creator: CreatorLoader,
    creator_stats: CreatorStats,
) -> CreatorPageContext:
    thumb_path = resolve_thumbnail_or_default(ctx, creator.portrait, ThumbType.PORTRAIT)

    base_context = CreatorPageContext(
        type=creator.type.value,
        name=creator.name,
        rel_portrait_path=path_utils.relative_path_from(thumb_path, ctx.output_dir).as_posix(),
        portrait_orientation=get_image_orientation(ctx, thumb_path),
        info_html=text_utils.markdown_to_html(creator.info),
        tags=merge_tag_maps(
            collect_tags_from_creator(creator),
            collect_project_metadata_tags(ctx, creator),
        ),
        projects=_build_project_cards(ctx, creator),
        media_groups=build_media_group_contexts(ctx, creator.media_groups),
        collaborations=_build_collaboration_entries(ctx, creator, get_creator),
        creator_stats=creator_stats,
        meta_entries=[],
    )

    if creator.type == CreatorType.COLLABORATION:
        visible = ctx.visible_collaboration_fields
        return replace(
            base_context,
            aliases=creator.aliases if CollaborationField.ALIASES in visible else [],
            nationalities=creator.nationalities if CollaborationField.NATIONALITIES in visible else [],
            active_since=date_utils.format_nice_date(creator.active_since) if CollaborationField.ACTIVE_SINCE in visible else "",
            members=_collect_member_links(ctx, creator, get_creator),
            member_names=creator.members if CollaborationField.MEMBERS in visible else [],
            founding_date=date_utils.format_nice_date(creator.founding_date) if CollaborationField.FOUNDING_DATE in visible else "",
            founding_location=creator.founding_location if CollaborationField.FOUNDING_LOCATION in visible else "",
            dissolution_date=date_utils.format_nice_date(creator.dissolution_date) if CollaborationField.DISSOLUTION_DATE in visible else "",
            meta_entries=build_collaboration_meta_entries(ctx, creator, visible, "", INDEX_HTML_FILE_NAME),
        )

    visible = ctx.visible_creator_fields
    raw_age = calculate_debut_age(creator) if CreatorField.DEBUT_AGE in visible else None

    return replace(
        base_context,
        aliases=creator.aliases if CreatorField.ALIASES in visible else [],
        nationalities=creator.nationalities if CreatorField.NATIONALITIES in visible else [],
        active_since=date_utils.format_nice_date(creator.active_since) if CreatorField.ACTIVE_SINCE in visible else "",
        civil_name=creator.civil_name if CreatorField.CIVIL_NAME in visible else "",
        date_of_birth=date_utils.format_nice_date(creator.date_of_birth) if CreatorField.DATE_OF_BIRTH in visible else "",
        place_of_birth=creator.place_of_birth if CreatorField.PLACE_OF_BIRTH in visible else "",
        date_of_death=date_utils.format_nice_date(creator.date_of_death) if CreatorField.DATE_OF_DEATH in visible else "",
        place_of_death=creator.place_of_death if CreatorField.PLACE_OF_DEATH in visible else "",
        debut_age=date_utils.format_age(raw_age),
        meta_entries=build_creator_meta_entries(ctx, creator, visible, "", INDEX_HTML_FILE_NAME),
    )


def _collect_participant_entries(
    ctx: HtmlBuildContext,
    creator: CreatorModel,
    project: ProjectModel,
    get_creator: CreatorLoader,
) -> list[CreatorProfileContext]:
    participants = []
    for name in creator.members:
        participant = get_creator(name)
        if not participant:
            logger.debug(f"Missing creator reference: {name}")
            continue
        participants.append(_collect_creator_entry(ctx, participant, project))
    return participants


def _collect_creator_base_entry(ctx: HtmlBuildContext, creator: CreatorModel) -> CreatorProfileContext:
    thumb_path = resolve_thumbnail_or_default(ctx, creator.portrait, ThumbType.PORTRAIT)

    return CreatorProfileContext(
        name=creator.name,
        rel_html_path=(Path(ctx.html_dir.name) / build_rel_creator_html_path(creator)).as_posix(),
        rel_portrait_path=path_utils.relative_path_from(thumb_path, ctx.output_dir).as_posix(),
    )


def _collect_creator_entry(
    ctx: HtmlBuildContext,
    creator: CreatorModel,
    project: ProjectModel,
) -> CreatorProfileContext:
    base = _collect_creator_base_entry(ctx, creator)
    return replace(
        base,
        age_at_release=calculate_age_at_release(creator, project),
        meta_entries=build_project_creator_meta_entries(
            ctx,
            creator,
            ctx.visible_project_creator_fields,
            project,
            base.rel_html_path,
            INDEX_HTML_FILE_NAME,
        ),
    )


def _collect_collaborator_entry(ctx: HtmlBuildContext, creator: CreatorModel) -> CreatorProfileContext:
    base = _collect_creator_base_entry(ctx, creator)
    return replace(
        base,
        meta_entries=build_collaboration_meta_entries(
            ctx,
            creator,
            ctx.visible_project_collaboration_fields,
            base.rel_html_path,
            INDEX_HTML_FILE_NAME,
        ),
    )


def _get_collaboration_label(collab: CreatorModel, creator_name: str) -> str:
    if creator_name in collab.members:
        others = [n for n in collab.members if n != creator_name]
        return " ".join(others)
    return collab.name


def _build_project_cards(ctx: HtmlBuildContext, creator: CreatorModel) -> list[ProjectCardContext]:
    project_cards = []
    for project in sorted(creator.projects, key=sort_project):
        thumb = build_thumbnail_context(ctx, project.cover, ThumbType.CREATOR_PAGE_PROJECT)
        project_cards.append(
            ProjectCardContext(
                title=project.title,
                rel_html_path=(Path(ctx.html_dir.name) / build_rel_project_html_path(creator, project)).as_posix(),
                rel_thumbnail_path=thumb.rel_thumbnail_path,
                image_wrapper_width=thumb.image_wrapper_width,
                image_wrapper_height=thumb.image_wrapper_height,
                media_counts=count_media_groups(project.media_groups),
            )
        )
    return project_cards


def _build_collaboration_entries(
    ctx: HtmlBuildContext,
    creator: CreatorModel,
    get_creator: CreatorLoader,
) -> list[CollaborationProjectsContext]:
    collab_entries = []
    for collab_name in creator.collaborations:
        collab = get_creator(collab_name)
        if not collab:
            logger.warning(f"Missing creator reference: {collab_name}")
            continue

        collab_entries.append(
            CollaborationProjectsContext(
                label=_get_collaboration_label(collab, creator.name),
                projects=_build_project_cards(ctx, collab),
            )
        )

    return collab_entries


def _collect_member_links(
    ctx: HtmlBuildContext,
    creator: CreatorModel,
    get_creator: CreatorLoader,
) -> list[CreatorLinkContext]:
    if creator.type != CreatorType.COLLABORATION:
        return []

    member_links = []

    for member_name in creator.members:
        member = get_creator(member_name)
        if not member:
            logger.debug(f"Missing creator reference: {member_name}")
            continue

        thumb_path = resolve_thumbnail_or_default(ctx, member.portrait, ThumbType.PORTRAIT)
        member_links.append(
            CreatorLinkContext(
                name=member_name,
                rel_html_path=(Path(ctx.html_dir.name) / build_rel_creator_html_path(member)).as_posix(),
                rel_thumbnail_path=path_utils.relative_path_from(thumb_path, ctx.output_dir).as_posix(),
            )
        )

    return member_links
