from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Literal
import re


def validate_optional_iso_date(v: str) -> str:
    if not v:
        return v

    v = v.strip()

    if re.fullmatch(r"\d{4}", v):
        return v
    if re.fullmatch(r"\d{4}-\d{2}", v):
        return v
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", v):
        return v

    raise ValueError("must be in yyyy, yyyy-mm, yyyy-mm-dd format or empty")


def _validate_date_order(start: str, end: str, field_names: str):
    if start and end and start > end:
        raise ValueError(f"{field_names} are in invalid chronological order")


class BaseDatedModel(BaseModel):
    @field_validator("*", mode="before")
    def validate_dates(cls, v):
        if isinstance(v, str):
            return validate_optional_iso_date(v)
        return v


class Person(BaseDatedModel):
    date_of_birth: str = ""
    date_of_death: str = ""

    @model_validator(mode="after")
    def check_person_dates(self):
        _validate_date_order(self.date_of_birth, self.date_of_death, "date_of_birth/date_of_death")
        return self


class Collaboration(BaseDatedModel):
    founding_date: str = ""
    dissolution_date: str = ""
    members: List[str]

    @model_validator(mode="after")
    def check_collab_dates(self):
        _validate_date_order(self.founding_date, self.dissolution_date, "founding_date/dissolution_date")
        return self


class Video(BaseModel):
    file: str
    poster: str

    class Config:
        extra = "forbid"


class MediaGroup(BaseModel):
    is_root: bool
    videos: List[Video]
    tracks: List[str]
    images: List[str]
    documents: List[str]
    texts: List[str]
    rel_dir_path: str

    class Config:
        extra = "forbid"


class Project(BaseModel):
    title: str
    release_date: str
    cover: str
    info: str
    tags: List[str]
    media_groups: List[MediaGroup]

    @field_validator("release_date", mode="before")
    def validate_release_date(cls, v):
        return validate_optional_iso_date(v)

    class Config:
        extra = "forbid"


class Creator(BaseModel):
    name: str
    type: Literal["person", "collaboration"]
    active_since: str
    person: Person
    collaboration: Collaboration
    nationality: str
    aliases: List[str]
    portrait: str
    info: str
    tags: List[str]
    projects: List[Project]
    media_groups: List[MediaGroup]
    collaborations: List[str]

    @model_validator(mode="after")
    def enforce_type_consistency(self):
        if self.type == "person":
            if any([
                self.collaboration.founding_date,
                self.collaboration.dissolution_date,
                len(self.collaboration.members) > 0,
            ]):
                raise ValueError("person creator must not have collaboration data")

        elif self.type == "collaboration":
            if any([
                self.person.date_of_birth,
                self.person.date_of_death,
            ]):
                raise ValueError("collaboration must not have person data")

        return self

    class Config:
        extra = "forbid"
