from enum import Enum


class ImageVisibility(str, Enum):
    SHOW = "show"
    IF_AVAILABLE = "if_available"
    HIDE = "hide"
