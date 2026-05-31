from __future__ import annotations

from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Generic, TypeVar

from .enums.orientation import Orientation

__all__ = [
    "DEFAULT_MEDIA_CACHE_MAX_ENTRIES",
    "ImageDimensions",
    "MediaInfoCache",
]

DEFAULT_MEDIA_CACHE_MAX_ENTRIES = 4096

K = TypeVar("K")
V = TypeVar("V")


@dataclass(frozen=True)
class ImageDimensions:
    width: int = 0
    height: int = 0

    @property
    def orientation(self) -> Orientation:
        if self.width > 0 and self.height / self.width > 1.2:
            return Orientation.PORTRAIT
        return Orientation.LANDSCAPE


@dataclass
class _BoundedLruCache(Generic[K, V]):
    max_entries: int = DEFAULT_MEDIA_CACHE_MAX_ENTRIES
    _items: OrderedDict[K, V] = field(default_factory=OrderedDict)

    def get_or_load(self, key: K, loader: Callable[[], V]) -> V:
        if self.max_entries <= 0:
            return loader()

        if key in self._items:
            self._items.move_to_end(key)
            return self._items[key]

        value = loader()
        self._items[key] = value
        self._items.move_to_end(key)

        while len(self._items) > self.max_entries:
            self._items.popitem(last=False)

        return value

    def __len__(self) -> int:
        return len(self._items)


@dataclass
class MediaInfoCache:
    max_entries: int = DEFAULT_MEDIA_CACHE_MAX_ENTRIES
    _image_dimensions: _BoundedLruCache[str, ImageDimensions] = field(init=False)
    _audio_durations: _BoundedLruCache[str, float] = field(init=False)

    def __post_init__(self) -> None:
        self._image_dimensions = _BoundedLruCache(self.max_entries)
        self._audio_durations = _BoundedLruCache(self.max_entries)

    def image_dimensions(self, path: Path, loader: Callable[[], ImageDimensions]) -> ImageDimensions:
        return self._image_dimensions.get_or_load(_path_key(path), loader)

    def audio_duration_seconds(self, path: Path, loader: Callable[[], float]) -> float:
        return self._audio_durations.get_or_load(_path_key(path), loader)

    @property
    def image_dimension_count(self) -> int:
        return len(self._image_dimensions)

    @property
    def audio_duration_count(self) -> int:
        return len(self._audio_durations)


def _path_key(path: Path) -> str:
    return str(path.resolve(strict=False))
