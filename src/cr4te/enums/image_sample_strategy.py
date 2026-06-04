from enum import Enum

class ImageSampleStrategy(str, Enum):
    NONE = "none"
    SPREAD = "spread"
    HEAD = "head"
    ALL = "all"

