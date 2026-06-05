from __future__ import annotations

import logging

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .constants import CR4TE_TEMPLATES_DIR
from .html_context import HtmlBuildContext
from .enums.image_gallery_building_strategy import ImageGalleryBuildingStrategy
from .enums.media_type import MediaType
from .enums.thumb_type import ThumbType
from .html_paths import (
    build_path_to_root,
    build_rel_creator_html_path,
    build_rel_project_html_path,
)
from .render_models import CreatorOverviewEntry, CreatorPageContext, ProjectOverviewEntry, ProjectPageContext
from .schemas.library_schema import Creator as CreatorModel, Project as ProjectModel
from .tag_contexts import TagSource, merge_tag_maps

__all__ = [
    "render_creator_overview_page",
    "render_creator_page",
    "render_project_overview_page",
    "render_project_page",
    "render_tags_page",
]

logger = logging.getLogger(__name__)

env = Environment(
    loader=FileSystemLoader(str(CR4TE_TEMPLATES_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)
env.globals["MediaType"] = MediaType


def _theme_render_context(ctx: HtmlBuildContext) -> dict:
    return {
        "themes": ctx.themes,
        "default_theme": ctx.default_theme,
    }


def render_project_overview_page(ctx: HtmlBuildContext, project_entries: list[ProjectOverviewEntry]) -> None:
    logger.info("Generating project overview page...")

    template = env.get_template("project_overview.html.j2")
    rendered = template.render(
        projects=project_entries,
        site_labels=ctx.site_labels,
        site_rendering=ctx.site_rendering,
        gallery_image_max_height=ctx.get_display_image_max_height(ThumbType.PROJECT_OVERVIEW),
        ImageGalleryBuildingStrategy=ImageGalleryBuildingStrategy,
        **_theme_render_context(ctx),
    )

    with open(ctx.projects_html_path, "w", encoding="utf-8") as file:
        file.write(rendered)


def render_tags_page(ctx: HtmlBuildContext, tags: TagSource) -> None:
    logger.info("Generating tags page...")

    template = env.get_template("tags.html.j2")
    rendered = template.render(
        site_labels=ctx.site_labels,
        site_rendering=ctx.site_rendering,
        tags=merge_tag_maps(tags),
        **_theme_render_context(ctx),
    )

    with open(ctx.tags_html_path, "w", encoding="utf-8") as file:
        file.write(rendered)


def render_project_page(
    ctx: HtmlBuildContext,
    creator: CreatorModel,
    project: ProjectModel,
    page_context: ProjectPageContext,
) -> None:
    page_path = ctx.html_dir / build_rel_project_html_path(creator, project)
    template = env.get_template("project.html.j2")
    rendered = template.render(
        site_labels=ctx.site_labels,
        site_rendering=ctx.site_rendering,
        project=page_context,
        gallery_image_max_height=ctx.get_display_image_max_height(ThumbType.GALLERY),
        path_to_root=build_path_to_root(page_path, ctx.output_dir),
        **_theme_render_context(ctx),
    )

    page_path.parent.mkdir(parents=True, exist_ok=True)
    with open(page_path, "w", encoding="utf-8") as file:
        file.write(rendered)


def render_creator_page(
    ctx: HtmlBuildContext,
    creator: CreatorModel,
    page_context: CreatorPageContext,
) -> None:
    page_path = ctx.html_dir / build_rel_creator_html_path(creator)
    template = env.get_template("creator.html.j2")
    rendered = template.render(
        site_labels=ctx.site_labels,
        site_rendering=ctx.site_rendering,
        creator=page_context,
        project_image_max_height=ctx.get_display_image_max_height(ThumbType.CREATOR_PAGE_PROJECT),
        gallery_image_max_height=ctx.get_display_image_max_height(ThumbType.GALLERY),
        path_to_root=build_path_to_root(page_path, ctx.output_dir),
        ImageGalleryBuildingStrategy=ImageGalleryBuildingStrategy,
        **_theme_render_context(ctx),
    )

    page_path.parent.mkdir(parents=True, exist_ok=True)
    with open(page_path, "w", encoding="utf-8") as file:
        file.write(rendered)


def render_creator_overview_page(ctx: HtmlBuildContext, creator_entries: list[CreatorOverviewEntry]) -> None:
    logger.info("Generating overview page...")

    template = env.get_template("creator_overview.html.j2")
    rendered = template.render(
        site_labels=ctx.site_labels,
        site_rendering=ctx.site_rendering,
        creator_entries=creator_entries,
        gallery_image_max_height=ctx.get_display_image_max_height(ThumbType.CREATOR_OVERVIEW),
        ImageGalleryBuildingStrategy=ImageGalleryBuildingStrategy,
        **_theme_render_context(ctx),
    )

    with open(ctx.index_html_path, "w", encoding="utf-8") as file:
        file.write(rendered)
