import json
import re
from enum import Enum
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime
from collections import defaultdict

from PIL import Image
from pydantic import ValidationError

import constants
import utils.json_utils as json_utils
import utils.text_utils as text_utils
import utils.image_utils as image_utils
from enums.orientation import Orientation
from context.json_context import JsonBuildContext
from validators.cr4te_schema import Creator as CreatorSchema

__all__ = ["build_creator_json_files", "clean_creator_json_files"]

IMAGE_EXTS = (".jpg", ".jpeg", ".png")
VIDEO_EXTS = (".mp4", ".m4v")
AUDIO_EXTS = (".mp3", ".m4a")
DOC_EXTS = (".pdf",)
TEXT_EXTS = (".md",)

# TODO: improve this method and move it to date_utils.py
def _validate_date_string(date_str: str) -> str:
    """Ensures the date is in yyyy-mm-dd format, or returns empty string if invalid."""
    if not date_str or not isinstance(date_str, str):
        return ""
    try:
        parsed_date = datetime.strptime(date_str.strip(), "%Y-%m-%d")
        return parsed_date.strftime("%Y-%m-%d")  # Normalize
    except ValueError:
        return ""
        
def _validate_creator(creator: Dict) -> None:
    try:
        CreatorSchema(**creator)
    except ValidationError as e:
        name = creator.get("name", "<unknown>")
        error_lines = [f"[{name}] {err['loc'][0]}: {err['msg']}" for err in e.errors()]
        formatted = "\n".join(error_lines)
        raise ValueError(f"Validation failed for creator '{name}':\n{formatted}")
    
def _find_all_images(root: Path, exclude_prefix: str) -> List[Path]:
    return [
        p for p in root.rglob("*")
        if p.suffix.lower() in IMAGE_EXTS and not p.name.startswith(exclude_prefix)
    ]
    
def _find_image_by_name(image_paths: List[Path], name: str) -> Optional[Path]:
    for image_path in image_paths:
        if image_path.stem.lower() == name.lower():
            return image_path
    return None
    
def _select_best_image(image_paths: List[Path], name: str, orientation_fallback: Orientation) -> Optional[Path]:
    """
    Selects the best image from a list:
    - First, tries to find an image matching the given name.
    - If not found, tries to find an image matching the specified orientation.
    - If both fail, returns the first image in the list.
    - Returns None if the image list is empty.
    """
    if not image_paths:
        return None

    return (
        _find_image_by_name(image_paths, name)
        or _find_image_by_orientation(image_paths, orientation_fallback)
        or image_paths[0]
    )

def _find_image_by_orientation(image_paths: List[Path], orientation: Orientation) -> Optional[Path]:
    for image_path in sorted(image_paths, key=lambda x: x.name):
        if orientation == image_utils.infer_image_orientation(image_path):
            return image_path
    return None
    
def _build_media_map(ctx: JsonBuildContext, media_dir: Path) -> Dict[str, Dict]:
    media_map = defaultdict(lambda: {
        "videos": [],
        "tracks": [],
        "images": [],
        "documents": [],
        "texts": [],
        "is_root": False
    })
    
    # Helper to check max depth
    def is_within_search_depth(path: Path) -> bool:
        return ctx.max_search_depth is None or len(path.relative_to(media_dir).parts) <= ctx.max_search_depth

    for media_path in (
        p for p in media_dir.rglob("*")
        if p.is_file()
        and is_within_search_depth(p)
        and not p.name.startswith(ctx.global_exclude_prefix)
    ):
        suffix = media_path.suffix.lower()
        stem = media_path.stem.lower()
        rel_to_input = media_path.relative_to(ctx.input_dir)
        is_root = media_path.parent.resolve() == media_dir.resolve()
        rel_dir_key = str(media_path.parent.relative_to(ctx.input_dir)) or media_dir.name

        if suffix in VIDEO_EXTS:
            media_map[rel_dir_key]["videos"].append(str(rel_to_input))
        elif suffix in AUDIO_EXTS:
            media_map[rel_dir_key]["tracks"].append(str(rel_to_input))
        elif suffix in IMAGE_EXTS and stem not in (ctx.cover_basename, ctx.portrait_basename):
            media_map[rel_dir_key]["images"].append(str(rel_to_input))
        elif suffix in DOC_EXTS:
            media_map[rel_dir_key]["documents"].append(str(rel_to_input))
        elif suffix in TEXT_EXTS and media_path.name.lower() != ctx.readme_file_name.lower():
            media_map[rel_dir_key]["texts"].append(str(rel_to_input))

        media_map[rel_dir_key]["is_root"] = is_root

    return media_map
    
