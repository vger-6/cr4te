import json
from enum import Enum
from pathlib import Path
from typing import List, Dict, Optional
from utils import is_collaboration, is_valid_entry
from PIL import Image
from datetime import datetime

class Orientation(Enum):
    PORTRAIT = "portrait"
    LANDSCAPE = "landscape"
    
def validate_date_string(date_str: str) -> str:
    """Ensures the date is in yyyy-mm-dd format, or returns empty string if invalid."""
    if not date_str or not isinstance(date_str, str):
        return ""
    try:
        parsed_date = datetime.strptime(date_str.strip(), "%Y-%m-%d")
        return parsed_date.strftime("%Y-%m-%d")  # Normalize
    except ValueError:
        return ""

def find_all_images(folder: Path) -> List[Path]:
    return sorted([p for p in folder.glob("*.jpg") if is_valid_entry(p)], key=lambda x: x.name)

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

def find_portrait(images: List[Path]) -> Optional[Path]:
    return find_image_by_orientation(images, Orientation.PORTRAIT)

def find_landscape(images: List[Path]) -> Optional[Path]:
    return find_image_by_orientation(images, Orientation.LANDSCAPE)

def get_evenly_distributed_images(image_dir: Path, input_path: Path, max_images: int = 10) -> List[str]:
    all_images = find_all_images(image_dir)
    relative_paths = [str(p.relative_to(input_path)) for p in all_images]
    total = len(relative_paths)

    if total <= max_images:
        return relative_paths

    step = total / max_images
    indices = [int(i * step) for i in range(max_images)]
    selected = [relative_paths[i] for i in indices]
    return selected

def collect_projects_data(creator_path: Path, existing_data: Dict, input_path: Path) -> List[Dict]:
    projects_data = []

    for project_dir in sorted(creator_path.iterdir()):
        if not project_dir.is_dir() or not is_valid_entry(project_dir):
            continue

        project_title = project_dir.name.strip()
        existing_projects = existing_data.get("projects", [])
        project_data = next((s for s in existing_projects if s.get("title") == project_title), {})

        thumbnail_path = ""
        image_count = 0
        image_groups = []
        
        # Try to find a suitable thumbnail directly in the project directory
        project_level_images = find_all_images(project_dir)
        if project_level_images:
            landscape = find_landscape(project_level_images)
            if landscape:
                thumbnail_path = str(landscape.relative_to(input_path))
        
        # Scan subfolders for image groups
        for subfolder in sorted(project_dir.iterdir()):
            if not subfolder.is_dir() or not is_valid_entry(subfolder):
                continue
        
            images = find_all_images(subfolder)
            if not images:
                continue
        
            label = subfolder.name.replace("_", " ").title()
            selected = get_evenly_distributed_images(subfolder, input_path)
        
            if selected:
                image_groups.append({
                    "label": label,
                    "images": selected
                })
                image_count += len(images)

                # If thumbnail is still missing, grab one from the first group
                if not thumbnail_path:
                    landscape = find_landscape(images)
                    if landscape:
                        thumbnail_path = str(landscape.relative_to(input_path))

        # Find videos
        video_files = sorted([p for p in project_dir.glob("*.mp4") if is_valid_entry(p)])
        video_paths = [str(p.relative_to(input_path)) for p in video_files]
        video_count = len(video_files)

        projects_data.append({
            "title": project_title,
            "release_date": validate_date_string(project_data.get("release_date", "")),
            "thumbnail": thumbnail_path,
            "info": read_readme_text(project_dir) or project_data.get("info", ""),
            "video_count": video_count,
            "image_count": image_count,
            "videos": video_paths,
            "tags": project_data.get("tags", []),
            "image_groups": image_groups
        })

    return projects_data

def build_creator_json(creator_path: Path, input_path: Path) -> Dict:
    creator_name = creator_path.name
    existing_data = load_existing_json(creator_path / "cr4te.json")
    all_images = [p for p in creator_path.rglob("*.jpg") if is_valid_entry(p)]
    portrait_path = ""
    if all_images:
        portrait = find_portrait(all_images)
        portrait_path = str(portrait.relative_to(input_path)) if portrait else ""

    is_collab = is_collaboration(creator_name)
    creator_json = {
        "name": creator_name,
        "is_collaboration": existing_data.get("is_collaboration", is_collab),
        "portrait": portrait_path,
        "info": read_readme_text(creator_path) or existing_data.get("info", ""),
        "tags": existing_data.get("tags", []),
        "projects": collect_projects_data(creator_path, existing_data, input_path)
    }

    if is_collab:
        members = [name.strip() for name in creator_name.split("&")]
        creator_json["members"] = existing_data.get("members", members)
    else:
        dob = existing_data.get("date_of_birth", "")
        creator_json["date_of_birth"] = validate_date_string(dob)
    
    return creator_json

def process_all_creators(input_path: Path):
    creator_list = []
    for creator in sorted(input_path.iterdir()):
        if not creator.is_dir() or not is_valid_entry(creator):
            continue
        print(f"Processing creator: {creator.name}")
        creator_json = build_creator_json(creator, input_path)
        json_path = creator / "cr4te.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(creator_json, f, indent=2)
        creator_list.append(creator_json)
    return creator_list
