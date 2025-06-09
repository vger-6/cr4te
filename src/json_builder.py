import json
from enum import Enum
from pathlib import Path
from typing import List, Dict, Optional, Any, Pattern
from datetime import datetime
from collections import defaultdict

from PIL import Image

from . import utils
from .enums.image_sample_strategy import ImageSampleStrategy

__all__ = ["build_creator_json_files", "clean_creator_json_files"]

IMAGE_EXTS = (".jpg", ".jpeg", ".png")
VIDEO_EXTS = (".mp4", ".m4v")
AUDIO_EXTS = (".mp3", ".m4a")
DOC_EXTS = (".pdf",)
TEXT_EXTS = (".md",)

class Orientation(Enum):
    PORTRAIT = "portrait"
    LANDSCAPE = "landscape"
    
def _validate_date_string(date_str: str) -> str:
    """Ensures the date is in yyyy-mm-dd format, or returns empty string if invalid."""
    if not date_str or not isinstance(date_str, str):
        return ""
    try:
        parsed_date = datetime.strptime(date_str.strip(), "%Y-%m-%d")
        return parsed_date.strftime("%Y-%m-%d")  # Normalize
    except ValueError:
        return ""

def _read_readme_text(folder: Path) -> str:
    readme_file = folder / "README.md"
    return utils.read_text(readme_file)
    
def _find_all_images(root: Path, exclude_prefix: str) -> List[Path]:
    return [
        p for p in root.rglob("*")
        if p.suffix.lower() in IMAGE_EXTS and not p.name.startswith(exclude_prefix)
    ]
    
def _select_best_image(images: List[Path], image_name: str, orientation_fallback: Orientation) -> Optional[Path]:
    for image in images:
        if image.stem.lower() == image_name.lower() and image.suffix.lower() in IMAGE_EXTS:
            return image

    return _find_image_by_orientation(images, orientation_fallback)

def _find_image_by_orientation(images: List[Path], orientation: Orientation = Orientation.PORTRAIT) -> Optional[Path]:
    for img_path in sorted(images, key=lambda x: x.name):
        try:
            with Image.open(img_path) as img:
                match orientation:
                    case Orientation.PORTRAIT:
                        if img.height > img.width:
                            return img_path
                    case Orientation.LANDSCAPE:
                        if img.width > img.height:
                            return img_path
        except Exception as e:
            print(f"Error checking image orientation for {img_path}: {e}")
    return None

def _sample_images(images: List[str], max_images: int, strategy: ImageSampleStrategy) -> List[str]:
    if max_images <= 0:
        return []

    sorted_images = sorted(images)

    match strategy:
        case ImageSampleStrategy.ALL:
            return sorted_images
        case _ if len(sorted_images) <= max_images:
            return sorted_images
        case ImageSampleStrategy.HEAD:
            return sorted_images[:max_images]
        case ImageSampleStrategy.SPREAD:
            step = len(sorted_images) / max_images
            return [sorted_images[int(i * step)] for i in range(max_images)]
        case _:
            return sorted_images  # fallback
            
def _build_media_map(media_folder: Path, input_path: Path, media_rules: Dict) -> Dict[str, Dict]:
    media_map = defaultdict(lambda: {
        "videos": [],
        "tracks": [],
        "images": [],
        "documents": [],
        "texts": [],
        "is_root": False
    })
    
    max_depth = media_rules["max_depth"]

    # Helper to check max depth
    def is_within_max_depth(path: Path) -> bool:
        return max_depth is None or len(path.relative_to(media_folder).parts) <= max_depth

    for file in media_folder.rglob("*"):
        if not file.is_file():
            continue
        if not is_within_max_depth(file):
            continue
        if file.name.startswith(media_rules["global_exclude_prefix"]):
            continue

        suffix = file.suffix.lower()
        stem = file.stem.lower()
        rel_to_input = file.relative_to(input_path)
        is_root = file.parent.resolve() == media_folder.resolve()
        folder_key = str(file.parent.relative_to(input_path)) or media_folder.name

        if suffix in VIDEO_EXTS:
            media_map[folder_key]["videos"].append(str(rel_to_input))
        elif suffix in AUDIO_EXTS:
            media_map[folder_key]["tracks"].append(str(rel_to_input))
        elif suffix in IMAGE_EXTS and stem not in ("cover", "portrait"):
            media_map[folder_key]["images"].append(str(rel_to_input))
        elif suffix in DOC_EXTS:
            media_map[folder_key]["documents"].append(str(rel_to_input))
        elif suffix in TEXT_EXTS and stem != "readme":
            media_map[folder_key]["texts"].append(str(rel_to_input))

        media_map[folder_key]["is_root"] = is_root

    return media_map
    
def _build_media_groups(media_folder: Path, input_path: Path, media_rules: Dict, existing_media_groups: List[Dict[str, any]]) -> List[Dict[str, Any]]:
    media_groups = []
    media_map = _build_media_map(media_folder, input_path, media_rules)
    existing_media_groups_by_name = {g["folder_path"]: g for g in existing_media_groups if "folder_path" in g}

    for folder_path, media in media_map.items():
        existing_media_group = existing_media_groups_by_name.get(folder_path, {})

        sampled_images = _sample_images(
            media["images"],
            media_rules["image_gallery_max"],
            media_rules["image_gallery_sample_strategy"]
        )

        media_group = {
            "is_root": media["is_root"],
            "videos": sorted(media["videos"]),
            "featured_videos": existing_media_group.get("featured_videos"),
            "tracks": sorted(media["tracks"]),
            "featured_tracks": existing_media_group.get("featured_tracks"),
            "images": sampled_images,
            "featured_images": existing_media_group.get("featured_images"),
            "documents": media["documents"],
            "featured_documents": existing_media_group.get("featured_documents"),
            "texts": media["texts"],
            "featured_texts": existing_media_group.get("featured_texts"),
            "folder_path": folder_path
        }

        media_groups.append(media_group)

    return media_groups

