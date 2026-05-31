from enum import Enum

__all__ = ["CreatorType"]


class CreatorType(str, Enum):
    PERSON = "person"
    COLLABORATION = "collaboration"
