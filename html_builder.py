import shutil
import json
import os
from pathlib import Path
from typing import List, Dict
from datetime import datetime
from enum import Enum
from collections import defaultdict

import markdown
from PIL import Image
from jinja2 import Environment, FileSystemLoader, select_autoescape

from utils import slugify, get_relative_path

__all__ = ["clear_output_folder", "build_html_pages"]

SCRIPT_DIR = Path(__file__).resolve().parent

# Setup Jinja2 environment
TEMPLATE_DIR = Path(__file__).parent / "templates"
env = Environment(
    loader=FileSystemLoader(str(TEMPLATE_DIR)),
    autoescape=select_autoescape(['html', 'xml'])
)

class ThumbType(Enum):
    THUMB = ("_thumb.jpg", 300)
    PORTRAIT = ("_portrait.jpg", 600)
    POSTER = ("_poster.jpg", 800)
    PROJECT = ("_project.jpg", 800)
    GALLERY = ("_gallery.jpg", 600)

    def __init__(self, suffix: str, height: int):
        self.suffix = suffix
        self.height = height

DEFAULT_IMAGES = {
    ThumbType.THUMB: "defaults/default_thumb.jpg",
    ThumbType.PORTRAIT: "defaults/default_portrait.jpg",
    ThumbType.POSTER: "defaults/default_poster.jpg",
    ThumbType.PROJECT: "defaults/default_poster.jpg",  # Reuse poster fallback
    ThumbType.GALLERY: "defaults/default_thumb.jpg"  # Reuse thumb fallback
}

def _render_markdown(text: str) -> str:
    return markdown.markdown(text, extensions=["extra"])
    
def _calculate_age(dob: datetime, date: datetime) -> str:
    try:
        age = date.year - dob.year - ((date.month, date.day) < (dob.month, dob.day))
        return str(age)
    except Exception as e:
        print(f"Error calculating age: {e}")
        return ""

def _get_creator_slug(creator: Dict) -> str:
    return slugify(creator['name'])
    
def _get_project_slug(creator: Dict, project: Dict) -> str:
    return slugify(f"{creator['name']}__{project['title']}")
               
def _create_thumbnail(input_root: Path, relative_path: Path, dest_dir: Path, thumb_type: ThumbType) -> Path:
    ext = thumb_type.suffix
    slug = slugify('__'.join(relative_path.parent.parts))
    thumb_path = dest_dir / slug / (relative_path.stem + ext)

    if not thumb_path.exists():
        thumb_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with Image.open(input_root / relative_path) as img:
                img.thumbnail((thumb_type.height, thumb_type.height))
                img.save(thumb_path, format='JPEG')
        except Exception as e:
            print(f"Error creating thumbnail for {relative_path}: {e}")

    return thumb_path

def _sort_project(project: Dict) -> tuple:
    release_date = project.get("release_date", "")
    has_date = bool(release_date)
    date_value = datetime.strptime(release_date, "%Y-%m-%d") if has_date else datetime.max
    title = project.get("title", "").lower()
    return (not has_date, date_value, title)
    
def _build_project_overview_page(projects: List[dict], input_path: Path, output_path: Path, html_settings: Dict):
    template = env.get_template("project_overview.html.j2")

    sorted_projects = sorted(projects, key=lambda p: p["title"].lower())

    rendered = template.render(
        projects=sorted_projects,
        html_settings=html_settings,
        poster_max_height=ThumbType.PROJECT.height,
    )

    output_path.mkdir(parents=True, exist_ok=True)
    with open(output_path / "projects.html", "w", encoding="utf-8") as f:
        f.write(rendered)

def _collect_all_tags(creators: List[Dict]) -> Dict[str, set[str]]:
    tags = defaultdict(set)
    for creator in creators:
        for tag in creator.get("tags", []):
            if ":" in tag:
                category, label = tag.split(":", 1)
                tags[category.strip()].add(label.strip())
            else:
                tags["Tag"].add(tag.strip())

        for project in creator.get("projects", []):
            for tag in project.get("tags", []):
                if ":" in tag:
                    category, label = tag.split(":", 1)
                    tags[category.strip()].add(label.strip())
                else:
                    tags["Tag"].add(tag.strip())
    return tags

