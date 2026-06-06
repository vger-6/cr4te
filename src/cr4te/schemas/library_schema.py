from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from typing import Dict, List

from ..enums.creator_type import CreatorType
from ..enums.visible_fields import ProjectField
from ..utils.date_utils import normalize_optional_iso_date


def _validate_date_order(start: str, end: str, field_names: str):
    if start and end and start > end:
        raise ValueError(f"{field_names} are in invalid chronological order")


class BaseDatedModel(BaseModel):
    @field_validator(
        "date_of_birth",
        "date_of_death",
        "active_since",
        "founding_date",
        "dissolution_date",
        mode="before",
        check_fields=False,
    )
    def validate_dates(cls, v):
        return normalize_optional_iso_date(v)


class Video(BaseModel):
    file: str
    poster: str

    model_config = ConfigDict(extra="forbid")


class MediaGroup(BaseModel):
    is_root: bool
    videos: List[Video]
    tracks: List[str]
    images: List[str]
    documents: List[str]
    texts: List[str]
    rel_dir_path: str

    model_config = ConfigDict(extra="forbid")


class Project(BaseModel):
    title: str
    display_title: str
    release_date: str
    cover: str
    info: str
    tags: Dict[str, List[str]] = Field(default_factory=dict)
    facets: Dict[ProjectField, List[str]] = Field(default_factory=dict)
    media_groups: List[MediaGroup]

    @field_validator("release_date", mode="before")
    def validate_release_date(cls, v):
        return normalize_optional_iso_date(v)

    model_config = ConfigDict(extra="forbid")


PERSON_CREATOR_FIELDS = {
    "date_of_birth",
    "place_of_birth",
    "date_of_death",
    "place_of_death",
    "civil_name",
}

COLLABORATION_CREATOR_FIELDS = {
    "founding_date",
    "founding_location",
    "dissolution_date",
    "members",
}


class Creator(BaseDatedModel):
    name: str
    display_name: str
    type: CreatorType
    active_since: str
    date_of_birth: str = ""
    place_of_birth: str = ""
    date_of_death: str = ""
    place_of_death: str = ""
    civil_name: str = ""
    founding_date: str = ""
    founding_location: str = ""
    dissolution_date: str = ""
    members: List[str] = Field(default_factory=list)
    nationalities: List[str] = Field(default_factory=list)
    aliases: List[str] = Field(default_factory=list)
    portrait: str
    info: str
    tags: Dict[str, List[str]] = Field(default_factory=dict)
    projects: List[Project] = Field(default_factory=list)
    media_groups: List[MediaGroup] = Field(default_factory=list)
    collaborations: List[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def enforce_type_consistency(self):
        if self.type == CreatorType.PERSON:
            if self.model_fields_set & COLLABORATION_CREATOR_FIELDS:
                raise ValueError("person creator must not have collaboration fields")
            _validate_date_order(self.date_of_birth, self.date_of_death, "date_of_birth/date_of_death")

        elif self.type == CreatorType.COLLABORATION:
            if self.model_fields_set & PERSON_CREATOR_FIELDS:
                raise ValueError("collaboration must not have person fields")
            if "members" not in self.model_fields_set:
                raise ValueError("collaboration creator must have members")
            _validate_date_order(self.founding_date, self.dissolution_date, "founding_date/dissolution_date")

        return self

    model_config = ConfigDict(extra="forbid")
