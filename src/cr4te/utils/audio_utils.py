from pathlib import Path

__all__ = ["get_audio_duration_seconds"]


def get_audio_duration_seconds(audio_path: Path) -> float:
    from mutagen import File as MutagenFile

    audio = MutagenFile(str(audio_path))
    if not audio or not audio.info:
        raise ValueError("Audio duration metadata is unavailable")
    return float(audio.info.length)
