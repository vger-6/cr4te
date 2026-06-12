from enum import Enum


class PortraitVisibility(str, Enum):
    DISABLED = "disabled"
    DETAILS = "details"
    ALL = "all"
