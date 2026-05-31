from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from .schemas.library_schema import MediaGroup

__all__ = ["MediaCounts", "count_media_groups"]


@dataclass(frozen=True)
class MediaCounts:
    video: int = 0
    audio: int = 0
    image: int = 0
    document: int = 0
    text: int = 0

    def values(self) -> tuple[int, int, int, int, int]:
        return (self.video, self.audio, self.image, self.document, self.text)

    def add(self, other: "MediaCounts") -> "MediaCounts":
        return MediaCounts(
            video=self.video + other.video,
            audio=self.audio + other.audio,
            image=self.image + other.image,
            document=self.document + other.document,
            text=self.text + other.text,
        )


def count_media_groups(media_groups: Iterable[MediaGroup]) -> MediaCounts:
    totals = MediaCounts()
    for group in media_groups:
        totals = totals.add(
            MediaCounts(
                video=len(group.videos),
                audio=len(group.tracks),
                image=len(group.images),
                document=len(group.documents),
                text=len(group.texts),
            )
        )
    return totals
