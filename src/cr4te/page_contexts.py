from __future__ import annotations

import logging
from dataclasses import replace
from pathlib import Path
from typing import Callable, Optional

from .constants import INDEX_HTML_FILE_NAME
from .html_context import HtmlBuildContext
from .enums.creator_type import CreatorType
from .enums.portrait_visibility import PortraitVisibility
from .enums.thumb_type import ThumbType
from .enums.visible_fields import CreatorField, ProjectField
from .html_paths import build_rel_creator_html_path, build_rel_project_html_path
from .library_issues import invalid_collaboration_reference_issue
from .media_counts import count_media_groups
from .render_assets import build_thumbnail_context, get_image_orientation
from .render_media import build_media_group_contexts
from .render_metadata import (
    build_collaboration_meta_entries,
    build_creator_meta_entries,
    build_project_creator_meta_entries,
    build_project_meta_entries,
    calculate_age_at_release,
)
from .render_models import (
    CollaborationProjectsContext,
    CreatorLinkContext,
    CreatorPageContext,
    CreatorProfileContext,
    CreatorStats,
    MetaEntry,
    ProjectCardContext,
    ProjectPageContext,
    ThumbnailContext,
)
from .schemas.library_schema import Creator as CreatorModel, Project as ProjectModel
from .tag_contexts import (
    collect_project_metadata_tags,
    collect_tags_from_creator,
    merge_tag_maps,
)
from .utils.sorting_utils import dated_title_sort_key
from .utils import date_utils, text_utils

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
    return dated_title_sort_key(date_utils.parse_date(project.release_date), project.display_title)


def compute_creator_stats(creator: CreatorModel) -> CreatorStats:
    project_count = len(creator.projects)
    total_media_counts = count_media_groups(creator.media_groups)

    for project in creator.projects:
        total_media_counts = total_media_counts.add(count_media_groups(project.media_groups))

    return CreatorStats(project_count=project_count, media_counts=total_media_counts)


def _build_portrait_thumbnail(ctx: HtmlBuildContext, portrait: str) -> ThumbnailContext | None:
    visibility = ctx.site_rendering.portraits.visibility
    if visibility == PortraitVisibility.DISABLED:
        return None
    if visibility == PortraitVisibility.DETAILS and not portrait:
        return None
    return build_thumbnail_context(ctx, portrait, ThumbType.PORTRAIT)


