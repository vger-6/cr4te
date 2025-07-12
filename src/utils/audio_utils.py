from pathlib import Path

from mutagen import File as MutagenFile

# TODO: use logging instead of print()

__all__ = ["get_audio_duration_seconds"]

def get_audio_duration_seconds(audio_path: Path) -> int:
    """
    Returns the duration of the given audio file in seconds,
    or 0 if the duration cannot be determined.
    """
    try:
        audio = MutagenFile(str(audio_path))
        if audio and audio.info:
            return int(audio.info.length)
    except Exception as e:
        print(f"Warning: could not read duration for {audio_path}: {e}")
    return 0
