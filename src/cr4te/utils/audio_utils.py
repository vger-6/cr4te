import logging
from pathlib import Path

logger = logging.getLogger(__name__)

__all__ = ["get_audio_duration_seconds"]


def get_audio_duration_seconds(audio_path: Path) -> float:
    """
    Returns the duration of the given audio file in seconds,
    or 0 if the duration cannot be determined.
    """
    try:
        from mutagen import File as MutagenFile

        audio = MutagenFile(str(audio_path))
        if audio and audio.info:
            return float(audio.info.length)
    except Exception as e:
        logger.warning(f"Could not read duration for {audio_path}: {e}")
    return 0