def _build_tags_page(creators: list, output_path: Path, html_settings: dict):
    print("Generating tags page...")

    template = env.get_template("tags.html.j2")

    tags = _collect_all_tags(creators)

    output_html = template.render(
        html_settings=html_settings,
        tags=tags,
    )

    tag_file = output_path / "tags.html"
    with open(tag_file, "w", encoding="utf-8") as f:
        f.write(output_html)
        
def _create_symlink(input_root: Path, relative_path: Path, dest_dir: Path) -> str:
    ext = relative_path.suffix.lower()
    slug_parts = relative_path.parent.parts + (relative_path.stem,) 
    base = slugify('__'.join(slug_parts))
    dest_file = dest_dir / f"{base}{ext}"

    dest_file.parent.mkdir(parents=True, exist_ok=True)
    if not dest_file.exists():
        os.symlink((input_root / relative_path).resolve(), dest_file)

    return dest_file.name

def _label_for_type(folder_name: str, label: str, active_types: list[str], current_type: str) -> str:
    """
    Returns a label for the media section based on what types are present.

    - If only one type is active, return folder_name only.
    - If multiple types, return "folder_name - label".
    """
    folder_name = folder_name.replace("/", " - ").strip()
    if len(active_types) == 1 and current_type in active_types:
        return folder_name
    return f"{folder_name} - {label}"

