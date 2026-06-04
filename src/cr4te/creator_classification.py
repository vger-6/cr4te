from __future__ import annotations

from collections.abc import Iterable

from .enums.creator_type import CreatorType

__all__ = ["infer_creator_type"]


def infer_creator_type(creator_name: str, collaboration_separators: Iterable[str]) -> CreatorType:
    if any(separator in creator_name for separator in collaboration_separators):
        return CreatorType.COLLABORATION
    return CreatorType.PERSON
