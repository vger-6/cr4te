from enum import Enum

class CreatorField(str, Enum):
    PORTRAIT = "portrait"
    DATE_OF_BIRTH = "date_of_birth"
    NATIONALITY = "nationality"
    ALIASES = "aliases"
    DEBUT_AGE = "debut_age"

class CollaborationField(str, Enum):
    PORTRAIT = "portrait"
    NAME = "name"
    MEMBERS = "members"
    FOUNDED = "founded"
    NATIONALITY = "nationality"
    ACTIVE_SINCE = "active_since"

class ProjectField(str, Enum):
    COVER = "cover"
    TITLE = "title"
    RELEASE_DATE = "release_date"
