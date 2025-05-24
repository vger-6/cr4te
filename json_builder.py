import json
from enum import Enum
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from collections import defaultdict

from PIL import Image

from enums.image_sample_strategy import ImageSampleStrategy

__all__ = ["build_creator_json_files", "clean_creator_json_files"]

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
    if readme_file.exists() and readme_file.is_file():
        return readme_file.read_text(encoding='utf-8').strip()
    return ""

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
            
def _build_media_map(project_dir: Path, input_path: Path, compiled_media_rules: Dict) -> Dict[str, Dict]:
    media_map = defaultdict(lambda: {"images": [], "videos": [], "documents": [], "audio": [], "is_root": False})

    for file in project_dir.rglob("*"):
        if not file.is_file():
            continue

        rel_path_posix = file.relative_to(project_dir).as_posix()
        rel_to_input = file.relative_to(input_path)

        # Apply global exclusions
        if compiled_media_rules["global_exclude_re"].search(rel_path_posix):
            continue

        is_root = file.parent.resolve() == project_dir.resolve()
        folder_key = str(file.parent.relative_to(project_dir)) or project_dir.name

        if compiled_media_rules["video_include_re"].match(rel_path_posix) and not compiled_media_rules["video_exclude_re"].search(rel_path_posix):
            media_map[folder_key]["videos"].append(str(rel_to_input))
        elif compiled_media_rules["audio_include_re"].match(rel_path_posix) and not compiled_media_rules["audio_exclude_re"].search(rel_path_posix):
            media_map[folder_key]["audio"].append(str(rel_to_input))
        elif compiled_media_rules["image_include_re"].match(rel_path_posix) and not compiled_media_rules["image_exclude_re"].search(rel_path_posix):
            media_map[folder_key]["images"].append(str(rel_to_input))
        elif compiled_media_rules["document_include_re"].match(rel_path_posix) and not compiled_media_rules["document_exclude_re"].search(rel_path_posix):
            media_map[folder_key]["documents"].append(str(rel_to_input))
        else:
            continue

        media_map[folder_key]["is_root"] = is_root

    return media_map

def _collect_creator_projects(creator_path: Path, existing_data: Dict, input_path: Path, compiled_media_rules: Dict) -> List[Dict]:
    existing_projects = {p["title"]: p for p in existing_data.get("projects", []) if "title" in p}
    
    projects_data = []
    for project_dir in sorted(creator_path.iterdir()):
        if not project_dir.is_dir() or compiled_media_rules["global_exclude_re"].search(project_dir.name):
            continue

        project_title = project_dir.name.strip()
        project_data = existing_projects.get(project_title, {})
        existing_media_groups = {g.get("folder_name"): g for g in project_data.get("media_groups", []) if "folder_name" in g}

        media_map = _build_media_map(project_dir, input_path, compiled_media_rules)
            
        # Build media_groups list from the grouped map
        media_groups = []
        for folder_name, group in media_map.items():
            existing_media_group = existing_media_groups.get(folder_name, {})
            
            sampled_images = _sample_images(
                group["images"],
                compiled_media_rules.get("image_gallery_max", 20),
                compiled_media_rules.get("image_gallery_sample_strategy", ImageSampleStrategy.SPREAD)
            )
            
            media_group = {
                "is_root": group["is_root"],
                "videos": sorted(group["videos"]),
                "featured_videos": existing_media_group.get("featured_videos", None),
                "video_label": existing_media_group.get("video_label", None),
                "audio": sorted(group["audio"]),
                "featured_audio": existing_media_group.get("featured_audio", None),
                "audio_label": existing_media_group.get("audio_label", None),
                "images": sampled_images,
                "featured_images": existing_media_group.get("featured_images", None),
                "image_label": existing_media_group.get("image_label", None),
                "documents": group["documents"],
                "featured_documents": existing_media_group.get("featured_documents", None),
                "document_label": existing_media_group.get("document_label", None),
                "folder_name": folder_name
            }
            
            media_groups.append(media_group)
            
        # Find thumbnail
        all_images = [p for p in project_dir.rglob("*.jpg") if not compiled_media_rules["global_exclude_re"].search(p.name)]
        poster_re = compiled_media_rules.get("project_cover_image_re")
        poster_candidates = [p for p in all_images if poster_re and poster_re.match(p.name)]

        thumbnail_path = ""
        if poster_candidates:
            thumbnail_path = str(poster_candidates[0].relative_to(input_path))
        else:
            poster = _find_image_by_orientation(all_images, Orientation.LANDSCAPE)  # Fallback: heuristic
            if poster:
                thumbnail_path = str(poster.relative_to(input_path))

        project_data = {
            "title": project_title,
            "release_date": _validate_date_string(project_data.get("release_date", "")),
            "thumbnail": thumbnail_path,
            "featured_thumbnail": project_data.get("featured_thumbnail", None),
            "info": _read_readme_text(project_dir) or project_data.get("info", ""),
            "media_groups": media_groups,
            "tags": project_data.get("tags", [])
        }
        
        projects_data.append(project_data)

    return projects_data
        
def _is_collaboration(name: str, separator: Optional[str]) -> bool:
    if not separator:
        return False
    return separator in name
    
def _load_existing_json(json_path: Path) -> Dict:
    if json_path.exists():
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def _build_creator_json(creator_path: Path, input_path: Path, compiled_media_rules: Dict) -> Dict:
    creator_name = creator_path.name
    existing_data = _load_existing_json(creator_path / "cr4te.json")
    
    # Find portrait
    # TODO: DRY out code duplication. See: collect_projects_data
    all_images = [p for p in creator_path.rglob("*.jpg") if not compiled_media_rules["global_exclude_re"].search(p.name)]
    portrait_re = compiled_media_rules.get("creator_profile_image_re")
    portrait_candidates = [p for p in all_images if portrait_re and portrait_re.match(p.name)]

    portrait_path = ""
    if portrait_candidates:
        portrait_path = str(portrait_candidates[0].relative_to(input_path))
    else:
        portrait = _find_image_by_orientation(all_images, Orientation.PORTRAIT)  # Fallback: heuristic
        if portrait:
            portrait_path = str(portrait.relative_to(input_path))

    separator = compiled_media_rules.get("collaboration_separator", None)
    is_collab = _is_collaboration(creator_name, separator)
    creator_json = {
        "name": creator_name,
        "is_collaboration": existing_data.get("is_collaboration", is_collab),
        "born_or_founded": _validate_date_string(existing_data.get("born_or_founded", "")),
        "active_since": _validate_date_string(existing_data.get("active_since", "")),
        "nationality": existing_data.get("nationality", ""),
        "aliases": existing_data.get("aliases", []),
        "portrait": portrait_path,
        "featured_portrait": existing_data.get("featured_portrait", None),
        "info": _read_readme_text(creator_path) or existing_data.get("info", ""),
        "tags": existing_data.get("tags", []),
        "projects": _collect_creator_projects(creator_path, existing_data, input_path, compiled_media_rules)
    }
    
    if is_collab:
        members = [name.strip() for name in creator_name.split(separator)]
        creator_json["members"] = existing_data.get("members", members)
    else:
        creator_json["members"] = []
    
    return creator_json
    
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
            
def build_creator_json_files(input_path: Path, compiled_media_rules: Dict):
    all_creators = []

    for creator in sorted(input_path.iterdir()):
        if not creator.is_dir() or compiled_media_rules["global_exclude_re"].search(creator.name):
            continue
        print(f"Processing creator: {creator.name}")
        creator_json = _build_creator_json(creator, input_path, compiled_media_rules)
        all_creators.append(creator_json)

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

