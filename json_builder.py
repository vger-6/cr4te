import json
from enum import Enum
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from collections import defaultdict

from PIL import Image

from enums.image_sample_strategy import ImageSampleStrategy

class Orientation(Enum):
    PORTRAIT = "portrait"
    LANDSCAPE = "landscape"
    
def is_collaboration(name: str, separator: Optional[str]) -> bool:
    if not separator:
        return False
    return separator in name

def validate_date_string(date_str: str) -> str:
    """Ensures the date is in yyyy-mm-dd format, or returns empty string if invalid."""
    if not date_str or not isinstance(date_str, str):
        return ""
    try:
        parsed_date = datetime.strptime(date_str.strip(), "%Y-%m-%d")
        return parsed_date.strftime("%Y-%m-%d")  # Normalize
    except ValueError:
        return ""

def load_existing_json(json_path: Path) -> Dict:
    if json_path.exists():
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def read_readme_text(folder: Path) -> str:
    readme_file = folder / "README.md"
    if readme_file.exists() and readme_file.is_file():
        return readme_file.read_text(encoding='utf-8').strip()
    return ""

def find_image_by_orientation(images: List[Path], orientation: Orientation = Orientation.PORTRAIT) -> Optional[Path]:
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

def sample_images(images: List[str], max_images: int, strategy: ImageSampleStrategy) -> List[str]:
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

def collect_projects_data(creator_path: Path, existing_data: Dict, input_path: Path, compiled_media_rules: Dict) -> List[Dict]:
    projects_data = []

    for project_dir in sorted(creator_path.iterdir()):
        if not project_dir.is_dir() or compiled_media_rules["GLOBAL_EXCLUDE_RE"].search(project_dir.name):
            continue

        project_title = project_dir.name.strip()
        existing_projects = existing_data.get("projects", [])
        project_data = next((s for s in existing_projects if s.get("title") == project_title), {})

        media_map = defaultdict(lambda: {"images": [], "videos": []})
        image_count = 0
        video_count = 0

        for file in project_dir.rglob("*"):
            if not file.is_file():
                continue
            
            rel_path_posix = file.relative_to(project_dir).as_posix()
            rel_to_input = file.relative_to(input_path)

            # 1. Apply global exclusions
            if compiled_media_rules["GLOBAL_EXCLUDE_RE"].search(rel_path_posix):
                continue
                
            is_root = file.parent.resolve() == project_dir.resolve()
            folder_key = str(file.parent.relative_to(project_dir)) or project_title

            # 2. Match video
            if compiled_media_rules["VIDEO_INCLUDE_RE"].match(rel_path_posix) and not compiled_media_rules["VIDEO_EXCLUDE_RE"].search(rel_path_posix):
                media_map[folder_key]["videos"].append(str(rel_to_input))
                media_map[folder_key]["is_root"] = is_root
                video_count += 1
                continue

            # 3. Match image
            if compiled_media_rules["IMAGE_INCLUDE_RE"].match(rel_path_posix) and not compiled_media_rules["IMAGE_EXCLUDE_RE"].search(rel_path_posix):
                media_map[folder_key]["images"].append(str(rel_to_input))
                media_map[folder_key]["is_root"] = is_root
                image_count += 1

        # Find thumbnail
        all_images = [p for p in project_dir.rglob("*.jpg") if not compiled_media_rules["GLOBAL_EXCLUDE_RE"].search(p.name)]
        poster_re = compiled_media_rules.get("POSTER_RE")
        poster_candidates = [p for p in all_images if poster_re and poster_re.match(p.name)]

        thumbnail_path = ""
        if poster_candidates:
            thumbnail_path = str(poster_candidates[0].relative_to(input_path))
        else:
            poster = find_image_by_orientation(all_images, Orientation.LANDSCAPE)  # Fallback: heuristic
            if poster:
                thumbnail_path = str(poster.relative_to(input_path))
                        
        # Build media_groups list from the grouped map
        media_groups = []
        for folder_name, group in media_map.items():
            sampled_images = sample_images(
                group["images"],
                compiled_media_rules.get("MAX_IMAGES", 20),
                compiled_media_rules.get("IMAGE_SAMPLE_STRATEGY", ImageSampleStrategy.SPREAD)
            )
            
            media_group = {
                "is_root": group["is_root"],
                "videos": group["videos"],
                "images": sampled_images,
                "folder_name": folder_name
            }
            
            media_groups.append(media_group)

        projects_data.append({
            "title": project_title,
            "release_date": validate_date_string(project_data.get("release_date", "")),
            "thumbnail": thumbnail_path,
            "info": read_readme_text(project_dir) or project_data.get("info", ""),
            "image_count": image_count,
            "video_count": video_count,
            "media_groups": media_groups,
            "tags": project_data.get("tags", [])
        })

    return projects_data

