from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .asset_issues import (
    media_inspection_failure_issue,
    media_staging_failure_issue,
    missing_media_issue,
    thumbnail_failure_issue,
)
from .build_issues import BuildIssueError
from .html_context import HtmlBuildContext
from .enums.orientation import Orientation
from .enums.portrait_visibility import PortraitVisibility
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

THUMBNAIL_FRESHNESS_VERSION = 1

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
    project_cards_width_ratio, project_cards_height_ratio = image_utils.parse_aspect_ratio(
        ctx.site_rendering.galleries.project_cards.aspect_ratio
    )
    specs = [
        DefaultThumbnailSpec(ThumbType.PROJECT_OVERVIEW, ctx.site_labels.entity.project, project_cards_width_ratio, project_cards_height_ratio),
        DefaultThumbnailSpec(ThumbType.CREATOR_PAGE_PROJECT, ctx.site_labels.entity.project, 4, 3),
        DefaultThumbnailSpec(ThumbType.COVER, ctx.site_labels.entity.cover, project_cards_width_ratio, project_cards_height_ratio),
        DefaultThumbnailSpec(ThumbType.GALLERY, ctx.site_labels.entity.gallery, 4, 3),
    ]
    portrait_visibility = ctx.site_rendering.portraits.visibility
    if portrait_visibility != PortraitVisibility.DISABLED:
        specs.insert(0, DefaultThumbnailSpec(ThumbType.PORTRAIT, ctx.site_labels.entity.portrait, 3, 4))
    if portrait_visibility == PortraitVisibility.ALL:
        specs.insert(0, DefaultThumbnailSpec(ThumbType.CREATOR_OVERVIEW, ctx.site_labels.entity.creator, 3, 4))
    return tuple(specs)


def stage_media_file(ctx: HtmlBuildContext, rel_source_path: Path) -> Path | None:
    source_path = (ctx.input_dir / rel_source_path).resolve()
    target_path = ctx.symlinks_dir / path_utils.build_unique_path(rel_source_path)

    if not source_path.is_file():
        ctx.report_issue(missing_media_issue(source_path))
        return None

    if target_path.exists():
        ctx.asset_statistics.media_links_reused += 1
        return target_path

    target_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.symlink(source_path, target_path)
        ctx.asset_statistics.symbolic_links_created += 1
    except OSError as symlink_exc:
        try:
            os.link(source_path, target_path)
            ctx.asset_statistics.hard_links_created += 1
        except OSError as hardlink_exc:
            message = (
                "Cannot stage media file because creating both a symbolic link and a hard link failed. "
                "cr4te will not copy media files automatically because copying large libraries can be expensive. "
                f"Source: {source_path}. Target: {target_path}. "
                f"Symbolic link error: {symlink_exc}. Hard link error: {hardlink_exc}. "
                "Enable symlink permissions or place input and output on the same filesystem so hard links can be used."
            )
            raise BuildIssueError(media_staging_failure_issue(source_path, message)) from hardlink_exc

    return target_path


def resolve_thumbnail_or_default(ctx: HtmlBuildContext, rel_image_path: Optional[str], thumb_type: ThumbType) -> Path:
    if rel_image_path:
        return _get_or_create_thumbnail(ctx, Path(rel_image_path), thumb_type)
    ctx.asset_statistics.default_thumbnail_uses += 1
    return ctx.get_default_thumb_path(thumb_type)