def _build_project_page(creator: Dict, project: Dict, root_input: Path, out_dir: Path, thumbs_dir: Path, creators: list, html_settings: Dict):
    slug = _get_project_slug(creator, project)
    print(f"Building project page: {slug}.html")
    
    projects_dir = out_dir / "projects"

    template = env.get_template("project.html.j2")

    # Thumbnail
    thumbnail = project.get("featured_thumbnail") or project.get("thumbnail")
    if thumbnail:
        thumb_path = _create_thumbnail(root_input, Path(thumbnail), thumbs_dir, ThumbType.POSTER)
        thumbnail_url = get_relative_path(thumb_path, projects_dir)
    else:
        thumbnail_url = get_relative_path(out_dir / DEFAULT_IMAGES[ThumbType.POSTER], projects_dir)

    # Tags
    tag_map = {}
    for tag in sorted(project.get("tags", [])):
        if ":" in tag:
            category, label = tag.split(":", 1)
            tag_map.setdefault(category.strip(), []).append(label.strip())
        else:
            tag_map.setdefault("Tag", []).append(tag.strip())

    # Participants (creators)
    participants = []
    for name in creator.get("members") if creator.get("is_collaboration") else [creator["name"]]:
        participant = next((p for p in creators if p["name"] == name), None)
        if participant:
            if participant.get('portrait'):
                thumb_path = _create_thumbnail(root_input, Path(participant['portrait']), thumbs_dir, ThumbType.PORTRAIT)
                portrait_url = get_relative_path(thumb_path, projects_dir)
            else:
                portrait_url = get_relative_path(out_dir / DEFAULT_IMAGES[ThumbType.PORTRAIT], projects_dir)

            age_at_release = ""
            if participant.get("date_of_birth") and project.get("release_date"):
                from datetime import datetime
                try:
                    dob_dt = datetime.strptime(participant['date_of_birth'], "%Y-%m-%d")
                    release_dt = datetime.strptime(project['release_date'], "%Y-%m-%d")
                    age_at_release = _calculate_age(dob_dt, release_dt)
                except Exception as e:
                    print(f"Error calculating age: {e}")

            participants.append({
                "name": name,
                "url": f"../creators/{_get_creator_slug(participant)}.html",
                "portrait_url": portrait_url,
                "age_at_release": age_at_release
            })

    # Media groups
    media_groups = []
    for media_group in project.get("media_groups", []):
        images = []
        image_rel_paths =  media_group["featured_images"] if media_group.get("featured_images") is not None else media_group.get("images", [])
        for image_rel_path in image_rel_paths:
            thumb_path = _create_thumbnail(root_input, Path(image_rel_path), thumbs_dir, ThumbType.GALLERY)
            thumb_url = get_relative_path(thumb_path, projects_dir)
            image_name = _create_symlink(root_input, Path(image_rel_path), projects_dir / "images")
            
            images.append({
                "thumb_url": thumb_url,
                "full_url": f"images/{image_name}",
                "caption": Path(image_rel_path).stem
            })

        videos = []
        video_rel_paths =  media_group["featured_videos"] if media_group.get("featured_videos") is not None else media_group.get("videos", [])
        for video_path in video_rel_paths:
            video_name = _create_symlink(root_input, Path(video_path), projects_dir / "videos")
            videos.append(f"videos/{video_name}")
            
        audio = []
        audio_rel_paths =  media_group["featured_audio"] if media_group.get("featured_audio") is not None else media_group.get("audio", [])
        for audio_path in audio_rel_paths:
            audio_name = _create_symlink(root_input, Path(audio_path), projects_dir / "audio")
            
            audio.append({
                "full_url": f"audio/{audio_name}",
                "name": Path(audio_path).stem
            })
            
        documents = []
        document_rel_paths =  media_group["featured_documents"] if media_group.get("featured_documents") is not None else media_group.get("documents", [])
        for documents_path in document_rel_paths:
            documents_name = _create_symlink(root_input, Path(documents_path), projects_dir / "documents")
            documents.append(f"documents/{documents_name}")

        image_label = html_settings.get("project_page_images_label", "Images")
        video_label = html_settings.get("project_page_videos_label", "Videos")
        audio_label = html_settings.get("project_page_audio_label", "Audios")
        document_label = html_settings.get("project_page_documents_label", "Documents")
        
        is_root = media_group.get("is_root", False)
        folder_name = media_group.get("folder_name", "")

        if not is_root:
            active_types = []
            if images:
                active_types.append("images")
            if videos:
                active_types.append("videos")
            if audio:
                active_types.append("audio")
            if documents:
                active_types.append("documents")

            image_label = _label_for_type(folder_name, html_settings["project_page_images_label"], active_types, "images")
            video_label = _label_for_type(folder_name, html_settings["project_page_videos_label"], active_types, "videos")
            audio_label = _label_for_type(folder_name, html_settings["project_page_audio_label"], active_types, "audio")
            document_label = _label_for_type(folder_name, html_settings["project_page_documents_label"], active_types, "documents")
        else:
            # For root folders, use plain labels
            image_label = html_settings["project_page_images_label"]
            video_label = html_settings["project_page_videos_label"]
            audio_label = html_settings["project_page_audio_label"]
            document_label = html_settings["project_page_documents_label"]
                        
        media_groups.append({
            "image_label": media_group.get("image_label") or image_label,
            "video_label": media_group.get("video_label") or video_label,
            "audio_label": media_group.get("audio_label") or audio_label,
            "document_label": media_group.get("document_label") or document_label,
            "images": images,
            "videos": videos,
            "audio": audio,
            "documents": documents
        })
        
    output_html = template.render(
        html_settings=html_settings,
        creator_name=creator["name"],
        creator_slug=_get_creator_slug(creator),
        project=project,
        thumbnail_url=thumbnail_url,
        info_html=_render_markdown(project.get("info", "")),
        tag_map=tag_map,
        participants=participants,
        media_groups=media_groups,
        gallery_image_max_height=ThumbType.GALLERY.height,
        root_input=root_input,
        out_dir=projects_dir,
        get_relative_path=get_relative_path,
    )

    page_path = projects_dir / f"{slug}.html"
    with open(page_path, "w", encoding="utf-8") as f:
        f.write(output_html)
    
def _build_project_pages(creators: List[Dict], root_input: Path, out_dir: Path, thumbs_dir: Path, html_settings: Dict):
    print("Generating project pages...")
    
    for creator in creators:
        for project in creator['projects']:
            _build_project_page(creator, project, root_input, out_dir, thumbs_dir, creators, html_settings)
    
