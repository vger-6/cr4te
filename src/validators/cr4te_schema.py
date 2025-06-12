from pydantic import BaseModel, validator
from typing import List
import re

def validate_optional_iso_date(v: str) -> str:
    if not v:
        return v
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", v):
        return v
    raise ValueError("must be in yyyy-mm-dd format or empty")

class MediaGroup(BaseModel):
    is_root: bool
    videos: List[str]
    tracks: List[str]
    images: List[str]
    documents: List[str]
    texts: List[str]
    folder_path: str

class Project(BaseModel):
    title: str
    release_date: str
    cover: str
    info: str
    tags: List[str]
    media_groups: List[MediaGroup]

    @validator("release_date")
    def validate_release_date(cls, v):
        return validate_optional_iso_date(v)

class Creator(BaseModel):
    name: str
    is_collaboration: bool
    born_or_founded: str
    active_since: str
    nationality: str
    aliases: List[str]
    portrait: str
    info: str
    tags: List[str]
    projects: List[Project]
    media_groups: List[MediaGroup]
    members: List[str]
    collaborations: List[str]

    @validator("born_or_founded", "active_since")
    def validate_optional_dates(cls, v):
        return validate_optional_iso_date(v)

