from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Collection, Iterable, Mapping

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
    "iter_creator_dirs",
    "iter_media_files",
    "iter_project_dirs",
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


def _media_groups_from_buckets(
    buckets: dict[Path, _MediaBucket],
    media_rules: MediaRules,
    video_posters: Mapping[str, str],
    excluded_images: Collection[str] = (),
) -> list[MediaGroup]:
    def group_sort_key(item: tuple[Path, _MediaBucket]) -> tuple[int, str]:
        rel_folder, bucket = item
        if bucket.is_root and rel_folder.name != media_rules.metadata_folder_name:
            priority = 0
        elif rel_folder.name == media_rules.metadata_folder_name:
            priority = 1
        else:
            priority = 2
        return priority, rel_folder.as_posix()

    return [
        bucket.to_media_group(
            media_rules.image_gallery_sample_max,
            media_rules.image_gallery_sample_strategy,
            video_posters,
            excluded_images,
        )
        for _, bucket in sorted(buckets.items(), key=group_sort_key)
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


def _lexicographic_path_key(path: Path) -> tuple[str, str]:
    value = path.as_posix()
    return value.casefold(), value


def _named_candidates(image_paths: Iterable[Path], basename: str) -> list[Path]:
    normalized_basename = basename.casefold()
    return sorted(
        (image_path for image_path in image_paths if image_path.stem.casefold() == normalized_basename),
        key=_lexicographic_path_key,
    )


def _select_named_candidate(candidates: list[Path], preferred_dir: Path) -> Path | None:
    return next((candidate for candidate in candidates if candidate.parent == preferred_dir), None) or (
        candidates[0] if candidates else None
    )


@dataclass
class _MediaBucket:
    rel_dir_path: Path
    is_root: bool
    input_dir: Path
    videos: list[str] = field(default_factory=list)
    tracks: list[str] = field(default_factory=list)
    images: list[str] = field(default_factory=list)
    documents: list[str] = field(default_factory=list)
    texts: list[str] = field(default_factory=list)

    def add(self, media_path: Path) -> None:
        suffix = media_path.suffix.lower()
        rel_path = rel_to_input(media_path, self.input_dir)

        if suffix in VIDEO_EXTS:
            self.videos.append(rel_path)

        elif suffix in AUDIO_EXTS:
            self.tracks.append(rel_path)

        elif suffix in IMAGE_EXTS:
            self.images.append(rel_path)

        elif suffix in DOC_EXTS:
            self.documents.append(rel_path)

        elif suffix in TEXT_EXTS and media_path.name.lower() != README_FILE_NAME.lower():
            self.texts.append(rel_path)

    def to_media_group(
        self,
        image_sample_max: int,
        image_sample_strategy: ImageSampleStrategy,
        video_posters: Mapping[str, str],
        excluded_images: Collection[str] = (),
    ) -> MediaGroup:
        return MediaGroup(
            is_root=self.is_root,
            videos=[Video(file=video, poster=video_posters.get(video, "")) for video in sorted(self.videos)],
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
    _creator_buckets: dict[Path, _MediaBucket] = field(default_factory=dict, init=False)
    _project_buckets: dict[str, dict[Path, _MediaBucket]] = field(default_factory=dict, init=False)
    _image_paths: list[Path] = field(default_factory=list, init=False)
    _video_paths: list[Path] = field(default_factory=list, init=False)
    _special_images_resolved: bool = field(default=False, init=False)
    _selected_portrait: Path | None = field(default=None, init=False)
    _selected_covers: dict[str, Path | None] = field(default_factory=dict, init=False)
    _video_posters: dict[str, str] = field(default_factory=dict, init=False)
    _gallery_excluded_images: set[str] = field(default_factory=set, init=False)
    _image_orientations: dict[Path, Orientation] = field(default_factory=dict, init=False)

    def add_media(self, media_path: Path) -> None:
        if media_path.suffix.lower() not in MEDIA_EXTS:
            return

        rel_path = media_path.relative_to(self.input_dir)
        parts = rel_path.parts
        rel_folder = rel_path.parent
        project_name = self._project_name(parts)

        if project_name is None:
            bucket = self._creator_bucket(rel_folder, parts)
        else:
            bucket = self._project_bucket(project_name, rel_folder, parts)

        bucket.add(media_path)
        if media_path.suffix.lower() in IMAGE_EXTS:
            self._image_paths.append(media_path)
        elif media_path.suffix.lower() in VIDEO_EXTS:
            self._video_paths.append(media_path)
        self._special_images_resolved = False

    def _project_name(self, parts: tuple[str, ...]) -> str | None:
        if len(parts) <= 2:
            return None
        candidate = parts[1]
        return None if candidate == self.media_rules.metadata_folder_name else candidate

    def _is_root(self, parts: tuple[str, ...], depth: int) -> bool:
        is_direct_child = len(parts) == depth + 1
        is_in_metadata = len(parts) > depth and parts[-2] == self.media_rules.metadata_folder_name
        return is_direct_child or is_in_metadata

    def _creator_bucket(self, rel_folder: Path, parts: tuple[str, ...]) -> _MediaBucket:
        bucket = self._creator_buckets.get(rel_folder)
        if bucket is None:
            bucket = _MediaBucket(rel_folder, self._is_root(parts, 1), self.input_dir)
            self._creator_buckets[rel_folder] = bucket
        return bucket

    def _project_bucket(self, project_name: str, rel_folder: Path, parts: tuple[str, ...]) -> _MediaBucket:
        project_buckets = self._project_buckets.setdefault(project_name, {})
        bucket = project_buckets.get(rel_folder)
        if bucket is None:
            bucket = _MediaBucket(rel_folder, self._is_root(parts, 2), self.input_dir)
            project_buckets[rel_folder] = bucket
        return bucket

    def selected_portrait(self) -> Path | None:
        self._resolve_special_images()
        return self._selected_portrait

    def selected_cover(self, project_name: str) -> Path | None:
        self._resolve_special_images()
        return self._selected_covers.get(project_name)

    def discovered_project_names(self) -> set[str]:
        return set(self._project_buckets)

    def creator_media_groups(self) -> list[MediaGroup]:
        self._resolve_special_images()
        return _media_groups_from_buckets(
            self._creator_buckets,
            self.media_rules,
            self._video_posters,
            self._gallery_excluded_images,
        )

    def project_media_groups(self, project_name: str) -> list[MediaGroup]:
        self._resolve_special_images()
        return _media_groups_from_buckets(
            self._project_buckets.get(project_name, {}),
            self.media_rules,
            self._video_posters,
            self._gallery_excluded_images,
        )

    def _resolve_special_images(self) -> None:
        if self._special_images_resolved:
            return

        sorted_images = sorted(set(self._image_paths), key=_lexicographic_path_key)
        poster_candidates = self._resolve_video_posters(sorted_images)
        project_images = self._project_images(sorted_images)
        self._gallery_excluded_images = {rel_to_input(path, self.input_dir) for path in poster_candidates}

        portrait_candidates = _named_candidates(sorted_images, self.media_rules.portrait_basename)
        self._gallery_excluded_images.update(rel_to_input(path, self.input_dir) for path in portrait_candidates)
        self._selected_portrait = _select_named_candidate(portrait_candidates, self.creator_dir)
        if self._selected_portrait is None and self.media_rules.portrait_discovery == PortraitDiscovery.AUTO:
            self._selected_portrait = next(
                (
                    image_path
                    for image_path in sorted_images
                    if image_path not in poster_candidates and self._orientation(image_path) == Orientation.PORTRAIT
                ),
                None,
            )
            if self._selected_portrait is not None:
                self._gallery_excluded_images.add(rel_to_input(self._selected_portrait, self.input_dir))

        self._selected_covers = {}
        for project_name, images in project_images.items():
            cover_candidates = _named_candidates(images, self.media_rules.cover_basename)
            self._gallery_excluded_images.update(rel_to_input(path, self.input_dir) for path in cover_candidates)
            selected_cover = _select_named_candidate(cover_candidates, self.creator_dir / project_name)
            if selected_cover is None:
                eligible_images = [image_path for image_path in images if image_path not in poster_candidates]
                selected_cover = next(
                    (
                        image_path
                        for image_path in eligible_images
                        if self._orientation(image_path) == Orientation.LANDSCAPE
                    ),
                    eligible_images[0] if eligible_images else None,
                )
                if selected_cover is not None:
                    self._gallery_excluded_images.add(rel_to_input(selected_cover, self.input_dir))
            self._selected_covers[project_name] = selected_cover

        self._special_images_resolved = True

    def _resolve_video_posters(self, sorted_images: list[Path]) -> set[Path]:
        images_by_folder_and_stem: dict[tuple[Path, str], list[Path]] = {}
        for image_path in sorted_images:
            key = image_path.parent, image_path.stem.casefold()
            images_by_folder_and_stem.setdefault(key, []).append(image_path)

        self._video_posters = {}
        poster_candidates: set[Path] = set()
        for video_path in sorted(set(self._video_paths), key=_lexicographic_path_key):
            candidates = images_by_folder_and_stem.get((video_path.parent, video_path.stem.casefold()), [])
            if not candidates:
                continue
            poster_candidates.update(candidates)
            self._video_posters[rel_to_input(video_path, self.input_dir)] = rel_to_input(candidates[0], self.input_dir)
        return poster_candidates

    def _project_images(self, sorted_images: list[Path]) -> dict[str, list[Path]]:
        project_images: dict[str, list[Path]] = {}
        for image_path in sorted_images:
            project_name = self._project_name(image_path.relative_to(self.input_dir).parts)
            if project_name is not None:
                project_images.setdefault(project_name, []).append(image_path)
        return project_images

    def _orientation(self, image_path: Path) -> Orientation:
        orientation = self._image_orientations.get(image_path)
        if orientation is None:
            orientation = image_utils.infer_image_orientation(image_path)
            self._image_orientations[image_path] = orientation
        return orientation
