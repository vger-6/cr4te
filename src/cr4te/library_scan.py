from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Collection, Iterable

from .constants import README_FILE_NAME
from .enums.image_sample_strategy import ImageSampleStrategy
from .enums.orientation import Orientation
from .enums.portrait_discovery import PortraitDiscovery
from .media_extensions import AUDIO_EXTS, DOC_EXTS, IMAGE_EXTS, MEDIA_EXTS, TEXT_EXTS, VIDEO_EXTS
from .schemas.config_schema import MediaRules
from .schemas.library_schema import MediaGroup, Video
from .utils import image_utils

__all__ = [
    "CreatorScan",
    "MediaBucket",
    "iter_creator_dirs",
    "iter_media_files",
    "iter_project_dirs",
    "media_groups_from_buckets",
    "rel_to_input",
]


def rel_to_input(path: Path, input_dir: Path) -> str:
    return path.relative_to(input_dir).as_posix()


def iter_creator_dirs(input_dir: Path, media_rules: MediaRules) -> Iterable[Path]:
    for creator_dir in sorted(input_dir.iterdir()):
        if not creator_dir.is_dir() or _is_excluded_path(creator_dir, (media_rules.global_exclude_prefix,)):
            continue
        yield creator_dir


def iter_project_dirs(creator_dir: Path, media_rules: MediaRules) -> Iterable[Path]:
    for child in sorted(creator_dir.iterdir()):
        if not child.is_dir():
            continue
        if child.name == media_rules.metadata_folder_name:
            continue
        if _is_excluded_path(child, (media_rules.global_exclude_prefix,)):
            continue
        yield child


def iter_media_files(creator_dir: Path, media_rules: MediaRules) -> Iterable[Path]:
    def within_depth(path: Path) -> bool:
        if media_rules.max_search_depth is None:
            return True
        return len(path.relative_to(creator_dir).parts) <= media_rules.max_search_depth + 1

    for media_path in creator_dir.rglob("*"):
        if not media_path.is_file():
            continue
        if _is_excluded_path(media_path, (media_rules.global_exclude_prefix,)):
            continue
        if not within_depth(media_path):
            continue
        yield media_path


def media_groups_from_buckets(
    buckets: dict[Path, MediaBucket],
    media_rules: MediaRules,
    excluded_images: Collection[str] = (),
) -> list[MediaGroup]:
    return [
        bucket.to_media_group(
            media_rules.image_gallery_sample_max,
            media_rules.image_gallery_sample_strategy,
            excluded_images,
        )
        for _, bucket in sorted(buckets.items(), key=lambda item: item[0].as_posix())
    ]


def _is_excluded_path(path: Path, exclude_prefixes: tuple[str, ...]) -> bool:
    return any(part.startswith(exclude_prefixes) or part.startswith(".") for part in path.parts)


def _sample_images(rel_image_paths: list[str], max_images: int, strategy: ImageSampleStrategy) -> list[str]:
    if max_images <= 0:
        return []

    sorted_paths = sorted(rel_image_paths)

    match strategy:
        case ImageSampleStrategy.NONE:
            return []
        case ImageSampleStrategy.ALL:
            return sorted_paths
        case _ if len(sorted_paths) <= max_images:
            return sorted_paths
        case ImageSampleStrategy.HEAD:
            return sorted_paths[:max_images]
        case ImageSampleStrategy.SPREAD:
            step = len(sorted_paths) / max_images
            return [sorted_paths[int(i * step)] for i in range(max_images)]
        case _:
            return sorted_paths


@dataclass
class ImageSelector:
    basename: str
    orientation: Orientation
    preferred_dir: Path
    allow_orientation_fallback: bool = False
    allow_any_fallback: bool = False
    _direct_named_candidate: Path | None = None
    _nested_named_candidate: Path | None = None
    _orientation_candidate: Path | None = None
    _fallback_candidate: Path | None = None

    def consider(self, image_path: Path) -> None:
        stem = image_path.stem.lower()
        if stem == self.basename.lower():
            if image_path.parent == self.preferred_dir:
                self._direct_named_candidate = _lexicographic_min(self._direct_named_candidate, image_path)
            else:
                self._nested_named_candidate = _lexicographic_min(self._nested_named_candidate, image_path)
            return

        if self._direct_named_candidate is not None or self._nested_named_candidate is not None:
            return

        if self.allow_orientation_fallback:
            if image_utils.infer_image_orientation(image_path) == self.orientation:
                self._orientation_candidate = _lexicographic_min(self._orientation_candidate, image_path)

        if self.allow_any_fallback:
            self._fallback_candidate = _lexicographic_min(self._fallback_candidate, image_path)

    def best(self) -> Path | None:
        return (
            self._direct_named_candidate
            or self._nested_named_candidate
            or self._orientation_candidate
            or self._fallback_candidate
        )


def _lexicographic_min(current: Path | None, candidate: Path) -> Path:
    if current is None:
        return candidate

    def key(path: Path) -> tuple[str, str]:
        value = path.as_posix()
        return value.casefold(), value

    return min(current, candidate, key=key)


