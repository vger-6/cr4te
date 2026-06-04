from __future__ import annotations

from collections.abc import Iterable, Mapping

from .html_context import HtmlBuildContext
from .enums.visible_fields import ProjectField
from .library_index import CreatorSummary, ProjectSummary
from .render_metadata import project_metadata_values
from .render_models import TagCollection, TagGroup
from .schemas.library_schema import Creator as CreatorModel

__all__ = [
    "RawTagMap",
    "TagSource",
    "build_tag_search_terms",
    "collect_project_metadata_tags",
    "collect_project_metadata_tags_from_summary",
    "collect_tags_from_creator",
    "collect_tags_from_creator_summary",
    "merge_tag_maps",
    "project_summary_values",
]

RawTagMap = Mapping[str, Iterable[str]]
TagSource = RawTagMap | TagCollection


def merge_tag_maps(*tag_maps: TagSource) -> TagCollection:
    grouped: dict[str, set[str]] = {}

    for tag_map in tag_maps:
        for category, tags in _iter_tag_items(tag_map):
            category = category.strip()
            if not category:
                continue

            grouped.setdefault(category, set())
            for tag in tags:
                tag = tag.strip()
                if tag:
                    grouped[category].add(tag)

    return TagCollection(
        tuple(
            TagGroup(category=category, tags=tuple(sorted(tags)))
            for category, tags in sorted(grouped.items())
            if tags
        )
    )


def collect_tags_from_creator(creator: CreatorModel) -> TagCollection:
    return merge_tag_maps(
        creator.tags,
        *(project.tags for project in creator.projects),
    )


def collect_project_metadata_tags(ctx: HtmlBuildContext, creator: CreatorModel) -> TagCollection:
    return merge_tag_maps(
        *(
            {ctx.meta_filter_label(field): project_metadata_values(project, field)}
            for project in creator.projects
            for field in ctx.project_tag_fields
        )
    )


def collect_tags_from_creator_summary(creator: CreatorSummary) -> TagCollection:
    return merge_tag_maps(
        creator.tags,
        *(project.tags for project in creator.projects),
    )


def collect_project_metadata_tags_from_summary(ctx: HtmlBuildContext, creator: CreatorSummary) -> TagCollection:
    return merge_tag_maps(
        *(
            {ctx.meta_filter_label(field): project_summary_values(project, field)}
            for project in creator.projects
            for field in ctx.project_tag_fields
        )
    )


def build_tag_search_terms(tag_map: TagSource) -> list[str]:
    return [
        f"{group.category}:{tag}"
        for group in merge_tag_maps(tag_map).groups
        for tag in group.tags
    ]


def project_summary_values(project: ProjectSummary, field: ProjectField) -> list[str]:
    for facet_field, values in project.facets.items():
        if isinstance(facet_field, ProjectField) and facet_field is field:
            return values
    return []


def _iter_tag_items(tag_map: TagSource) -> Iterable[tuple[str, Iterable[str]]]:
    if isinstance(tag_map, TagCollection):
        return ((group.category, group.tags) for group in tag_map.groups)

    return tag_map.items()