def _build_creator_page(creator: dict, creators: list, input_path: Path, out_dir: Path, thumbs_dir: Path, html_settings: dict):
    slug = _get_creator_slug(creator)
    print(f"Building creator page: {slug}.html")
    
    creators_dir = out_dir / "creators"

    template = env.get_template("creator.html.j2")

    # Process portrait thumbnail
    portrait = creator.get("featured_portrait") or creator.get("portrait")
    if portrait:
        thumb_path = _create_thumbnail(input_path, Path(portrait), thumbs_dir, ThumbType.PORTRAIT)
        portrait_url = get_relative_path(thumb_path, creators_dir)
    else:
        portrait_url = get_relative_path(out_dir / DEFAULT_IMAGES[ThumbType.PORTRAIT], creators_dir)

    # Compute debut age
    dob = creator.get("date_of_birth")
    release_dates = [p.get("release_date") for p in creator.get("projects", []) if p.get("release_date")]
    debut_age = ""
    if dob and release_dates:
        try:
            from datetime import datetime
            dob_dt = datetime.strptime(dob, "%Y-%m-%d")
            first_release = min(datetime.strptime(d, "%Y-%m-%d") for d in release_dates)
            debut_age = _calculate_age(dob_dt, first_release)
        except Exception as e:
            print(f"Error computing debut age: {e}")

    # Prepare tags
    all_tags = set(creator.get("tags", []))
    for project in creator.get("projects", []):
        all_tags.update(project.get("tags", []))

    tag_map = {}
    for tag in sorted(all_tags):
        if ":" in tag:
            category, label = tag.split(":", 1)
            tag_map.setdefault(category.strip(), []).append(label.strip())
        else:
            tag_map.setdefault("Tag", []).append(tag.strip())

    # Prepare projects
    projects = []
    for project in sorted(creator.get("projects", []), key=_sort_project):
        if project.get('thumbnail'):
            thumb_path = _create_thumbnail(input_path, Path(project['thumbnail']), thumbs_dir, ThumbType.PROJECT)
            thumb_url = get_relative_path(thumb_path, creators_dir)
        else:
            thumb_url = get_relative_path(out_dir / DEFAULT_IMAGES[ThumbType.PROJECT], creators_dir)

        project_slug = _get_project_slug(creator, project)
        projects.append({
            "title": project['title'],
            "url": f"../projects/{project_slug}.html",
            "thumbnail_url": thumb_url,
        })

    # Prepare collaborations (from creator["collaborations"])
    collaborations = []
    for collab_name in creator.get("collaborations", []):
        collab = next((c for c in creators if c["name"] == collab_name), None)
        if not collab:
            continue

        collab_projects = []
        for project in sorted(collab.get("projects", []), key=_sort_project):
            if project.get('thumbnail'):
                thumb_path = _create_thumbnail(input_path, Path(project['thumbnail']), thumbs_dir, ThumbType.PROJECT)
                thumb_url = get_relative_path(thumb_path, creators_dir)
            else:
                thumb_url = get_relative_path(out_dir / DEFAULT_IMAGES[ThumbType.PROJECT], creators_dir)

            project_slug = _get_project_slug(collab, project)
            collab_projects.append({
                "title": project['title'],
                "url": f"../projects/{project_slug}.html",
                "thumbnail_url": thumb_url,
            })
            
        # Determine label
        if creator["name"] in collab.get("members", []):
            others = [n for n in collab["members"] if n != creator["name"]]
            label = " & ".join(others)
        else:
            label = collab_name

        collaborations.append({
            "label": label,
            "projects": collab_projects
        })

    output_html = template.render(
        html_settings=html_settings,
        creator=creator,
        portrait_url=portrait_url,
        debut_age=debut_age,
        info_html=_render_markdown(creator.get("info", "")),
        tag_map=tag_map,
        projects=projects,
        collaborations=collaborations,
        project_thumb_max_height=ThumbType.POSTER.height,
    )

    page_path = creators_dir / f"{slug}.html"
    with open(page_path, "w", encoding="utf-8") as f:
        f.write(output_html)
    
