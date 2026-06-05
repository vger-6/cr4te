from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .html_context import HtmlBuildContext
from .enums.orientation import Orientation
from .enums.thumb_type import ThumbType
from .media_cache import ImageDimensions
from .render_models import ThumbnailContext
from .utils import file_utils, image_utils, path_utils

__all__ = [
    "build_thumbnail_context",
    "build_default_thumbnail_specs",
    "DefaultThumbnailSpec",
    "MediaStagingError",
    "get_image_dimensions",
    "get_image_orientation",
    "prepare_default_thumbnails",
    "resolve_thumbnail_or_default",
    "stage_media_file",
]

logger = logging.getLogger(__name__)


class MediaStagingError(RuntimeError):
    """Raised when media cannot be staged without copying source files."""


@dataclass(frozen=True)
class DefaultThumbnailSpec:
    thumb_type: ThumbType
    label: str
    width_ratio: int
    height_ratio: int

    def width_for_height(self, height: int) -> int:
        return int(height * self.width_ratio / self.height_ratio)


def prepare_default_thumbnails(ctx: HtmlBuildContext) -> None:
    ctx.defaults_dir.mkdir(parents=True, exist_ok=True)
    for spec in build_default_thumbnail_specs(ctx):
        height = ctx.get_generated_thumb_height(spec.thumb_type)
        image_utils.create_centered_text_image(
            spec.width_for_height(height),
            height,
            spec.label,
            ctx.get_default_thumb_path(spec.thumb_type),
        )


def build_default_thumbnail_specs(ctx: HtmlBuildContext) -> tuple[DefaultThumbnailSpec, ...]:
    return (
        DefaultThumbnailSpec(ThumbType.CREATOR_OVERVIEW, ctx.site_labels.entity.creator, 3, 4),
        DefaultThumbnailSpec(ThumbType.PROJECT_OVERVIEW, ctx.site_labels.entity.project, 4, 3),
        DefaultThumbnailSpec(ThumbType.CREATOR_PAGE_PROJECT, ctx.site_labels.entity.project, 4, 3),
        DefaultThumbnailSpec(ThumbType.PORTRAIT, ctx.site_labels.entity.portrait, 3, 4),
        DefaultThumbnailSpec(ThumbType.COVER, ctx.site_labels.entity.cover, 4, 3),
        DefaultThumbnailSpec(ThumbType.GALLERY, ctx.site_labels.entity.gallery, 4, 3),
    )


def stage_media_file(input_dir: Path, rel_source_path: Path, target_dir: Path) -> Path:
    source_path = (input_dir / rel_source_path).resolve()
    target_path = target_dir / path_utils.build_unique_path(rel_source_path)

    if not source_path.exists():
        logger.warning(f"Cannot stage media file: source file not found: {source_path}")
        return target_path

    if target_path.exists():
        return target_path

    target_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.symlink(source_path, target_path)
    except OSError as symlink_exc:
        try:
            os.link(source_path, target_path)
        except OSError as hardlink_exc:
            raise MediaStagingError(
                "Cannot stage media file because creating both a symbolic link and a hard link failed. "
                "cr4te will not copy media files automatically because copying large libraries can be expensive. "
                f"Source: {source_path}. Target: {target_path}. "
                f"Symbolic link error: {symlink_exc}. Hard link error: {hardlink_exc}. "
                "Enable symlink permissions or place input and output on the same filesystem so hard links can be used."
            ) from hardlink_exc

    return target_path


def resolve_thumbnail_or_default(ctx: HtmlBuildContext, rel_image_path: Optional[str], thumb_type: ThumbType) -> Path:
    if rel_image_path:
        return _get_or_create_thumbnail(ctx, Path(rel_image_path), thumb_type)
    return ctx.get_default_thumb_path(thumb_type)


def build_thumbnail_context(ctx: HtmlBuildContext, rel_image_path: Optional[str], thumb_type: ThumbType) -> ThumbnailContext:
    thumb_path = resolve_thumbnail_or_default(ctx, rel_image_path, thumb_type)
    rel_thumbnail_path = path_utils.relative_path_from(thumb_path, ctx.output_dir).as_posix()
    dimensions = get_image_dimensions(ctx, thumb_path)

    return ThumbnailContext(
        rel_thumbnail_path=rel_thumbnail_path,
        image_wrapper_width=dimensions.width,
        image_wrapper_height=dimensions.height,
    )


def get_image_dimensions(ctx: HtmlBuildContext, path: Path) -> ImageDimensions:
    return ctx.media_cache.image_dimensions(path, lambda: image_utils.read_image_dimensions(path))


def get_image_orientation(ctx: HtmlBuildContext, path: Path) -> Orientation:
    return get_image_dimensions(ctx, path).orientation


def _source_hash_sidecar_path(thumb_path: Path) -> Path:
    return thumb_path.with_suffix(f"{thumb_path.suffix}.sha256")


def _regenerate_thumbnail(ctx: HtmlBuildContext, source_path: Path, thumb_path: Path, thumb_type: ThumbType) -> None:
    thumb = image_utils.generate_thumbnail(source_path, ctx.get_generated_thumb_height(thumb_type))
    thumb_path.parent.mkdir(parents=True, exist_ok=True)

    thumb_ext = thumb_path.suffix.lower()
    match thumb_ext:
        case ".jpg" | ".jpeg":
            image_format = "JPEG"
        case ".png":
            image_format = "PNG"
        case _:
            raise ValueError(f"Unsupported thumbnail extension: {thumb_ext}")

    thumb.save(thumb_path, format=image_format)


def _get_or_create_thumbnail(ctx: HtmlBuildContext, rel_image_path: Path, thumb_type: ThumbType) -> Path:
    thumb_path = ctx.thumbs_dir / path_utils.build_unique_path(rel_image_path)
    thumb_path = path_utils.tag_path(thumb_path, thumb_type.value)
    source_path = ctx.input_dir / rel_image_path
    sidecar_path = _source_hash_sidecar_path(thumb_path)

    try:
        if not thumb_path.exists():
            _regenerate_thumbnail(ctx, source_path, thumb_path, thumb_type)
            sidecar_path.unlink(missing_ok=True)
            return thumb_path

        thumb_stat = thumb_path.stat()
        if source_path.stat().st_mtime_ns > thumb_stat.st_mtime_ns:
            _regenerate_thumbnail(ctx, source_path, thumb_path, thumb_type)
            sidecar_path.unlink(missing_ok=True)
            return thumb_path

        parent_mtime_ns = source_path.parent.stat().st_mtime_ns
        if parent_mtime_ns <= thumb_stat.st_mtime_ns:
            return thumb_path

        source_hash = file_utils.calculate_sha256(source_path)
        stored_hash = sidecar_path.read_text(encoding="ascii") if sidecar_path.exists() else None
        if source_hash == stored_hash:
            os.utime(thumb_path, ns=(thumb_stat.st_atime_ns, parent_mtime_ns))
            return thumb_path

        _regenerate_thumbnail(ctx, source_path, thumb_path, thumb_type)
        sidecar_path.write_text(source_hash, encoding="ascii")
    except Exception as exc:
        logger.error(f"Error resolving thumbnail for {rel_image_path}: {exc}")

    return thumb_path
