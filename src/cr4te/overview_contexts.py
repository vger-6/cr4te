from __future__ import annotations

from pathlib import Path

from .html_context import HtmlBuildContext
from .enums.portrait_visibility import PortraitVisibility
from .enums.thumb_type import ThumbType
from .enums.visible_fields import CreatorField
from .html_paths import build_rel_creator_html_path, build_rel_project_html_path
from .library_index import CreatorSummary, ProjectSummary
from .render_assets import build_thumbnail_context
from .render_metadata import build_filter_search_terms
from .render_models import CreatorOverviewEntry, ProjectOverviewEntry
from .tag_contexts import build_tag_search_terms, project_summary_values
from .utils.sorting_utils import dated_title_sort_key
from .utils import date_utils

__all__ = [
    "build_creator_overview_entry_from_index",
    "build_project_overview_entry_from_index",
    "sort_project_summary",
]


def sort_project_summary(project: ProjectSummary) -> tuple:
    return dated_title_sort_key(date_utils.parse_date(project.release_date), project.display_title)


def build_creator_overview_entry_from_index(ctx: HtmlBuildContext, creator: CreatorSummary) -> CreatorOverviewEntry:
    if ctx.site_rendering.portraits.visibility != PortraitVisibility.ALL:
        rel_thumbnail_path = ""
        image_wrapper_width = 0
        image_wrapper_height = 0
    else:
        thumb = build_thumbnail_context(ctx, creator.portrait, ThumbType.CREATOR_OVERVIEW)
        rel_thumbnail_path = thumb.rel_thumbnail_path
        image_wrapper_width = thumb.image_wrapper_width
        image_wrapper_height = thumb.image_wrapper_height

    return CreatorOverviewEntry(
        name=creator.display_name,
        rel_html_path=(Path(ctx.html_dir.name) / build_rel_creator_html_path(creator)).as_posix(),
        search_text=_build_creator_summary_search_text(ctx, creator),
        rel_thumbnail_path=rel_thumbnail_path,
        image_wrapper_width=image_wrapper_width,
        image_wrapper_height=image_wrapper_height,
        project_count=creator.project_count,
        media_counts=creator.media_counts,
        project_count_summary=_build_project_count_summary(ctx, creator),
        media_count_summary=_build_media_count_summary(ctx, creator),
    )


def build_project_overview_entry_from_index(
    ctx: HtmlBuildContext,
    creator: CreatorSummary,
    project: ProjectSummary,
) -> ProjectOverviewEntry:
    thumb = build_thumbnail_context(ctx, project.cover, ThumbType.PROJECT_OVERVIEW)
    return ProjectOverviewEntry(
        title=project.display_title,
        rel_html_path=(Path(ctx.html_dir.name) / build_rel_project_html_path(creator, project)).as_posix(),
        rel_thumbnail_path=thumb.rel_thumbnail_path,
        image_wrapper_width=thumb.image_wrapper_width,
        image_wrapper_height=thumb.image_wrapper_height,
        creator_name=creator.display_name,
        search_text=_build_project_summary_search_text(ctx, project, creator),
        media_counts=project.media_counts,
    )


def _build_creator_summary_search_text(ctx: HtmlBuildContext, creator: CreatorSummary) -> str:
    search_terms = [creator.display_name]
    search_terms.extend(alias.strip() for alias in creator.aliases if alias and alias.strip())
    search_terms.extend(build_tag_search_terms(creator.tags))
    search_terms.extend(build_filter_search_terms(ctx.meta_filter_label(CreatorField.NATIONALITIES), list(creator.nationalities)))

    for project in creator.projects:
        search_terms.append(project.display_title)
        search_terms.extend(build_tag_search_terms(project.tags))
        for field in ctx.project_searchable_fields:
            search_terms.extend(build_filter_search_terms(ctx.meta_filter_label(field), project_summary_values(project, field)))

    return " ".join(search_terms).lower()


def _build_project_count_summary(ctx: HtmlBuildContext, creator: CreatorSummary) -> str:
    if creator.project_count == 0:
        return ""
    label = ctx.site_labels.counts.project if creator.project_count == 1 else ctx.site_labels.counts.projects
    return f"{creator.project_count} {label}"


def _build_media_count_summary(ctx: HtmlBuildContext, creator: CreatorSummary) -> str:
    counts_and_labels = (
        (creator.media_counts.video, ctx.site_labels.media.video, ctx.site_labels.media.videos),
        (creator.media_counts.audio, ctx.site_labels.media.audio_track, ctx.site_labels.media.audio_tracks),
        (creator.media_counts.image, ctx.site_labels.media.image, ctx.site_labels.media.images),
        (creator.media_counts.document, ctx.site_labels.media.document, ctx.site_labels.media.documents),
        (creator.media_counts.text, ctx.site_labels.media.text_file, ctx.site_labels.media.text_files),
    )
    return " | ".join(
        f"{count} {singular if count == 1 else plural}"
        for count, singular, plural in counts_and_labels
        if count > 0
    )


def _build_project_summary_search_text(ctx: HtmlBuildContext, project: ProjectSummary, creator: CreatorSummary) -> str:
    search_terms = [project.display_title, creator.display_name]
    search_terms.extend(build_tag_search_terms(project.tags))

    for field in ctx.project_searchable_fields:
        search_terms.extend(build_filter_search_terms(ctx.meta_filter_label(field), project_summary_values(project, field)))

    return " ".join(search_terms).lower()
