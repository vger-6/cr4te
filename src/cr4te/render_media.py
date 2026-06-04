from __future__ import annotations

from pathlib import Path
from typing import Iterable

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
from .utils import audio_utils, path_utils, text_utils

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


def _staged_rel_path(ctx: HtmlBuildContext, rel_path: str) -> str:
    staged_path = stage_media_file(ctx.input_dir, Path(rel_path), ctx.symlinks_dir)
    return path_utils.relative_path_from(staged_path, ctx.output_dir).as_posix()


def _audio_duration_seconds(ctx: HtmlBuildContext, rel_path: str) -> float:
    audio_path = ctx.input_dir / Path(rel_path)
    return ctx.media_cache.audio_duration_seconds(audio_path, lambda: audio_utils.get_audio_duration_seconds(audio_path))


def _build_image_contexts(ctx: HtmlBuildContext, rel_image_paths: list[str]) -> list[GalleryImageContext]:
    images: list[GalleryImageContext] = []

    for rel_path in rel_image_paths:
        thumbnail = build_thumbnail_context(ctx, rel_path, ThumbType.GALLERY)
        images.append(
            GalleryImageContext(
                rel_thumbnail_path=thumbnail.rel_thumbnail_path,
                image_wrapper_width=thumbnail.image_wrapper_width,
                image_wrapper_height=thumbnail.image_wrapper_height,
                rel_path=_staged_rel_path(ctx, rel_path),
                caption=Path(rel_path).stem,
            )
        )

    return images


def _build_video_contexts(ctx: HtmlBuildContext, videos: list[Video]) -> list[VideoContext]:
    return [
        VideoContext(
            rel_path=_staged_rel_path(ctx, video.file),
            title=Path(video.file).stem.title(),
            rel_poster_path=_staged_rel_path(ctx, video.poster) if video.poster else "",
        )
        for video in videos
    ]


def _build_track_contexts(ctx: HtmlBuildContext, rel_track_paths: list[str]) -> list[TrackContext]:
    return [
        TrackContext(
            rel_path=_staged_rel_path(ctx, rel_path),
            title=Path(rel_path).stem,
            duration_seconds=_audio_duration_seconds(ctx, rel_path),
        )
        for rel_path in rel_track_paths
    ]


def _build_document_contexts(ctx: HtmlBuildContext, rel_document_paths: list[str]) -> list[DocumentContext]:
    return [
        DocumentContext(
            rel_path=_staged_rel_path(ctx, rel_path),
            title=Path(rel_path).stem.title(),
        )
        for rel_path in rel_document_paths
    ]


def _build_text_contexts(ctx: HtmlBuildContext, rel_text_paths: list[str]) -> list[TextContext]:
    return [
        TextContext(
            content=text_utils.markdown_to_html(text_utils.read_text(ctx.input_dir / Path(rel_path))),
            title=Path(rel_path).stem.title(),
        )
        for rel_path in rel_text_paths
    ]
