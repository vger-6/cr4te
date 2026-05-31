from enum import Enum

class ThumbType(str, Enum):
    CREATOR_OVERVIEW = "creator-overview"
    PROJECT_OVERVIEW = "project-overview"
    CREATOR_PAGE_PROJECT = "creator-page-project"
    PORTRAIT = "portrait"
    COVER = "cover"
    GALLERY = "gallery"
