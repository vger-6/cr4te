from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from .enums.visible_fields import CollaborationField, CreatorField, ProjectField

__all__ = [
    "CORE_META_FIELD_SPECS",
    "LabelPair",
    "MetaField",
    "MetaFieldSpec",
    "MetadataLabelKey",
    "get_core_meta_field",
]

MetaField = CollaborationField | CreatorField | ProjectField


class MetadataLabelKey(str, Enum):
    TITLE = "title"
    RELEASE_DATE = "release_date"
    NAME = "name"
    MEMBERS = "members"
    DATE_OF_BIRTH = "date_of_birth"
    PLACE_OF_BIRTH = "place_of_birth"
    DATE_OF_DEATH = "date_of_death"
    PLACE_OF_DEATH = "place_of_death"
    NATIONALITY = "nationality"
    NATIONALITIES = "nationalities"
    CIVIL_NAME = "civil_name"
    ALIAS = "alias"
    ALIASES = "aliases"
    DEBUT_AGE = "debut_age"
    AGE_AT_TIME = "age_at_time"
    ACTIVE_SINCE = "active_since"
    FOUNDING_DATE = "founding_date"
    FOUNDING_LOCATION = "founding_location"
    DISSOLUTION_DATE = "dissolution_date"


@dataclass(frozen=True)
class LabelPair:
    singular: MetadataLabelKey
    plural: MetadataLabelKey

    def resolve(self, labels: Any, count: int | None = None) -> str:
        key = self.singular if count == 1 else self.plural
        return getattr(labels.metadata, key.value)


@dataclass(frozen=True)
class MetaFieldSpec:
    field: MetaField
    labels: LabelPair

    def resolve_label(self, labels: Any, count: int | None = None) -> str:
        return self.labels.resolve(labels, count)


def _single(label: MetadataLabelKey) -> LabelPair:
    return LabelPair(label, label)


CORE_META_FIELD_SPECS: tuple[MetaFieldSpec, ...] = (
    MetaFieldSpec(ProjectField.TITLE, _single(MetadataLabelKey.TITLE)),
    MetaFieldSpec(ProjectField.RELEASE_DATE, _single(MetadataLabelKey.RELEASE_DATE)),
    MetaFieldSpec(CreatorField.NAME, _single(MetadataLabelKey.NAME)),
    MetaFieldSpec(CreatorField.DATE_OF_BIRTH, _single(MetadataLabelKey.DATE_OF_BIRTH)),
    MetaFieldSpec(CreatorField.PLACE_OF_BIRTH, _single(MetadataLabelKey.PLACE_OF_BIRTH)),
    MetaFieldSpec(CreatorField.DATE_OF_DEATH, _single(MetadataLabelKey.DATE_OF_DEATH)),
    MetaFieldSpec(CreatorField.PLACE_OF_DEATH, _single(MetadataLabelKey.PLACE_OF_DEATH)),
    MetaFieldSpec(CreatorField.NATIONALITIES, LabelPair(MetadataLabelKey.NATIONALITY, MetadataLabelKey.NATIONALITIES)),
    MetaFieldSpec(CreatorField.CIVIL_NAME, _single(MetadataLabelKey.CIVIL_NAME)),
    MetaFieldSpec(CreatorField.ALIASES, LabelPair(MetadataLabelKey.ALIAS, MetadataLabelKey.ALIASES)),
    MetaFieldSpec(CreatorField.DEBUT_AGE, _single(MetadataLabelKey.DEBUT_AGE)),
    MetaFieldSpec(CreatorField.AGE_AT_TIME, _single(MetadataLabelKey.AGE_AT_TIME)),
    MetaFieldSpec(CreatorField.ACTIVE_SINCE, _single(MetadataLabelKey.ACTIVE_SINCE)),
    MetaFieldSpec(CollaborationField.NAME, _single(MetadataLabelKey.NAME)),
    MetaFieldSpec(
        CollaborationField.NATIONALITIES,
        LabelPair(MetadataLabelKey.NATIONALITY, MetadataLabelKey.NATIONALITIES),
    ),
    MetaFieldSpec(CollaborationField.ALIASES, LabelPair(MetadataLabelKey.ALIAS, MetadataLabelKey.ALIASES)),
    MetaFieldSpec(CollaborationField.ACTIVE_SINCE, _single(MetadataLabelKey.ACTIVE_SINCE)),
    MetaFieldSpec(CollaborationField.MEMBERS, _single(MetadataLabelKey.MEMBERS)),
    MetaFieldSpec(CollaborationField.FOUNDING_DATE, _single(MetadataLabelKey.FOUNDING_DATE)),
    MetaFieldSpec(CollaborationField.FOUNDING_LOCATION, _single(MetadataLabelKey.FOUNDING_LOCATION)),
    MetaFieldSpec(CollaborationField.DISSOLUTION_DATE, _single(MetadataLabelKey.DISSOLUTION_DATE)),
)

_CORE_META_FIELD_BY_FIELD = {spec.field: spec for spec in CORE_META_FIELD_SPECS}


def get_core_meta_field(field: MetaField) -> MetaFieldSpec | None:
    return _CORE_META_FIELD_BY_FIELD.get(field)