def build_project_page_context(
    ctx: HtmlBuildContext,
    creator: CreatorModel,
    project: ProjectModel,
    get_creator: CreatorLoader,
) -> ProjectPageContext:
    visible = ctx.visible_project_fields
    thumbnail = build_thumbnail_context(ctx, project.cover, ThumbType.COVER)
    thumb_path = ctx.output_dir / thumbnail.rel_thumbnail_path

    base_context = ProjectPageContext(
        title=project.display_title,
        release_date=date_utils.format_nice_date(project.release_date) if ProjectField.RELEASE_DATE in visible else "",
        meta_entries=build_project_meta_entries(ctx, project),
        rel_thumbnail_path=thumbnail.rel_thumbnail_path,
        thumbnail_orientation=get_image_orientation(ctx, thumb_path),
        info_html=text_utils.markdown_to_html(project.info),
        tags=merge_tag_maps(project.tags),
        media_groups=build_media_group_contexts(ctx, project.media_groups),
    )

    if creator.type == CreatorType.COLLABORATION:
        return replace(
            base_context,
            participants=_collect_participant_entries(ctx, creator, project, get_creator),
            collaboration=_collect_collaborator_entry(ctx, creator, get_creator),
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
    thumbnail = _build_portrait_thumbnail(ctx, creator.portrait)
    if thumbnail is None:
        rel_portrait_path = ""
        portrait_orientation = None
    else:
        rel_portrait_path = thumbnail.rel_thumbnail_path
        portrait_orientation = get_image_orientation(ctx, ctx.output_dir / thumbnail.rel_thumbnail_path)

    base_context = CreatorPageContext(
        type=creator.type.value,
        name=creator.display_name,
        rel_portrait_path=rel_portrait_path,
        portrait_orientation=portrait_orientation,
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
        member_display_names = _display_member_names(creator, get_creator)
        return replace(
            base_context,
            members=_collect_member_links(ctx, creator, get_creator),
            meta_entries=build_collaboration_meta_entries(
                ctx,
                creator,
                visible,
                "",
                INDEX_HTML_FILE_NAME,
                member_display_names,
            ),
        )

    visible = ctx.visible_creator_fields

    return replace(
        base_context,
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
    thumbnail = _build_portrait_thumbnail(ctx, creator.portrait)

    return CreatorProfileContext(
        name=creator.display_name,
        rel_html_path=(Path(ctx.html_dir.name) / build_rel_creator_html_path(creator)).as_posix(),
        rel_portrait_path=thumbnail.rel_thumbnail_path if thumbnail else "",
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


def _collect_collaborator_entry(
    ctx: HtmlBuildContext,
    creator: CreatorModel,
    get_creator: CreatorLoader,
) -> CreatorProfileContext:
    base = _collect_creator_base_entry(ctx, creator)
    return replace(
        base,
        meta_entries=build_collaboration_meta_entries(
            ctx,
            creator,
            ctx.visible_project_collaboration_fields,
            base.rel_html_path,
            INDEX_HTML_FILE_NAME,
            _display_member_names(creator, get_creator),
        ),
    )


def _format_collaboration_members(names: list[str]) -> str:
    if not names:
        return ""
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f"{names[0]} & {names[1]}"
    return f"{', '.join(names[:-2])}, {names[-2]} & {names[-1]}"


def _get_collaboration_label(collab: CreatorModel, creator_name: str, get_creator: CreatorLoader) -> str:
    if creator_name in collab.members:
        others = [
            _display_creator_reference(name, get_creator)
            for name in collab.members
            if name != creator_name
        ]
        if others:
            return _format_collaboration_members(others)
        return collab.display_name
    return collab.display_name


def _build_project_cards(ctx: HtmlBuildContext, creator: CreatorModel) -> list[ProjectCardContext]:
    project_cards = []
    for project in sorted(creator.projects, key=sort_project):
        thumb = build_thumbnail_context(ctx, project.cover, ThumbType.CREATOR_PAGE_PROJECT)
        project_cards.append(
            ProjectCardContext(
                title=project.display_title,
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
            ctx.report_issue(
                invalid_collaboration_reference_issue(ctx.input_dir / creator.name, [collab_name]),
            )
            continue

        collab_entries.append(
            CollaborationProjectsContext(
                label=_get_collaboration_label(collab, creator.name, get_creator),
                projects=_build_project_cards(ctx, collab),
            )
        )

    return sorted(collab_entries, key=lambda entry: entry.label.lower())


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

        thumbnail = _build_portrait_thumbnail(ctx, member.portrait)
        rel_html_path = (Path(ctx.html_dir.name) / build_rel_creator_html_path(member)).as_posix()
        member_links.append(
            CreatorLinkContext(
                name=member.display_name,
                rel_thumbnail_path=thumbnail.rel_thumbnail_path if thumbnail else "",
                meta_entries=[
                    MetaEntry(
                        label=ctx.meta_label(CreatorField.NAME),
                        values=[member.display_name],
                        hrefs=[rel_html_path],
                    )
                ],
            )
        )

    return member_links


def _display_creator_reference(name: str, get_creator: CreatorLoader) -> str:
    creator = get_creator(name)
    return creator.display_name if creator else name


def _display_member_names(creator: CreatorModel, get_creator: CreatorLoader) -> list[str]:
    return [
        _display_creator_reference(member_name, get_creator)
        for member_name in creator.members
    ]
