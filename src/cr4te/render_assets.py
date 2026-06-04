from __future__ import annotations

import logging
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .html_context import HtmlBuildContext
from .enums.orientation import Orientation
from .enums.thumb_type import ThumbType
from .media_cache import ImageDimensions
from .render_models import ThumbnailContext
from .utils import image_utils, path_utils

__all__ = [
    "build_thumbnail_context",
    "build_default_thumbnail_specs",
    "DefaultThumbnailSpec",
    "get_image_dimensions",
    "get_image_orientation",
    "prepare_default_thumbnails",
    "resolve_thumbnail_or_default",
    "stage_media_file",
]

logger = logging.getLogger(__name__)


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
    except OSError:
        try:
            os.link(source_path, target_path)
        except OSError:
            shutil.copy2(source_path, target_path)

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


def _get_or_create_thumbnail(ctx: HtmlBuildContext, rel_image_path: Path, thumb_type: ThumbType) -> Path:
    thumb_path = ctx.thumbs_dir / path_utils.build_unique_path(rel_image_path)
    thumb_path = path_utils.tag_path(thumb_path, thumb_type.value)

    if not thumb_path.exists():
        try:
            thumb = image_utils.generate_thumbnail(ctx.input_dir / rel_image_path, ctx.get_generated_thumb_height(thumb_type))
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

        except Exception as exc:
            logger.error(f"Error creating thumbnail for {rel_image_path}: {exc}")

    return thumb_path
