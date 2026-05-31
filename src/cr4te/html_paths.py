from __future__ import annotations

from pathlib import Path
from typing import Protocol

from .utils import path_utils

__all__ = [
    "FILE_TREE_DEPTH",
    "HTML_PATH_TO_ROOT",
    "build_rel_creator_html_path",
    "build_rel_project_html_path",
]

FILE_TREE_DEPTH = 4
HTML_PATH_TO_ROOT = path_utils.get_path_to_root(FILE_TREE_DEPTH + 1)


class CreatorPathTarget(Protocol):
    name: str


class ProjectPathTarget(Protocol):
    title: str


def build_rel_creator_html_path(creator: CreatorPathTarget) -> Path:
    return path_utils.build_unique_path(Path("creator", creator.name).with_suffix(".html"), FILE_TREE_DEPTH)


def build_rel_project_html_path(creator: CreatorPathTarget, project: ProjectPathTarget) -> Path:
    return path_utils.build_unique_path(Path("project", creator.name, project.title).with_suffix(".html"), FILE_TREE_DEPTH)