def _build_collaboration_page(creator: dict, creators: list, input_path: Path, out_dir: Path, thumbs_dir: Path, html_settings: dict):
    slug = _get_creator_slug(creator)
    print(f"Building collaboration page: {slug}.html")
    
    creators_dir = out_dir / "creators"

    template = env.get_template("collaboration.html.j2")

    # Process portrait thumbnail
    portrait = creator.get("featured_portrait") or creator.get("portrait")
    if portrait:
        thumb_path = _create_thumbnail(input_path, Path(portrait), thumbs_dir, ThumbType.PORTRAIT)
        portrait_url = get_relative_path(thumb_path, creators_dir)
    else:
        portrait_url = get_relative_path(out_dir / DEFAULT_IMAGES[ThumbType.PORTRAIT], creators_dir)

    # Prepare tags
    all_tags = set(creator.get("tags", []))
    for project in creator.get("projects", []):
        all_tags.update(project.get("tags", []))

    tag_map = {}
    for tag in sorted(all_tags):
        if ":" in tag:
            category, label = tag.split(":", 1)
            tag_map.setdefault(category.strip(), []).append(label.strip())
        else:
            tag_map.setdefault("Tag", []).append(tag.strip())

    # Prepare member links
    member_links = []
    existing_creator_names = {m["name"]: m for m in creators if not m.get("is_collaboration")}
    for member in creator.get("members", []):
        if member in existing_creator_names:
            member_slug = _get_creator_slug(existing_creator_names[member])
            member_portrait = existing_creator_names[member].get("portrait")
            if member_portrait:
                thumb_path = _create_thumbnail(input_path, Path(member_portrait), thumbs_dir, ThumbType.THUMB)
                thumb_url = get_relative_path(thumb_path, creators_dir)
            else:
                thumb_url = get_relative_path(out_dir / DEFAULT_IMAGES[ThumbType.THUMB], creators_dir)

            member_links.append({
                "name": member,
                "url": f"../creators/{member_slug}.html",
                "thumbnail_url": thumb_url
            })

    # Prepare projects
    projects = []
    for project in sorted(creator.get("projects", []), key=_sort_project):
        if project.get('thumbnail'):
            thumb_path = _create_thumbnail(input_path, Path(project['thumbnail']), thumbs_dir, ThumbType.PROJECT)
            thumb_url = get_relative_path(thumb_path, creators_dir)
        else:
            thumb_url = get_relative_path(out_dir / DEFAULT_IMAGES[ThumbType.PROJECT], creators_dir)

        project_slug = _get_project_slug(creator, project)
        projects.append({
            "title": project['title'],
            "url": f"../projects/{project_slug}.html",
            "thumbnail_url": thumb_url,
        })

    output_html = template.render(
        html_settings=html_settings,
        creator=creator,
        portrait_url=portrait_url,
        info_html=_render_markdown(creator.get("info", "")),
        tag_map=tag_map,
        member_links=member_links,
        projects=projects,
        member_thumb_max_height=ThumbType.THUMB.height,
    )

    page_path = creators_dir / f"{slug}.html"
    with open(page_path, "w", encoding="utf-8") as f:
        f.write(output_html)
    
def _build_creator_pages(creators: List[Dict], input_path: Path, out_dir: Path, thumbs_dir: Path, html_settings: dict):
    print("Generating creator pages...")
    
    for creator in creators:
        if not creator["is_collaboration"]:
            _build_creator_page(creator, creators, input_path, out_dir, thumbs_dir, html_settings)
        else:
            _build_collaboration_page(creator, creators, input_path, out_dir, thumbs_dir, html_settings)
    
