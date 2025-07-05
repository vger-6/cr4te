from enum import Enum

class CreatorField(str, Enum):
    DATE_OF_BIRTH = "date_of_birth"
    NATIONALITY = "nationality"
    ALIASES = "aliases"
    DEBUT_AGE = "debut_age"

class CollaborationField(str, Enum):
    NAME = "name"
    MEMBERS = "members"
    FOUNDED = "founded"
    NATIONALITY = "nationality"
    ACTIVE_SINCE = "active_since"

class ProjectField(str, Enum):
    TITLE = "title"
    RELEASE_DATE = "release_date"