@dataclass
class MediaBucket:
    rel_dir_path: Path
    is_root: bool
    input_dir: Path
    videos: list[Video] = field(default_factory=list)
    tracks: list[str] = field(default_factory=list)
    images: list[str] = field(default_factory=list)
    documents: list[str] = field(default_factory=list)
    texts: list[str] = field(default_factory=list)

    def add(self, media_path: Path, cover_selector: ImageSelector | None, portrait_selector: ImageSelector) -> None:
        suffix = media_path.suffix.lower()
        stem = media_path.stem.lower()
        rel_path = rel_to_input(media_path, self.input_dir)

        if suffix in VIDEO_EXTS:
            poster = self._find_video_poster(media_path)
            self.videos.append(Video(file=rel_path, poster=poster or ""))

        elif suffix in AUDIO_EXTS:
            self.tracks.append(rel_path)

        elif suffix in IMAGE_EXTS and not self._is_video_poster_candidate(media_path):
            role_basenames = (
                cover_selector.basename if cover_selector else "",
                portrait_selector.basename,
            )
            if stem not in role_basenames:
                self.images.append(rel_path)

            portrait_selector.consider(media_path)
            if cover_selector is not None:
                cover_selector.consider(media_path)

        elif suffix in DOC_EXTS:
            self.documents.append(rel_path)

        elif suffix in TEXT_EXTS and media_path.name.lower() != README_FILE_NAME.lower():
            self.texts.append(rel_path)

    def _find_video_poster(self, video_path: Path) -> str:
        for image_ext in IMAGE_EXTS:
            candidate = video_path.with_suffix(image_ext)
            if candidate.exists():
                return rel_to_input(candidate, self.input_dir)
        return ""

    def _is_video_poster_candidate(self, image_path: Path) -> bool:
        return any(image_path.with_suffix(video_ext).exists() for video_ext in VIDEO_EXTS)

    def to_media_group(
        self,
        image_sample_max: int,
        image_sample_strategy: ImageSampleStrategy,
        excluded_images: Collection[str] = (),
    ) -> MediaGroup:
        return MediaGroup(
            is_root=self.is_root,
            videos=sorted(self.videos, key=lambda video: video.file),
            tracks=sorted(self.tracks),
            images=_sample_images(
                [image for image in self.images if image not in excluded_images],
                image_sample_max,
                image_sample_strategy,
            ),
            documents=sorted(self.documents),
            texts=sorted(self.texts),
            rel_dir_path=self.rel_dir_path.as_posix(),
        )


@dataclass
class CreatorScan:
    creator_dir: Path
    input_dir: Path
    media_rules: MediaRules
    creator_buckets: dict[Path, MediaBucket] = field(default_factory=dict)
    project_buckets: dict[str, dict[Path, MediaBucket]] = field(default_factory=dict)
    portrait_selector: ImageSelector = field(init=False)
    cover_selectors: dict[str, ImageSelector] = field(init=False)

    def __post_init__(self) -> None:
        self.portrait_selector = ImageSelector(
            self.media_rules.portrait_basename,
            Orientation.PORTRAIT,
            self.creator_dir,
            allow_orientation_fallback=self.media_rules.portrait_discovery == PortraitDiscovery.AUTO,
        )
        self.cover_selectors = {}

    def add_media(self, media_path: Path) -> None:
        if media_path.suffix.lower() not in MEDIA_EXTS:
            return

        rel_path = media_path.relative_to(self.input_dir)
        parts = rel_path.parts
        rel_folder = rel_path.parent
        project_name = self._project_name(parts)

        if project_name is None:
            bucket = self._creator_bucket(rel_folder, parts)
            cover_selector = None
        else:
            bucket = self._project_bucket(project_name, rel_folder, parts)
            cover_selector = self._cover_selector(project_name)

        bucket.add(media_path, cover_selector, self.portrait_selector)

    def _project_name(self, parts: tuple[str, ...]) -> str | None:
        if len(parts) <= 2:
            return None
        candidate = parts[1]
        return None if candidate == self.media_rules.metadata_folder_name else candidate

    def _is_root(self, parts: tuple[str, ...], depth: int) -> bool:
        is_direct_child = len(parts) == depth + 1
        is_in_metadata = len(parts) > depth and parts[-2] == self.media_rules.metadata_folder_name
        return is_direct_child or is_in_metadata

    def _creator_bucket(self, rel_folder: Path, parts: tuple[str, ...]) -> MediaBucket:
        bucket = self.creator_buckets.get(rel_folder)
        if bucket is None:
            bucket = MediaBucket(rel_folder, self._is_root(parts, 1), self.input_dir)
            self.creator_buckets[rel_folder] = bucket
        return bucket

    def _project_bucket(self, project_name: str, rel_folder: Path, parts: tuple[str, ...]) -> MediaBucket:
        project_buckets = self.project_buckets.setdefault(project_name, {})
        bucket = project_buckets.get(rel_folder)
        if bucket is None:
            bucket = MediaBucket(rel_folder, self._is_root(parts, 2), self.input_dir)
            project_buckets[rel_folder] = bucket
        return bucket

    def selected_portrait(self) -> Path | None:
        return self.portrait_selector.best()

    def selected_cover(self, project_name: str) -> Path | None:
        return self._cover_selector(project_name).best()

    def _cover_selector(self, project_name: str) -> ImageSelector:
        selector = self.cover_selectors.get(project_name)
        if selector is None:
            selector = ImageSelector(
                self.media_rules.cover_basename,
                Orientation.LANDSCAPE,
                self.creator_dir / project_name,
                allow_orientation_fallback=True,
                allow_any_fallback=True,
            )
            self.cover_selectors[project_name] = selector
        return selector
