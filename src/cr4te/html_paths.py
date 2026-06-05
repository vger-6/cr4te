from __future__ import annotations

from pathlib import Path
from typing import Protocol

from .utils import path_utils

__all__ = [
    "FILE_TREE_DEPTH",
    "build_path_to_root",
    "build_rel_creator_html_path",
    "build_rel_project_html_path",
]

FILE_TREE_DEPTH = 4


class CreatorPathTarget(Protocol):
    name: str


class ProjectPathTarget(Protocol):
    title: str


def build_path_to_root(page_path: Path, output_dir: Path) -> str:
    relative_path = path_utils.relative_path_from(output_dir, page_path.parent).as_posix()
    return "" if relative_path == "." else f"{relative_path}/"


def build_rel_creator_html_path(creator: CreatorPathTarget) -> Path:
    return path_utils.build_unique_path(Path("creator", creator.name).with_suffix(".html"), FILE_TREE_DEPTH)


def build_rel_project_html_path(creator: CreatorPathTarget, project: ProjectPathTarget) -> Path:
    return path_utils.build_unique_path(Path("project", creator.name, project.title).with_suffix(".html"), FILE_TREE_DEPTH)
