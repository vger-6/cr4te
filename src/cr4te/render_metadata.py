from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Optional
from urllib.parse import quote

from .constants import PROJECTS_HTML_FILE_NAME
from .html_context import HtmlBuildContext
from .enums.creator_type import CreatorType
from .enums.visible_fields import CollaborationField, CreatorField, ProjectField
from .render_models import MetaEntry
from .schemas.library_schema import Creator as CreatorModel, Project as ProjectModel
from .utils import date_utils

__all__ = [
    "build_collaboration_meta_entries",
    "build_creator_meta_entries",
    "build_filter_search_terms",
    "build_project_creator_meta_entries",
    "build_project_meta_entries",
    "calculate_age_at_release",
    "calculate_debut_age",
    "project_metadata_values",
]

CreatorValueGetter = Callable[[CreatorModel, Optional[ProjectModel]], list[str]]


@dataclass(frozen=True)
class CreatorMetaEntrySpec:
    field: CreatorField
    values: CreatorValueGetter
    separator: str = ", "
    filterable: bool = False
    links_to_creator: bool = False


@dataclass(frozen=True)
class CollaborationMetaEntrySpec:
    field: CollaborationField
    values: CreatorValueGetter
    separator: str = ", "
    filterable: bool = False
    links_to_creator: bool = False


@dataclass(frozen=True)
class EventMetaEntrySpec:
    field: CreatorField | CollaborationField
    date_values: CreatorValueGetter
    place_values: CreatorValueGetter


def build_project_meta_entries(ctx: HtmlBuildContext, project: ProjectModel) -> list[MetaEntry]:
    entries: list[MetaEntry] = []

    for field in ctx.visible_project_fields:
        if field == ProjectField.TITLE:
            _append_meta_entry(entries, ctx.meta_label(field), [project.display_title])
            continue

        if field == ProjectField.RELEASE_DATE:
            _append_meta_entry(entries, ctx.meta_label(field), [date_utils.format_nice_date(project.release_date)])
            continue

        if field not in project.facets:
            continue

        values = project_metadata_values(project, field)
        label = ctx.meta_label(field, _count_meta_values(values))
        separator = ctx.project_metadata_separator(field)
        if ctx.project_metadata_is_clickable(field):
            _append_filter_meta_entry(
                entries,
                label,
                values,
                PROJECTS_HTML_FILE_NAME,
                separator=separator,
                filter_label=ctx.meta_filter_label(field),
            )
        else:
            _append_meta_entry(entries, label, values, separator=separator)

    return entries


def build_creator_meta_entries(
    ctx: HtmlBuildContext,
    creator: CreatorModel,
    visible_fields: list[CreatorField],
    rel_html_path: str,
    filter_page: str,
    project: ProjectModel | None = None,
) -> list[MetaEntry]:
    entries: list[MetaEntry] = []

    for field in visible_fields:
        event_spec = CREATOR_EVENT_ENTRY_SPECS.get(field)
        if event_spec:
            _append_event_meta_entry(entries, ctx, creator, event_spec, project)
            continue

        spec = CREATOR_META_ENTRY_SPECS[field]
        _append_spec_entry(entries, ctx, creator, project, spec, rel_html_path, filter_page)

    return entries


def build_project_creator_meta_entries(
    ctx: HtmlBuildContext,
    creator: CreatorModel,
    visible_fields: list[CreatorField],
    project: ProjectModel,
    rel_html_path: str,
    filter_page: str,
) -> list[MetaEntry]:
    return build_creator_meta_entries(ctx, creator, visible_fields, rel_html_path, filter_page, project)


def build_collaboration_meta_entries(
    ctx: HtmlBuildContext,
    creator: CreatorModel,
    visible_fields: list[CollaborationField],
    rel_html_path: str,
    filter_page: str,
    member_display_names: list[str] | None = None,
) -> list[MetaEntry]:
    entries: list[MetaEntry] = []

    for field in visible_fields:
        event_spec = COLLABORATION_EVENT_ENTRY_SPECS.get(field)
        if event_spec:
            _append_event_meta_entry(entries, ctx, creator, event_spec)
            continue

        spec = COLLABORATION_META_ENTRY_SPECS[field]
        if field == CollaborationField.MEMBERS and member_display_names is not None:
            _append_meta_entry(entries, ctx.meta_label(field, _count_meta_values(member_display_names)), member_display_names, separator=spec.separator)
            continue
        _append_spec_entry(entries, ctx, creator, None, spec, rel_html_path, filter_page)

    return entries