def _build_media_groups(ctx: JsonBuildContext, media_dir: Path, existing_media_groups: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    media_groups = []
    media_map = _build_media_map(ctx, media_dir)
    #existing_media_groups_by_name = {g["folder_path"]: g for g in existing_media_groups if "folder_path" in g}

    for rel_dir_path, media in media_map.items():
        #existing_media_group = existing_media_groups_by_name.get(folder_path, {})

        media_group = {
            "is_root": media["is_root"],
            "videos": sorted(media["videos"]),
            "tracks": sorted(media["tracks"]),
            "images": sorted(media["images"]),
            "documents": sorted(media["documents"]),
            "texts": sorted(media["texts"]),
            "folder_path": rel_dir_path
        }

        media_groups.append(media_group)

    return media_groups

def _collect_creator_projects(ctx: JsonBuildContext, creator_dir: Path, creator: Dict) -> List[Dict]:
    existing_projects = {p["title"]: p for p in creator.get("projects", []) if "title" in p}
    
    projects = []
    for project_dir in sorted(creator_dir.iterdir()):
        if not project_dir.is_dir() or project_dir.name.startswith((ctx.global_exclude_prefix, ctx.metadata_folder_name)):
            continue

        project_title = project_dir.name.strip()
        
        existing_project = existing_projects.get(project_title, {})

        # Find cover
        all_images = _find_all_images(project_dir, ctx.global_exclude_prefix)
        cover = _select_best_image(all_images, ctx.cover_basename, Orientation.LANDSCAPE)

        project = {
            "title": project_title,
            "release_date": _validate_date_string(existing_project.get("release_date", "")),
            "cover": str(cover.relative_to(ctx.input_dir)) if cover else "",
            "info": text_utils.read_text(project_dir / ctx.readme_file_name) or existing_project.get("info", ""),
            "media_groups": _build_media_groups(ctx, project_dir, existing_project.get("media_groups", [])),
            "tags": existing_project.get("tags", [])
        }
        
        projects.append(project)

    return projects
    
def _build_creator_media_groups(ctx: JsonBuildContext, creator_dir: Path, existing_media_groups: List[Dict]) -> List[Dict]:
    media_groups = []

    # Metadata folder media
    metadata_dir = creator_dir / ctx.metadata_folder_name
    if metadata_dir.exists():
        media_groups = _build_media_groups(ctx, metadata_dir, existing_media_groups)

    # Root-level media (shallow only)
    shallow_ctx = JsonBuildContext(input_dir=ctx.input_dir, media_rules={**ctx.media_rules, "max_search_depth": 1})
    media_groups.extend(_build_media_groups(shallow_ctx, creator_dir, existing_media_groups))

    return media_groups
        
def _is_collaboration(name: str, separators: Optional[List[str]]) -> bool:
    if not separators:
        return False
    return any(sep in name for sep in separators)
    
def _load_existing_json(json_path: Path) -> Dict:
    if json_path.exists():
        return json_utils.load_json(json_path)
    return {}

def _build_creator(ctx: JsonBuildContext, creator_dir: Path) -> Dict[str, Any]:
    creator_name = creator_dir.name
    existing_creator = _load_existing_json(creator_dir / constants.CR4TE_JSON_FILE_NAME)
    
    # Find portrait
    all_images = _find_all_images(creator_dir, ctx.global_exclude_prefix)
    portrait = (
        _select_best_image(all_images, ctx.portrait_basename, Orientation.PORTRAIT) 
        if ctx.auto_find_portrait 
        else _find_image_by_name(all_images, ctx.portrait_basename)
    )
    
    separators = ctx.collaboration_separators
    is_collab = existing_creator.get("is_collaboration")
    if is_collab is None:
        is_collab = _is_collaboration(creator_name, separators)
    
    creator = {
        "name": creator_name,
        "is_collaboration": is_collab,
        "born_or_founded": _validate_date_string(existing_creator.get("born_or_founded", "")),
        "active_since": _validate_date_string(existing_creator.get("active_since", "")),
        "nationality": existing_creator.get("nationality", ""),
        "aliases": existing_creator.get("aliases", []),
        "portrait": str(portrait.relative_to(ctx.input_dir)) if portrait else "",
        "info": text_utils.read_text(creator_dir / ctx.readme_file_name) or existing_creator.get("info", ""),
        "tags": existing_creator.get("tags", []),
        "projects": _collect_creator_projects(ctx, creator_dir, existing_creator),
        "media_groups": _build_creator_media_groups(ctx, creator_dir, existing_creator.get("media_groups", [])),
        "collaborations": [],
    }
    
    if is_collab:
        members = [name.strip() for name in text_utils.multi_split(creator_name, separators)]
        creator["members"] = existing_creator.get("members", members)
    else:
        creator["members"] = []
    
    return creator
    
def _resolve_creator_collaborations(creators: List[Dict]) -> None:
    # Build collaboration map (name -> members)
    collaboration_map = {
        creator["name"]: creator["members"]
        for creator in creators
        if creator.get("is_collaboration") and creator.get("members")
    }

    # Add reverse links to solo creators
    for creator in creators:
        if not creator.get("is_collaboration"):
            auto_collabs = [
                name for name, members in collaboration_map.items()
                if creator["name"] in members
            ]
            manual_collabs = creator.get("collaborations", [])
            creator["collaborations"] = sorted(set(auto_collabs + manual_collabs))
            
def _write_json_files(creator_records: List[Tuple[Path, Dict]]) -> None:
    """
    Writes each creator's JSON data to <creator_dir>/cr4te.json.
    """
    for creator_dir, creator_data in creator_records:
        json_path = creator_dir / constants.CR4TE_JSON_FILE_NAME
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(creator_data, f, indent=2)
            
def build_creator_json_files(input_dir: Path, media_rules: Dict):
    ctx = JsonBuildContext(input_dir, media_rules)

    creator_records = []
    for creator_dir in sorted(ctx.input_dir.iterdir()):
        if not creator_dir.is_dir() or creator_dir.name.startswith(ctx.global_exclude_prefix):
            continue
        print(f"Processing creator: {creator_dir.name}")
        creator_data = _build_creator(ctx, creator_dir)
        creator_records.append((creator_dir, creator_data))

    _resolve_creator_collaborations([creator_data for _, creator_data in creator_records])
    
    for _, creator_data in creator_records:
        _validate_creator(creator_data)

    _write_json_files(creator_records)
    
def clean_creator_json_files(input_dir: Path, dry_run: bool = False) -> None:
    total = 0
    deleted = 0
    skipped = 0

    for creator_dir in input_dir.iterdir():
        if not creator_dir.is_dir():
            continue

        json_path = creator_dir / constants.CR4TE_JSON_FILE_NAME
        if json_path.exists():
            total += 1
            print(f"{'[DRY-RUN] ' if dry_run else ''}Deleting: {json_path}")
            if not dry_run:
                try:
                    json_path.unlink()
                    deleted += 1
                except Exception as e:
                    print(f"Error deleting {json_path}: {e}")
                    skipped += 1
        else:
            continue

    print("\nSummary:")
    print(f"\tTotal {constants.CR4TE_JSON_FILE_NAME} files found: {total}")
    print(f"\tDeleted: {deleted}")
    print(f"\tSkipped/errors: {skipped}")
    if dry_run:
        print("\t(Dry-run mode: no files were deleted)")