def _collect_creator_projects(creator_path: Path, creator: Dict, input_path: Path, media_rules: Dict) -> List[Dict]:
    existing_projects = {p["title"]: p for p in creator.get("projects", []) if "title" in p}
    
    projects = []
    for project_dir in sorted(creator_path.iterdir()):
        if not project_dir.is_dir() or project_dir.name.startswith((media_rules["global_exclude_prefix"], media_rules["metadata_folder_name"])):
            continue

        project_title = project_dir.name.strip()
        
        existing_project = existing_projects.get(project_title, {})

        # Find cover
        all_images = _find_all_images(project_dir, media_rules["global_exclude_prefix"])
        cover = _select_best_image(all_images, "cover", Orientation.LANDSCAPE)

        project = {
            "title": project_title,
            "is_enabled": existing_project.get("is_enabled", True),
            "release_date": _validate_date_string(existing_project.get("release_date", "")),
            "cover": str(cover.relative_to(input_path)) if cover else "",
            "featured_cover": existing_project.get("featured_cover"),
            "info": _read_readme_text(project_dir) or existing_project.get("info", ""),
            "media_groups": _build_media_groups(project_dir, input_path, media_rules, existing_project.get("media_groups", [])),
            "tags": existing_project.get("tags", [])
        }
        
        projects.append(project)

    return projects
        
def _is_collaboration(name: str, separator: Optional[str]) -> bool:
    if not separator:
        return False
    return separator in name
    
def _load_existing_json(json_path: Path) -> Dict:
    if json_path.exists():
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def _build_creator(creator_path: Path, input_path: Path, media_rules: Dict) -> Dict[str, Any]:
    creator_name = creator_path.name
    existing_creator = _load_existing_json(creator_path / "cr4te.json")
    
    # Find portrait
    all_images = _find_all_images(creator_path, media_rules["global_exclude_prefix"])
    portrait = _select_best_image(all_images, "portrait", Orientation.PORTRAIT)
    
    separator = media_rules["collaboration_separator"]
    is_collab = existing_creator.get("is_collaboration")
    if is_collab is None:
        is_collab = _is_collaboration(creator_name, separator)
        
    media_groups = []
    if (creator_path / media_rules["metadata_folder_name"]).exists():
        media_groups = _build_media_groups(creator_path / media_rules["metadata_folder_name"], input_path, media_rules, existing_creator.get("media_groups", []))
    
    media_groups.extend(_build_media_groups(creator_path, input_path, {**media_rules, "max_depth": 0}, existing_creator.get("media_groups", [])))
    
    creator = {
        "name": creator_name,
        "is_enabled": existing_creator.get("is_enabled", True),
        "is_collaboration": is_collab,
        "born_or_founded": _validate_date_string(existing_creator.get("born_or_founded", "")),
        "active_since": _validate_date_string(existing_creator.get("active_since", "")),
        "nationality": existing_creator.get("nationality", ""),
        "aliases": existing_creator.get("aliases", []),
        "portrait": str(portrait.relative_to(input_path)) if portrait else "",
        "featured_portrait": existing_creator.get("featured_portrait"),
        "info": _read_readme_text(creator_path) or existing_creator.get("info", ""),
        "tags": existing_creator.get("tags", []),
        "projects": _collect_creator_projects(creator_path, existing_creator, input_path, media_rules),
        "media_groups": media_groups,
    }
    
    if is_collab:
        members = [name.strip() for name in creator_name.split(separator)]
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
        else:
            creator["collaborations"] = []
            
def _write_json_files(creators: List[Dict], base_path: Path) -> None:
    """
    Writes each creator's JSON data to <base_path>/<creator_name>/cr4te.json.
    """
    for creator in creators:
        json_path = base_path / creator["name"] / "cr4te.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(creator, f, indent=2)
            
def build_creator_json_files(input_path: Path, media_rules: Dict):
    all_creators = []

    for creator_path in sorted(input_path.iterdir()):
        if not creator_path.is_dir() or creator_path.name.startswith(media_rules["global_exclude_prefix"]):
            continue
        print(f"Processing creator: {creator_path.name}")
        creator = _build_creator(creator_path, input_path, media_rules)
        all_creators.append(creator)

    _resolve_creator_collaborations(all_creators)

    _write_json_files(all_creators, input_path)
    
def clean_creator_json_files(input_path: Path, dry_run: bool = False) -> None:
    total = 0
    deleted = 0
    skipped = 0

    for creator in input_path.iterdir():
        if not creator.is_dir():
            continue

        json_path = creator / "cr4te.json"
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
    print(f"\tTotal cr4te.json files found: {total}")
    print(f"\tDeleted: {deleted}")
    print(f"\tSkipped/errors: {skipped}")
    if dry_run:
        print("\t(Dry-run mode: no files were deleted)")

