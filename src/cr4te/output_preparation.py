from __future__ import annotations

import shutil
from pathlib import Path

from .constants import CR4TE_CSS_DIR, CR4TE_FAVICON_PATH, CR4TE_JS_DIR, OUTPUT_THUMBNAILS_DIRNAME
from .html_context import HtmlBuildContext

__all__ = [
    "clear_output_folder",
    "copy_static_assets",
    "prepare_output_dirs",
]


def prepare_output_dirs(ctx: HtmlBuildContext) -> None:
    ctx.output_dir.mkdir(parents=True, exist_ok=True)
    ctx.assets_dir.mkdir(parents=True, exist_ok=True)
    ctx.html_dir.mkdir(parents=True, exist_ok=True)
    ctx.thumbs_dir.mkdir(parents=True, exist_ok=True)


def copy_static_assets(ctx: HtmlBuildContext) -> None:
    shutil.copytree(CR4TE_CSS_DIR, ctx.css_dir, dirs_exist_ok=True)
    shutil.copytree(CR4TE_JS_DIR, ctx.js_dir, dirs_exist_ok=True)
    shutil.copy2(CR4TE_FAVICON_PATH, ctx.assets_dir / CR4TE_FAVICON_PATH.name)


def clear_output_folder(output_dir: Path, clear_thumbnails: bool) -> None:
    for item in output_dir.iterdir():
        if clear_thumbnails or item.name != OUTPUT_THUMBNAILS_DIRNAME:
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
