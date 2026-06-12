from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..enums.creator_type import CreatorType
from ..enums.visible_fields import ProjectField
from ..utils.date_utils import normalize_optional_iso_date

TagMap = Dict[str, List[str]]
FacetMap = Dict[ProjectField, List[str]]


class DatePlaceMetadata(BaseModel):
    date: str = ""
    place: str = ""

    model_config = ConfigDict(extra="forbid")

    @field_validator("date", mode="before")
    @classmethod
    def validate_date(cls, value):
        return normalize_optional_iso_date(value)


class PersonMetadata(BaseModel):
    active_since: str = ""
    birth: DatePlaceMetadata = Field(default_factory=DatePlaceMetadata)
    death: DatePlaceMetadata = Field(default_factory=DatePlaceMetadata)
    civil_name: str = ""
    nationalities: List[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")

    @field_validator("active_since", mode="before")
    @classmethod
    def validate_active_since(cls, value):
        return normalize_optional_iso_date(value)


class CollaborationMetadata(BaseModel):
    active_since: str = ""
    members: List[str] = Field(default_factory=list)
    founding: DatePlaceMetadata = Field(default_factory=DatePlaceMetadata)
    dissolution_date: str = ""
    nationalities: List[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")

    @field_validator("active_since", "dissolution_date", mode="before")
    @classmethod
    def validate_dates(cls, value):
        return normalize_optional_iso_date(value)


class CreatorMetadata(BaseModel):
    display_name: str = ""
    type: Optional[CreatorType] = None
    aliases: List[str] = Field(default_factory=list)
    collaborations: List[str] = Field(default_factory=list)
    person: PersonMetadata = Field(default_factory=PersonMetadata)
    collaboration: CollaborationMetadata = Field(default_factory=CollaborationMetadata)
    tags: TagMap = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


class ProjectMetadata(BaseModel):
    display_title: str = ""
    release_date: str = ""
    tags: TagMap = Field(default_factory=dict)
    facets: FacetMap = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")

    @field_validator("release_date", mode="before")
    @classmethod
    def validate_release_date(cls, value):
        return normalize_optional_iso_date(value)
