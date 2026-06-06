from __future__ import annotations

from pathlib import Path
from typing import Iterable

from .asset_issues import media_inspection_failure_issue, media_read_failure_issue, missing_media_issue
from .html_context import HtmlBuildContext
from .enums.media_type import MediaType
from .enums.thumb_type import ThumbType
from .render_assets import build_thumbnail_context, stage_media_file
from .render_models import (
    DocumentContext,
    GalleryImageContext,
    MediaGroupContext,
    MediaSectionContext,
    TextContext,
    TrackContext,
    VideoContext,
)
from .schemas.library_schema import MediaGroup, Video
from .utils import audio_utils, image_utils, path_utils, text_utils

__all__ = [
    "build_media_group_contexts",
    "sort_media_sections_by_type",
]


def sort_media_sections_by_type(
    sections: Iterable[MediaSectionContext],
    media_type_order: Iterable[MediaType | str],
) -> list[MediaSectionContext]:
    order_map = {
        _media_type_value(media_type): index
        for index, media_type in enumerate(dict.fromkeys(media_type_order))
    }
    fallback_order = len(order_map)

    return sorted(sections, key=lambda section: order_map.get(_media_type_value(section.type), fallback_order))


def build_media_group_contexts(ctx: HtmlBuildContext, media_groups: list[MediaGroup]) -> list[MediaGroupContext]:
    return [_build_media_group_context(ctx, media_group) for media_group in media_groups]


def _media_type_value(media_type: MediaType | str) -> str:
    if isinstance(media_type, MediaType):
        return media_type.value
    return media_type


def _build_media_group_context(ctx: HtmlBuildContext, media_group: MediaGroup) -> MediaGroupContext:
    audio_section_title, image_section_title = _get_section_titles(
        media_group,
        ctx.audio_section_default_title,
        ctx.image_section_default_title,
    )

    tracks = _build_track_contexts(ctx, media_group.tracks)
    sections = [
        MediaSectionContext(type=MediaType.VIDEO, videos=_build_video_contexts(ctx, media_group.videos)),
        MediaSectionContext(
            type=MediaType.AUDIO,
            tracks=tracks,
            total_duration_seconds=sum(track.duration_seconds for track in tracks),
        ),
        MediaSectionContext(type=MediaType.IMAGE, images=_build_image_contexts(ctx, media_group.images)),
        MediaSectionContext(type=MediaType.DOCUMENT, documents=_build_document_contexts(ctx, media_group.documents)),
        MediaSectionContext(type=MediaType.TEXT, texts=_build_text_contexts(ctx, media_group.texts)),
    ]

    return MediaGroupContext(
        audio_section_title=audio_section_title,
        image_section_title=image_section_title,
        sections=sort_media_sections_by_type(sections, ctx.media_type_order),
    )


def _get_section_titles(media_group: MediaGroup, audio_section_title: str, image_section_title: str) -> tuple[str, str]:
    if media_group.is_root:
        return audio_section_title, image_section_title

    title = Path(media_group.rel_dir_path).name.title()
    return title, title


def _staged_rel_path(ctx: HtmlBuildContext, rel_path: str) -> str | None:
    staged_path = stage_media_file(ctx, Path(rel_path))
    return path_utils.relative_path_from(staged_path, ctx.output_dir).as_posix() if staged_path else None


def _audio_duration_seconds(ctx: HtmlBuildContext, rel_path: str) -> float:
    audio_path = ctx.input_dir / Path(rel_path)

    def load_duration() -> float:
        try:
            return audio_utils.get_audio_duration_seconds(audio_path)
        except Exception as exc:
            ctx.report_issue(media_inspection_failure_issue(audio_path, exc), exc)
            return 0

    return ctx.media_cache.audio_duration_seconds(audio_path, load_duration)


def _build_image_contexts(ctx: HtmlBuildContext, rel_image_paths: list[str]) -> list[GalleryImageContext]:
    images: list[GalleryImageContext] = []

    for rel_path in rel_image_paths:
        source_path = ctx.input_dir / Path(rel_path)
        if not source_path.is_file():
            ctx.report_issue(missing_media_issue(source_path))
            continue
        thumbnail = build_thumbnail_context(ctx, rel_path, ThumbType.GALLERY)
        default_thumbnail_path = path_utils.relative_path_from(
            ctx.get_default_thumb_path(ThumbType.GALLERY),
            ctx.output_dir,
        ).as_posix()
        if thumbnail.rel_thumbnail_path == default_thumbnail_path:
            try:
                image_utils.read_image_dimensions(source_path)
            except Exception as exc:
                ctx.report_issue(media_read_failure_issue(source_path, exc), exc)
                continue
        staged_rel_path = _staged_rel_path(ctx, rel_path)
        if not staged_rel_path:
            continue
        images.append(
            GalleryImageContext(
                rel_thumbnail_path=thumbnail.rel_thumbnail_path,
                image_wrapper_width=thumbnail.image_wrapper_width,
                image_wrapper_height=thumbnail.image_wrapper_height,
                rel_path=staged_rel_path,
                caption=Path(rel_path).stem,
            )
        )

    return images


def _build_video_contexts(ctx: HtmlBuildContext, videos: list[Video]) -> list[VideoContext]:
    contexts: list[VideoContext] = []
    for video in videos:
        staged_rel_path = _staged_rel_path(ctx, video.file)
        if not staged_rel_path:
            continue
        contexts.append(
            VideoContext(
                rel_path=staged_rel_path,
                title=Path(video.file).stem.title(),
                rel_poster_path=(_staged_rel_path(ctx, video.poster) or "") if video.poster else "",
            )
        )
    return contexts


def _build_track_contexts(ctx: HtmlBuildContext, rel_track_paths: list[str]) -> list[TrackContext]:
    contexts: list[TrackContext] = []
    for rel_path in rel_track_paths:
        staged_rel_path = _staged_rel_path(ctx, rel_path)
        if not staged_rel_path:
            continue
        contexts.append(
            TrackContext(
                rel_path=staged_rel_path,
                title=Path(rel_path).stem,
                duration_seconds=_audio_duration_seconds(ctx, rel_path),
            )
        )
    return contexts


def _build_document_contexts(ctx: HtmlBuildContext, rel_document_paths: list[str]) -> list[DocumentContext]:
    contexts: list[DocumentContext] = []
    for rel_path in rel_document_paths:
        staged_rel_path = _staged_rel_path(ctx, rel_path)
        if not staged_rel_path:
            continue
        contexts.append(
            DocumentContext(
                rel_path=staged_rel_path,
                title=Path(rel_path).stem.title(),
            )
        )
    return contexts


def _build_text_contexts(ctx: HtmlBuildContext, rel_text_paths: list[str]) -> list[TextContext]:
    contexts: list[TextContext] = []
    for rel_path in rel_text_paths:
        text_path = ctx.input_dir / Path(rel_path)
        if not text_path.is_file():
            ctx.report_issue(missing_media_issue(text_path))
            continue
        try:
            content = text_utils.read_text(text_path)
        except (OSError, UnicodeError) as exc:
            ctx.report_issue(media_read_failure_issue(text_path, exc), exc)
            continue
        contexts.append(
            TextContext(
                content=text_utils.markdown_to_html(content),
                title=Path(rel_path).stem.title(),
            )
        )
    return contexts
