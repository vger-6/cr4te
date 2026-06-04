from __future__ import annotations

IMAGE_EXTS = (".jpg", ".jpeg", ".png")
VIDEO_EXTS = (".mp4", ".m4v", ".mkv", ".webm")
AUDIO_EXTS = (".mp3", ".m4a")
DOC_EXTS = (".pdf",)
TEXT_EXTS = (".md",)
MEDIA_EXTS = IMAGE_EXTS + VIDEO_EXTS + AUDIO_EXTS + DOC_EXTS + TEXT_EXTS

__all__ = [
    "AUDIO_EXTS",
    "DOC_EXTS",
    "IMAGE_EXTS",
    "MEDIA_EXTS",
    "TEXT_EXTS",
    "VIDEO_EXTS",
]