def project_metadata_values(project: ProjectModel, field: ProjectField) -> list[str]:
    return list(project.facets.get(field, []))


def build_filter_search_terms(label: str, values: list[str]) -> list[str]:
    return [
        f"{label}:{value.strip()}"
        for value in values
        if value and value.strip()
    ]


def calculate_age_at_release(creator: CreatorModel, project: ProjectModel) -> Optional[int]:
    if creator.type != CreatorType.PERSON:
        return None

    if not creator.date_of_birth or not project.release_date:
        return None

    return date_utils.calculate_age_from_strings(creator.date_of_birth, project.release_date)


def calculate_debut_age(creator: CreatorModel) -> Optional[int]:
    if not creator.date_of_birth:
        return None

    if creator.active_since:
        return date_utils.calculate_age_from_strings(creator.date_of_birth, creator.active_since)

    dates = [project.release_date for project in creator.projects if date_utils.parse_date(project.release_date)]
    if not dates:
        return None

    earliest = min(dates, key=lambda date: date_utils.parse_date(date) or datetime.max)
    return date_utils.calculate_age_from_strings(creator.date_of_birth, earliest)


def _build_metadata_filter_href(category: str, value: str, filter_page: str) -> str:
    return f"{filter_page}?tag={quote(f'{category}:{value.strip()}')}"


def _append_filter_meta_entry(
    entries: list[MetaEntry],
    label: str,
    values: list[str],
    filter_page: str,
    separator: str = ", ",
    filter_label: str | None = None,
) -> None:
    filter_label = filter_label or label
    hrefs = [
        _build_metadata_filter_href(filter_label, value, filter_page) if value and value.strip() else ""
        for value in values
    ]
    _append_meta_entry(entries, label, values, separator=separator, hrefs=hrefs)


def _append_meta_entry(
    entries: list[MetaEntry],
    label: str,
    values: list[str],
    separator: str = ", ",
    hrefs: list[str] | None = None,
) -> None:
    meta_values: list[str] = []
    entry_hrefs: list[str] = []
    hrefs = hrefs or []

    for index, value in enumerate(values):
        if not value:
            continue
        meta_values.append(value)
        entry_hrefs.append(hrefs[index] if index < len(hrefs) else "")

    if not meta_values:
        return

    entries.append(MetaEntry(label=label, values=meta_values, separator=separator, hrefs=entry_hrefs))


def _append_spec_entry(
    entries: list[MetaEntry],
    ctx: HtmlBuildContext,
    creator: CreatorModel,
    project: ProjectModel | None,
    spec: CreatorMetaEntrySpec | CollaborationMetaEntrySpec,
    rel_html_path: str,
    filter_page: str,
) -> None:
    values = spec.values(creator, project)
    label = ctx.meta_label(spec.field, _count_meta_values(values))

    if spec.filterable:
        _append_filter_meta_entry(
            entries,
            label,
            values,
            filter_page,
            separator=spec.separator,
            filter_label=ctx.meta_filter_label(spec.field),
        )
        return

    hrefs = [rel_html_path] if spec.links_to_creator and rel_html_path else None
    _append_meta_entry(entries, label, values, separator=spec.separator, hrefs=hrefs)


def _append_event_meta_entry(
    entries: list[MetaEntry],
    ctx: HtmlBuildContext,
    creator: CreatorModel,
    spec: EventMetaEntrySpec,
    project: ProjectModel | None = None,
) -> None:
    date = _first_meta_value(spec.date_values(creator, project))
    place = _first_meta_value(spec.place_values(creator, project))
    _append_meta_entry(
        entries,
        ctx.meta_label(spec.field),
        [ctx.format_date_and_place(date, place)],
    )


def _count_meta_values(values: list[str]) -> int:
    return sum(1 for value in values if value and value.strip())


def _first_meta_value(values: list[str]) -> str:
    return next((value for value in values if value and value.strip()), "")


def _creator_name(creator: CreatorModel, project: ProjectModel | None) -> list[str]:
    return [creator.display_name]


def _birth_date(creator: CreatorModel, project: ProjectModel | None) -> list[str]:
    return [date_utils.format_nice_date(creator.date_of_birth)]


def _birth_place(creator: CreatorModel, project: ProjectModel | None) -> list[str]:
    return [creator.place_of_birth]


def _death_date(creator: CreatorModel, project: ProjectModel | None) -> list[str]:
    return [date_utils.format_nice_date(creator.date_of_death)]


