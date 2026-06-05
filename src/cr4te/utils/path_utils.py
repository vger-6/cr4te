import hashlib
import os
from pathlib import Path

__all__ = ["relative_path_from", "build_unique_path", "tag_path"]


def relative_path_from(file_path: Path, base_path: Path) -> Path:
    file_path = file_path.resolve()
    base_path = base_path.resolve()

    return Path(os.path.relpath(file_path, base_path))


def build_unique_path(input_path: Path, depth: int = 4) -> Path:
    """
    Build a unique path based on a SHA-1 hash of the input path.

    Parameters:
        input_path (Path): The original relative path.
        depth (int): Number of directory levels (each 2 characters). Must be 1-20.

    Returns:
        Path: A unique, nested path ending with the hashed filename + original suffix.
    """
    if not (1 <= depth <= 20):
        raise ValueError("depth must be between 1 and 20 (inclusive)")

    original_suffix = input_path.suffix
    hash_input = input_path.as_posix()
    sha1 = hashlib.sha1(hash_input.encode("utf-8")).hexdigest()

    chunks = [sha1[i * 2: i * 2 + 2] for i in range(depth)]
    remaining = sha1[depth * 2:] + original_suffix
    chunks.append(remaining)

    return Path(*chunks)


def tag_path(input_path: Path, tag: str) -> Path:
    return input_path.with_name(f"{input_path.stem}_{tag}{input_path.suffix}")
