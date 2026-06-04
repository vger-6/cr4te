import logging
from pathlib import Path
from typing import Callable, Optional

from .html_context import HtmlBuildContext
from .enums.visible_fields import CreatorField
from .library_index import CreatorSummary, LibraryIndex
from .output_preparation import copy_static_assets, prepare_output_dirs
from .overview_contexts import (
    build_creator_overview_entry_from_index,
    build_project_overview_entry_from_index,
    sort_project_summary,
)
from .page_contexts import (
    build_creator_page_context,
    build_project_page_context,
    compute_creator_stats,
    sort_project,
)
from .render_assets import prepare_default_thumbnails
from .render_models import CreatorOverviewEntry, ProjectOverviewEntry, TagCollection
from .schemas.config_schema import SiteLabels, SiteRendering
from .schemas.library_schema import Creator as CreatorModel
from .tag_contexts import collect_project_metadata_tags_from_summary, collect_tags_from_creator_summary, merge_tag_maps
from .template_renderer import (
    render_creator_overview_page,
    render_creator_page,
    render_project_overview_page,
    render_project_page,
    render_tags_page,
)

__all__ = ["build_html_pages_streaming"]

logger = logging.getLogger(__name__)


def build_html_pages_streaming(
    index: LibraryIndex,
    output_dir: Path,
    site_labels: SiteLabels,
    site_rendering: SiteRendering,
    load_creator: Callable[[CreatorSummary], CreatorModel],
) -> Path:
    ctx = HtmlBuildContext(index.input_dir, output_dir, site_labels, site_rendering)

    prepare_output_dirs(ctx)
    copy_static_assets(ctx)
    prepare_default_thumbnails(ctx)

    summary_by_name = index.creator_by_name

    def get_creator(name: str) -> Optional[CreatorModel]:
        summary = summary_by_name.get(name)
        return load_creator(summary) if summary else None

    creator_entries: list[CreatorOverviewEntry] = []
    project_entries: list[ProjectOverviewEntry] = []
    all_tags = TagCollection()

    for summary in sorted(index.creators, key=lambda c: c.name.lower()):
        creator = load_creator(summary)
        logger.info(f"Building creator page: {creator.name}")
        creator_stats = compute_creator_stats(creator)
        creator_context = build_creator_page_context(ctx, creator, get_creator, creator_stats)
        render_creator_page(ctx, creator, creator_context)

        for project in sorted(creator.projects, key=sort_project):
            logger.info(f"Building project page: {creator.name} - {project.title}")
            project_context = build_project_page_context(ctx, creator, project, get_creator)
            render_project_page(ctx, creator, project, project_context)

        creator_entries.append(build_creator_overview_entry_from_index(ctx, summary))
        for project in sorted(summary.projects, key=sort_project_summary):
            project_entries.append(build_project_overview_entry_from_index(ctx, summary, project))

        project_metadata_tags = collect_project_metadata_tags_from_summary(ctx, summary)
        all_tags = merge_tag_maps(
            all_tags,
            collect_tags_from_creator_summary(summary),
            project_metadata_tags,
            {ctx.meta_filter_label(CreatorField.NATIONALITIES): list(summary.nationalities)},
        )

    creator_entries.sort(key=lambda e: e.name.lower())
    project_entries.sort(key=lambda e: (e.title.lower(), e.creator_name.lower()))

    render_creator_overview_page(ctx, creator_entries)
    render_project_overview_page(ctx, project_entries)
    render_tags_page(ctx, all_tags)

    return ctx.index_html_path
