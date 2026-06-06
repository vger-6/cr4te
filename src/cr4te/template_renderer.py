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
from .render_models import (
    CreatorOverviewEntry,
    CreatorPageContext,
    NavigationItem,
    PageShellContext,
    ProjectOverviewEntry,
    ProjectPageContext,
)
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


def _page_shell_context(
    ctx: HtmlBuildContext,
    title: str,
    layout_stylesheet: str,
    path_to_root: str = "",
    current_navigation: str | None = None,
    extra_navigation_items: tuple[NavigationItem, ...] = (),
) -> PageShellContext:
    return PageShellContext(
        title=title,
        layout_stylesheet=layout_stylesheet,
        navigation_items=(
            NavigationItem(
                ctx.site_labels.entity.creators,
                f"{path_to_root}index.html",
                current_navigation == "creators",
            ),
            NavigationItem(
                ctx.site_labels.entity.projects,
                f"{path_to_root}projects.html",
                current_navigation == "projects",
            ),
            NavigationItem(
                ctx.site_labels.entity.tags,
                f"{path_to_root}tags.html",
                current_navigation == "tags",
            ),
            *extra_navigation_items,
        ),
    )


def render_project_overview_page(ctx: HtmlBuildContext, project_entries: list[ProjectOverviewEntry]) -> None:
    logger.info("Generating project overview page...")

    template = env.get_template("project_overview.html.j2")
    rendered = template.render(
        projects=project_entries,
        site_labels=ctx.site_labels,
        site_rendering=ctx.site_rendering,
        gallery_image_max_height=ctx.get_display_image_max_height(ThumbType.PROJECT_OVERVIEW),
        ImageGalleryBuildingStrategy=ImageGalleryBuildingStrategy,
        page_shell=_page_shell_context(
            ctx,
            ctx.site_labels.entity.projects,
            "overview-layout.css",
            current_navigation="projects",
        ),
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
        page_shell=_page_shell_context(
            ctx,
            ctx.site_labels.entity.tags,
            "overview-layout.css",
            current_navigation="tags",
        ),
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
    path_to_root = build_path_to_root(page_path, ctx.output_dir)
    creator_base = page_context.creator or page_context.collaboration
    extra_navigation_items = (
        NavigationItem(creator_base.name, f"{path_to_root}{creator_base.rel_html_path}"),
    ) if creator_base else ()
    template = env.get_template("project.html.j2")
    rendered = template.render(
        site_labels=ctx.site_labels,
        site_rendering=ctx.site_rendering,
        project=page_context,
        gallery_image_max_height=ctx.get_display_image_max_height(ThumbType.GALLERY),
        path_to_root=path_to_root,
        page_shell=_page_shell_context(
            ctx,
            page_context.title,
            "two-column-layout.css",
            path_to_root,
            extra_navigation_items=extra_navigation_items,
        ),
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
    path_to_root = build_path_to_root(page_path, ctx.output_dir)
    template = env.get_template("creator.html.j2")
    rendered = template.render(
        site_labels=ctx.site_labels,
        site_rendering=ctx.site_rendering,
        creator=page_context,
        project_image_max_height=ctx.get_display_image_max_height(ThumbType.CREATOR_PAGE_PROJECT),
        gallery_image_max_height=ctx.get_display_image_max_height(ThumbType.GALLERY),
        path_to_root=path_to_root,
        ImageGalleryBuildingStrategy=ImageGalleryBuildingStrategy,
        page_shell=_page_shell_context(
            ctx,
            page_context.name,
            "two-column-layout.css",
            path_to_root,
        ),
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
        page_shell=_page_shell_context(
            ctx,
            ctx.site_labels.entity.creators,
            "overview-layout.css",
            current_navigation="creators",
        ),
        **_theme_render_context(ctx),
    )

    with open(ctx.index_html_path, "w", encoding="utf-8") as file:
        file.write(rendered)