def build_thumbnail_context(ctx: HtmlBuildContext, rel_image_path: Optional[str], thumb_type: ThumbType) -> ThumbnailContext:
    thumb_path = resolve_thumbnail_or_default(ctx, rel_image_path, thumb_type)
    rel_thumbnail_path = path_utils.relative_path_from(thumb_path, ctx.output_dir).as_posix()
    source_path = ctx.input_dir / rel_image_path if rel_image_path else thumb_path
    dimensions = get_image_dimensions(ctx, thumb_path, issue_path=source_path)
    if not dimensions.width or not dimensions.height:
        thumb_path = ctx.get_default_thumb_path(thumb_type)
        ctx.asset_statistics.default_thumbnail_uses += 1
        rel_thumbnail_path = path_utils.relative_path_from(thumb_path, ctx.output_dir).as_posix()
        dimensions = get_image_dimensions(ctx, thumb_path)

    return ThumbnailContext(
        rel_thumbnail_path=rel_thumbnail_path,
        image_wrapper_width=dimensions.width,
        image_wrapper_height=dimensions.height,
    )


def get_image_dimensions(ctx: HtmlBuildContext, path: Path, issue_path: Path | None = None) -> ImageDimensions:
    def load_dimensions() -> ImageDimensions:
        try:
            return image_utils.read_image_dimensions(path)
        except Exception as exc:
            ctx.report_issue(media_inspection_failure_issue(issue_path or path, exc), exc)
            return ImageDimensions()

    return ctx.media_cache.image_dimensions(path, load_dimensions)


def get_image_orientation(ctx: HtmlBuildContext, path: Path) -> Orientation:
    return get_image_dimensions(ctx, path).orientation


def _freshness_sidecar_path(thumb_path: Path) -> Path:
    return thumb_path.with_suffix(f"{thumb_path.suffix}.json")


def _thumbnail_freshness_metadata(
    source_path: Path,
    rel_image_path: Path,
    thumb_path: Path,
    thumb_type: ThumbType,
    generated_height: int,
) -> dict[str, int | str]:
    source_stat = source_path.stat()
    return {
        "version": THUMBNAIL_FRESHNESS_VERSION,
        "source_path": rel_image_path.as_posix(),
        "source_size": source_stat.st_size,
        "source_mtime_ns": source_stat.st_mtime_ns,
        "thumb_type": thumb_type.value,
        "generated_height": generated_height,
        "thumbnail_suffix": thumb_path.suffix.lower(),
    }


def _read_freshness_sidecar(sidecar_path: Path) -> dict[str, object] | None:
    try:
        data = json.loads(sidecar_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _write_freshness_sidecar(sidecar_path: Path, metadata: dict[str, int | str]) -> None:
    sidecar_path.write_text(json.dumps(metadata, sort_keys=True), encoding="utf-8")


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
    ctx.asset_statistics.source_thumbnails_generated += 1


def _get_or_create_thumbnail(ctx: HtmlBuildContext, rel_image_path: Path, thumb_type: ThumbType) -> Path:
    thumb_path = ctx.thumbs_dir / path_utils.build_unique_path(rel_image_path)
    thumb_path = path_utils.tag_path(thumb_path, thumb_type.value)
    source_path = ctx.input_dir / rel_image_path
    sidecar_path = _freshness_sidecar_path(thumb_path)

    if not source_path.is_file():
        ctx.report_issue(missing_media_issue(source_path))
        ctx.asset_statistics.default_thumbnail_uses += 1
        return ctx.get_default_thumb_path(thumb_type)

    try:
        ctx.asset_statistics.source_freshness_checks += 1
        generated_height = ctx.get_generated_thumb_height(thumb_type)
        current_freshness = _thumbnail_freshness_metadata(
            source_path,
            rel_image_path,
            thumb_path,
            thumb_type,
            generated_height,
        )
        stored_freshness = _read_freshness_sidecar(sidecar_path)

        if thumb_path.exists() and current_freshness == stored_freshness:
            ctx.asset_statistics.source_thumbnails_reused += 1
            return thumb_path

        _regenerate_thumbnail(ctx, source_path, thumb_path, thumb_type)
        _write_freshness_sidecar(sidecar_path, current_freshness)
    except Exception as exc:
        ctx.report_issue(thumbnail_failure_issue(source_path, exc), exc)
        ctx.asset_statistics.default_thumbnail_uses += 1
        return ctx.get_default_thumb_path(thumb_type)

    return thumb_path