def _build_creator_overview_page(creators: list, input_path: Path, output_path: Path, thumbs_dir: Path, html_settings: dict):
    print("Generating overview page...")

    template = env.get_template("creator_overview.html.j2")

    creator_entries = []

    for creator in creators:
        if creator.get('portrait'):
            thumb_path = _create_thumbnail(input_path, Path(creator['portrait']), thumbs_dir, ThumbType.THUMB)
            thumbnail_url = get_relative_path(thumb_path, output_path)
        else:
            thumbnail_url = get_relative_path(output_path / DEFAULT_IMAGES[ThumbType.THUMB], output_path)

        # Build search text
        search_terms = [creator['name']]
        search_terms.extend(creator.get("tags", []))
        for project in creator.get('projects', []):
            search_terms.append(project.get('title', ''))
            for group in project.get('media_groups', []):
                search_terms.append(group.get('label', ''))
            for tag in project.get('tags', []):
                search_terms.append(tag)

        search_text = " ".join(search_terms).lower()

        creator_slug = _get_creator_slug(creator)
        creator_entries.append({
            "name": creator['name'],
            "url": f"creators/{creator_slug}.html",
            "thumbnail_url": thumbnail_url,
            "search_text": search_text
        })

    output_html = template.render(
        html_settings=html_settings,
        creator_entries=creator_entries,
        creator_thumb_max_height=ThumbType.THUMB.height,
    )

    page_file = output_path / "index.html"
    with open(page_file, 'w', encoding='utf-8') as f:
        f.write(output_html)
    
def _copy_asset_folder(src_root: Path, folder_name: str, output_root: Path):
    src = src_root / folder_name
    dst = output_root / folder_name

    if src.exists() and src.is_dir():
        shutil.copytree(src, dst, dirs_exist_ok=True)
        print(f"Copied {folder_name} to {dst}")
    else:
        print(f"Warning: Folder '{folder_name}' not found at {src}")
    
def _collect_creator_data(input_path: Path) -> List[Dict]:
    creator_data = []
    for creator in sorted(input_path.iterdir()):
        if not creator.is_dir():
            continue
        json_path = creator / "cr4te.json"
        if json_path.exists():
            with open(json_path, 'r', encoding='utf-8') as f:
                creator_data.append(json.load(f))
    return creator_data
    
def build_html_pages(input_path: Path, output_path: Path, html_settings: Dict):
    creators = _collect_creator_data(input_path)
    
    # Prepare output folders
    (output_path / "creators").mkdir(parents=True, exist_ok=True)
    (output_path / "projects").mkdir(parents=True, exist_ok=True)
    (output_path / "thumbnails").mkdir(parents=True, exist_ok=True)
    
    _copy_asset_folder(SCRIPT_DIR, "css", output_path)
    _copy_asset_folder(SCRIPT_DIR, "js", output_path)
    _copy_asset_folder(SCRIPT_DIR, "defaults", output_path)
    
    thumbs_dir = output_path / "thumbnails"
    _build_creator_overview_page(creators, input_path, output_path, thumbs_dir, html_settings)
    _build_creator_pages(creators, input_path, output_path, thumbs_dir, html_settings)
    _build_project_pages(creators, input_path, output_path, thumbs_dir, html_settings)
    _build_tags_page(creators, output_path, html_settings)
    
    # Collect all projects
    all_projects = []
    for creator in creators:
        for project in creator.get("projects", []):
            if project.get('thumbnail'):
                thumb_path = _create_thumbnail(input_path, Path(project['thumbnail']), thumbs_dir, ThumbType.PROJECT)
                thumbnail_url = get_relative_path(thumb_path, output_path)
            else:
                thumbnail_url = get_relative_path(output_path / DEFAULT_IMAGES[ThumbType.PROJECT], output_path)
            
            project_slug = _get_project_slug(creator, project)
            
            search_terms = project.get("tags", [])
            search_text = " ".join(search_terms).lower()
            all_projects.append({
                "title": project["title"],
                "url": f"projects/{project_slug}.html",
                "thumbnail_url": thumbnail_url,
                "creator": creator["name"],
                "search_text": search_text
            })

    # Build project overview page
    _build_project_overview_page(all_projects, input_path, output_path, html_settings)
    
def clear_output_folder(output_path: Path, clear_thumbnails: bool):
    """Delete all contents of output_path except the 'thumbnails' folder."""
    for item in output_path.iterdir():
        if clear_thumbnails or item.name != "thumbnails":
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