def _death_place(creator: CreatorModel, project: ProjectModel | None) -> list[str]:
    return [creator.place_of_death]


def _nationalities(creator: CreatorModel, project: ProjectModel | None) -> list[str]:
    return creator.nationalities


def _civil_name(creator: CreatorModel, project: ProjectModel | None) -> list[str]:
    return [creator.civil_name]


def _aliases(creator: CreatorModel, project: ProjectModel | None) -> list[str]:
    return creator.aliases


def _debut_age(creator: CreatorModel, project: ProjectModel | None) -> list[str]:
    return [date_utils.format_age(calculate_debut_age(creator))]


def _age_at_release(creator: CreatorModel, project: ProjectModel | None) -> list[str]:
    if project is None:
        return []
    return [date_utils.format_age(calculate_age_at_release(creator, project))]


def _active_since(creator: CreatorModel, project: ProjectModel | None) -> list[str]:
    return [date_utils.format_nice_date(creator.active_since)]


def _members(creator: CreatorModel, project: ProjectModel | None) -> list[str]:
    return creator.members


def _founding_date(creator: CreatorModel, project: ProjectModel | None) -> list[str]:
    return [date_utils.format_nice_date(creator.founding_date)]


def _founding_location(creator: CreatorModel, project: ProjectModel | None) -> list[str]:
    return [creator.founding_location]


def _dissolution_date(creator: CreatorModel, project: ProjectModel | None) -> list[str]:
    return [date_utils.format_nice_date(creator.dissolution_date)]


CREATOR_META_ENTRY_SPECS: dict[CreatorField, CreatorMetaEntrySpec] = {
    CreatorField.NAME: CreatorMetaEntrySpec(CreatorField.NAME, _creator_name, links_to_creator=True),
    CreatorField.NATIONALITIES: CreatorMetaEntrySpec(CreatorField.NATIONALITIES, _nationalities, filterable=True),
    CreatorField.CIVIL_NAME: CreatorMetaEntrySpec(CreatorField.CIVIL_NAME, _civil_name),
    CreatorField.ALIASES: CreatorMetaEntrySpec(CreatorField.ALIASES, _aliases, separator="<br>"),
    CreatorField.DEBUT_AGE: CreatorMetaEntrySpec(CreatorField.DEBUT_AGE, _debut_age),
    CreatorField.AGE_AT_TIME: CreatorMetaEntrySpec(CreatorField.AGE_AT_TIME, _age_at_release),
    CreatorField.ACTIVE_SINCE: CreatorMetaEntrySpec(CreatorField.ACTIVE_SINCE, _active_since),
}

COLLABORATION_META_ENTRY_SPECS: dict[CollaborationField, CollaborationMetaEntrySpec] = {
    CollaborationField.NAME: CollaborationMetaEntrySpec(CollaborationField.NAME, _creator_name, links_to_creator=True),
    CollaborationField.NATIONALITIES: CollaborationMetaEntrySpec(CollaborationField.NATIONALITIES, _nationalities, filterable=True),
    CollaborationField.ALIASES: CollaborationMetaEntrySpec(CollaborationField.ALIASES, _aliases, separator="<br>"),
    CollaborationField.ACTIVE_SINCE: CollaborationMetaEntrySpec(CollaborationField.ACTIVE_SINCE, _active_since),
    CollaborationField.MEMBERS: CollaborationMetaEntrySpec(CollaborationField.MEMBERS, _members, separator="<br>"),
    CollaborationField.DISSOLUTION_DATE: CollaborationMetaEntrySpec(CollaborationField.DISSOLUTION_DATE, _dissolution_date),
}

CREATOR_EVENT_ENTRY_SPECS: dict[CreatorField, EventMetaEntrySpec] = {
    CreatorField.BIRTH: EventMetaEntrySpec(
        field=CreatorField.BIRTH,
        date_values=_birth_date,
        place_values=_birth_place,
    ),
    CreatorField.DEATH: EventMetaEntrySpec(
        field=CreatorField.DEATH,
        date_values=_death_date,
        place_values=_death_place,
    ),
}

COLLABORATION_EVENT_ENTRY_SPECS: dict[CollaborationField, EventMetaEntrySpec] = {
    CollaborationField.FOUNDING: EventMetaEntrySpec(
        field=CollaborationField.FOUNDING,
        date_values=_founding_date,
        place_values=_founding_location,
    ),
}
