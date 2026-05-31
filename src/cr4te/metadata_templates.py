from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .enums.creator_type import CreatorType
from .enums.visible_fields import ProjectField

JsonObject = dict[str, Any]

__all__ = [
    "CollaborationMetadataTemplate",
    "CreatorMetadataTemplate",
    "DatePlaceTemplate",
    "PersonMetadataTemplate",
    "ProjectMetadataTemplate",
]


@dataclass(frozen=True)
class DatePlaceTemplate:
    date: str = ""
    place: str = ""

    def as_json(self) -> JsonObject:
        return {
            "date": self.date,
            "place": self.place,
        }


@dataclass(frozen=True)
class PersonMetadataTemplate:
    active_since: str = ""
    birth: DatePlaceTemplate = field(default_factory=DatePlaceTemplate)
    death: DatePlaceTemplate = field(default_factory=DatePlaceTemplate)
    civil_name: str = ""
    nationalities: list[str] = field(default_factory=list)

    def as_json(self) -> JsonObject:
        return {
            "active_since": self.active_since,
            "birth": self.birth.as_json(),
            "death": self.death.as_json(),
            "civil_name": self.civil_name,
            "nationalities": list(self.nationalities),
        }


@dataclass(frozen=True)
class CollaborationMetadataTemplate:
    active_since: str = ""
    members: list[str] = field(default_factory=list)
    founding: DatePlaceTemplate = field(default_factory=DatePlaceTemplate)
    dissolution_date: str = ""
    nationalities: list[str] = field(default_factory=list)

    def as_json(self) -> JsonObject:
        return {
            "active_since": self.active_since,
            "members": list(self.members),
            "founding": self.founding.as_json(),
            "dissolution_date": self.dissolution_date,
            "nationalities": list(self.nationalities),
        }


@dataclass(frozen=True)
class ProjectMetadataTemplate:
    title: str
    cover: str = ""
    facet_fields: tuple[ProjectField, ...] = ()

    def as_json(self) -> JsonObject:
        return {
            "title": self.title,
            "release_date": "",
            "cover": self.cover,
            "tags": {},
            "facets": {
                field.value: []
                for field in self.facet_fields
            },
        }


@dataclass(frozen=True)
class CreatorMetadataTemplate:
    name: str
    type: CreatorType
    portrait: str = ""
    aliases: list[str] = field(default_factory=list)
    collaborations: list[str] = field(default_factory=list)
    tags: dict[str, list[str]] = field(default_factory=dict)
    person: PersonMetadataTemplate | None = None
    collaboration: CollaborationMetadataTemplate | None = None

    def as_json(self) -> JsonObject:
        data: JsonObject = {
            "name": self.name,
            "type": self.type.value,
            "portrait": self.portrait,
            "aliases": list(self.aliases),
            "collaborations": list(self.collaborations),
            "tags": {
                category: list(tags)
                for category, tags in self.tags.items()
            },
        }

        if self.type == CreatorType.COLLABORATION:
            data["collaboration"] = (self.collaboration or CollaborationMetadataTemplate()).as_json()
        else:
            data["person"] = (self.person or PersonMetadataTemplate()).as_json()

        return data