def build_creator_json(creator_path: Path, input_path: Path, compiled_media_rules: Dict) -> Dict:
    creator_name = creator_path.name
    existing_data = load_existing_json(creator_path / "cr4te.json")
    
    # Find portrait
    # TODO: DRY out code duplication. See: collect_projects_data
    all_images = [p for p in creator_path.rglob("*.jpg") if not compiled_media_rules["GLOBAL_EXCLUDE_RE"].search(p.name)]
    portrait_re = compiled_media_rules.get("PORTRAIT_RE")
    portrait_candidates = [p for p in all_images if portrait_re and portrait_re.match(p.name)]

    portrait_path = ""
    if portrait_candidates:
        portrait_path = str(portrait_candidates[0].relative_to(input_path))
    else:
        portrait = find_image_by_orientation(all_images, Orientation.PORTRAIT)  # Fallback: heuristic
        if portrait:
            portrait_path = str(portrait.relative_to(input_path))

    separator = compiled_media_rules.get("COLLABORATION_SEPARATOR", None)
    is_collab = is_collaboration(creator_name, separator)
    creator_json = {
        "name": creator_name,
        "is_collaboration": existing_data.get("is_collaboration", is_collab),
        "date_of_birth": validate_date_string(existing_data.get("date_of_birth", "")),
        "nationality": existing_data.get("nationality", ""),
        "aliases": existing_data.get("aliases", []),
        "portrait": portrait_path,
        "info": read_readme_text(creator_path) or existing_data.get("info", ""),
        "tags": existing_data.get("tags", []),
        "projects": collect_projects_data(creator_path, existing_data, input_path, compiled_media_rules)
    }
    
    if is_collab:
        members = [name.strip() for name in creator_name.split(separator)]
        creator_json["members"] = existing_data.get("members", members)
    else:
        creator_json["members"] = []
    
    return creator_json
            
def process_all_creators(input_path: Path, compiled_media_rules: Dict):
    all_creators = []

    for creator in sorted(input_path.iterdir()):
        if not creator.is_dir() or compiled_media_rules["GLOBAL_EXCLUDE_RE"].search(creator.name):
            continue
        print(f"Processing creator: {creator.name}")
        creator_json = build_creator_json(creator, input_path, compiled_media_rules)
        all_creators.append(creator_json)

    # Build collaboration map (name -> members)
    collaboration_map = {
        creator["name"]: creator["members"]
        for creator in all_creators
        if creator.get("is_collaboration") and creator.get("members")
    }
            
    # Add reverse links to solo creators
    for creator in all_creators:
        if not creator.get("is_collaboration"):
            auto_collabs = [
                name for name, members in collaboration_map.items()
                if creator["name"] in members
            ]
            manual_collabs = creator.get("collaborations", [])
            creator["collaborations"] = sorted(set(auto_collabs + manual_collabs))
        else:
            creator["collaborations"] = []

    # Write JSON files
    for creator in all_creators:
        json_path = input_path / creator["name"] / "cr4te.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(creator, f, indent=2)

