import shutil
import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Iterable
from datetime import datetime
from enum import Enum
from collections import defaultdict
from dataclasses import dataclass

import markdown
from PIL import Image
from jinja2 import Environment, FileSystemLoader, select_autoescape

from .enums.media_type import MediaType
from .utils import slugify, get_relative_path, read_text

__all__ = ["clear_output_folder", "build_html_pages"]

# === Path Constants ===
SCRIPT_DIR = Path(__file__).resolve().parents[1]

# Top-level folders
ASSETS_DIR = SCRIPT_DIR / "assets"
TEMPLATES_DIR = SCRIPT_DIR / "templates"

# Asset subfolders
CSS_DIR = ASSETS_DIR / "css"
JS_DIR = ASSETS_DIR / "js"
DEFAULTS_DIR = ASSETS_DIR / "defaults"

# Output structure
CREATORS_DIRNAME = "creators"
PROJECTS_DIRNAME = "projects"
THUMBNAILS_DIRNAME = "thumbnails"

# Setup Jinja2 environment
env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(['html', 'xml'])
)

class ThumbType(Enum):
    THUMB = ("_thumb.jpg", 300)
    PORTRAIT = ("_portrait.jpg", 450)
    POSTER = ("_poster.jpg", 600)
    PROJECT = ("_project.jpg", 600)
    GALLERY = ("_gallery.jpg", 450)

    def __init__(self, suffix: str, height: int):
        self.suffix = suffix
        self.height = height
        
DEFAULT_IMAGES = {
    ThumbType.THUMB: DEFAULTS_DIR / "default_thumb.jpg",
    ThumbType.PORTRAIT: DEFAULTS_DIR / "default_portrait.jpg",
    ThumbType.POSTER: DEFAULTS_DIR / "default_poster.jpg",
    ThumbType.PROJECT: DEFAULTS_DIR / "default_poster.jpg",   # same as poster
    ThumbType.GALLERY: DEFAULTS_DIR / "default_thumb.jpg",    # same as thumb
}
        
@dataclass
class BuildContext:
    input_dir: Path
    output_dir: Path
    html_settings: Dict

    @property
    def thumbs_dir(self) -> Path:
        return self.output_dir / THUMBNAILS_DIRNAME

    @property
    def creators_dir(self) -> Path:
        return self.output_dir / CREATORS_DIRNAME

    @property
    def projects_dir(self) -> Path:
        return self.output_dir / PROJECTS_DIRNAME
        
    @property
    def media_dir(self) -> Path:
        return self.output_dir / "media"

    @property
    def images_dir(self) -> Path:
        return self.media_dir / "images"

    @property
    def videos_dir(self) -> Path:
        return self.media_dir / "videos"

    @property
    def tracks_dir(self) -> Path:
        return self.media_dir / "tracks"

    @property
    def documents_dir(self) -> Path:
        return self.media_dir / "documents"
        
    @property
    def index_html_path(self) -> Path:
        return self.output_dir / "index.html"
        
    @property
    def projects_html_path(self) -> Path:
        return self.output_dir / "projects.html"
        
    @property
    def tags_html_path(self) -> Path:
        return self.output_dir / "tags.html"
        
    def default_image(self, thumb_type: ThumbType) -> Path:
        """
        Returns the path to the default image for a given thumbnail type.
        """
        return DEFAULT_IMAGES[thumb_type]

def _render_markdown(text: str) -> str:
    return markdown.markdown(text, extensions=["nl2br"])
    
def _parse_date(date_str: str) -> Optional[datetime]:
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except (TypeError, ValueError) as e:
        print(f"Failed to parse date '{date_str}': {e}")
        return None
    
def _calculate_age(dob: datetime, date: datetime) -> str:
    try:
        age = date.year - dob.year - ((date.month, date.day) < (dob.month, dob.day))
        return str(age)
    except Exception as e:
        print(f"Error calculating age: {e}")
        return ""
        
def _calculate_age_from_strings(birth_date_str: str, reference_date_str: str) -> str:
    """
    Safely parses two date strings and returns age as string.
    Returns empty string if either date is missing or invalid.
    """
    dob = _parse_date(birth_date_str)
    ref = _parse_date(reference_date_str)
    if dob and ref:
        return _calculate_age(dob, ref)
    return ""

def _get_creator_slug(creator: Dict) -> str:
    return slugify(creator['name'])
    
def _get_project_slug(creator: Dict, project: Dict) -> str:
    return slugify(f"{creator['name']}__{project['title']}")
    
def _build_slugified_filename(relative_path: Path, suffix: str) -> str:
    parts = [*relative_path.parent.parts, relative_path.stem]
    slug = slugify("__".join(parts))
    return f"{slug}{suffix}"
    
def is_portrait(image_path : Path) -> bool:
    try:
        with Image.open(image_path) as img:
            width, height = img.size

        if height > width:
            return True
        return False

    except Exception as e:
        print(f"Could not open image '{image_path}': {e}")
        return True
    
def _get_thumbnail_path(thumb_dir: Path, relative_image_path: Path, thumb_type: ThumbType) -> Path:
    filename = _build_slugified_filename(relative_image_path, thumb_type.suffix)
    return thumb_dir / filename
    
def _generate_thumbnail(source_path: Path, dest_path: Path, thumb_type: ThumbType) -> None:
    with Image.open(source_path) as img:
        target_height = thumb_type.height
        aspect_ratio = img.width / img.height
        target_width = int(target_height * aspect_ratio)
        resized = img.resize((target_width, target_height), Image.LANCZOS)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        resized.save(dest_path, format='JPEG')
               
def _get_or_create_thumbnail(input_dir: Path, relative_image_path: Path, thumb_dir: Path, thumb_type: ThumbType) -> Path:
    thumb_path = _get_thumbnail_path(thumb_dir, relative_image_path, thumb_type)

    if not thumb_path.exists():
        try:
            _generate_thumbnail(input_dir / relative_image_path, thumb_path, thumb_type)
        except Exception as e:
            print(f"Error creating thumbnail for {relative_image_path}: {e}")

    return thumb_path
    
def _resolve_thumbnail_or_default(relative_image_path: Optional[str], ctx: BuildContext, thumb_type: ThumbType) -> Path:
    """
    Returns the resolved thumbnail path for a given relative image path,
    falling back to a default image if the input is None or missing.
    """
    if relative_image_path:
        return _get_or_create_thumbnail(ctx.input_dir, Path(relative_image_path), ctx.thumbs_dir, thumb_type)
    return ctx.default_image(thumb_type)

def _sort_project(project: Dict) -> tuple:
    release_date = project["release_date"]
    has_date = bool(release_date)
    date_value = _parse_date(release_date) if has_date else datetime.max
    title = project["title"].lower()
    return (not has_date, date_value, title)
    
def _build_project_search_text(project: Dict) -> str:
    search_terms = [project["title"]]
    search_terms.extend(project["tags"])

    return " ".join(search_terms).lower()
    
def _collect_all_projects(creators: List[Dict], ctx: BuildContext) -> List[Dict]:
    all_projects = []
    for creator in creators:
        for project in creator["projects"]: 
            thumb_path = _resolve_thumbnail_or_default(project['featured_cover'] or project['cover'], ctx, ThumbType.PROJECT)

            all_projects.append({
                "title": project["title"],
                "url": f"{PROJECTS_DIRNAME}/{_get_project_slug(creator, project)}.html",
                "thumbnail_url": get_relative_path(thumb_path, ctx.output_dir),
                "creator_name": creator["name"],
                "search_text": _build_project_search_text(project)
            })  
    return sorted(all_projects, key=lambda p: p["title"].lower())
    
def _build_project_overview_page(creators: list, ctx: BuildContext):
    print("Generating project overview page...")

    template = env.get_template("project_overview.html.j2")

    rendered = template.render(
        projects=_collect_all_projects(creators, ctx),
        html_settings=ctx.html_settings,
        poster_max_height=ThumbType.PROJECT.height,
    )

    with open(ctx.projects_html_path, "w", encoding="utf-8") as f:
        f.write(rendered)

def _collect_tags_from_creator(creator: Dict) -> List[str]:
    tags = list(creator["tags"])
    for project in creator["projects"]:
        tags.extend(project["tags"])
    return tags
    
def _group_tags_by_category(tags: Iterable[str]) -> Dict[str, List[str]]:
    """
    Groups tags by category. Tags with the format 'Category: Label' are grouped under 'Category'.
    Tags without a colon are grouped under the default 'Tag' category.

    Returns:
        A dictionary sorted by category name and tag name.
    """
    grouped: Dict[str, Set[str]] = defaultdict(set)

    for tag in tags:
        if ":" in tag:
            category, label = tag.split(":", 1)
            grouped[category.strip()].add(label.strip())
        else:
            grouped["Tag"].add(tag.strip())
            
    return {category: sorted(grouped[category]) for category in sorted(grouped)}
    
def _collect_all_tags(creators: List[Dict]) -> Dict[str, List[str]]:
    all_tags = []
    for creator in creators:
        all_tags.extend(_collect_tags_from_creator(creator))
    return _group_tags_by_category(all_tags)

def _build_tags_page(creators: list, ctx: BuildContext):
    print("Generating tags page...")

    template = env.get_template("tags.html.j2")

    output_html = template.render(
        html_settings=ctx.html_settings,
        tags=_collect_all_tags(creators),
    )

    with open(ctx.tags_html_path, "w", encoding="utf-8") as f:
        f.write(output_html)
        
def _create_symlink(input_dir: Path, relative_path: Path, target_dir: Path) -> Path:
    source_file = (input_dir / relative_path).resolve()
    filename = _build_slugified_filename(relative_path, relative_path.suffix.lower())
    dest_file = target_dir / filename

    dest_file.parent.mkdir(parents=True, exist_ok=True)

    if not source_file.exists():
        print(f"[Warning] Cannot create symlink: source file not found: {source_file}")
    elif not dest_file.exists():
        os.symlink(source_file, dest_file)

    return dest_file
    
def _sort_sections_by_type(sections: List[Dict], type_order: List[str]) -> List[Dict]:
    order_map = {t: i for i, t in enumerate(dict.fromkeys(type_order))}
    fallback_order = len(order_map)

    return sorted(sections, key=lambda s: order_map.get(s["type"], fallback_order))

#def _format_section_title(folder_name: str, label: str, active_types: List[MediaType], current_type: MediaType) -> str:
#    """
#    Returns a title for the media section based on what types are present.
#
#    - If only one type is active, return folder_name only.
#    - If multiple types, return "folder_name - label".
#    """
#    folder_name = folder_name.replace("/", " - ").strip()
#    if len(active_types) == 1 and current_type in active_types:
#        return folder_name
#    return f"{folder_name} - {label}"
    
def _get_section_titles(media_group: Dict, html_settings: Dict) -> Dict[str, str]:
    audio_title = html_settings["project_page_audio_section_base_title"]
    image_title = html_settings["project_page_image_section_base_title"]

    if not media_group["is_root"]:
        folder_name = media_group["folder_name"]

        audio_title = folder_name.title()
        image_title = folder_name.title()

    return {
        "audio_section_title": audio_title,
        "image_section_title": image_title,
    }
    
def _build_media_groups(project: Dict, ctx: BuildContext) -> List[Dict[str, Any]]:  
    media_groups = []
    for media_group in project["media_groups"]:
        image_rel_paths = media_group["featured_images"] or media_group["images"]
        video_rel_paths = media_group["featured_videos"] or media_group["videos"]
        track_rel_paths = media_group["featured_tracks"] or media_group["tracks"]
        document_rel_paths = media_group["featured_documents"] or media_group["documents"]
        text_rel_paths = media_group["featured_texts"] or media_group["texts"]

        images = [
            {
                "thumb_url": get_relative_path(_get_or_create_thumbnail(ctx.input_dir, Path(rel), ctx.thumbs_dir, ThumbType.GALLERY), ctx.projects_dir),
                "full_url": get_relative_path(_create_symlink(ctx.input_dir, Path(rel), ctx.images_dir), ctx.projects_dir),
                "caption": Path(rel).stem
            }
            for rel in image_rel_paths
        ]

        videos = [
            {
                "full_url": get_relative_path(_create_symlink(ctx.input_dir, Path(rel), ctx.videos_dir), ctx.projects_dir),
                "title": Path(rel).stem.title()
            }
            for rel in video_rel_paths
        ]

        tracks = [
            {
                "full_url": get_relative_path(_create_symlink(ctx.input_dir, Path(rel), ctx.tracks_dir), ctx.projects_dir),
                "title": Path(rel).stem
            }
            for rel in track_rel_paths
        ]

        documents = [
            {
                "full_url": get_relative_path(_create_symlink(ctx.input_dir, Path(rel), ctx.documents_dir), ctx.projects_dir),
                "title": Path(rel).stem.title()
            }
            for rel in document_rel_paths
        ]
        
        texts = [
            {
                "content": _render_markdown(read_text(ctx.input_dir / Path(rel))),
                "title": Path(rel).stem.title()
            }
            for rel in text_rel_paths
        ]

        section_titles = _get_section_titles(
            media_group,
            ctx.html_settings
        )
        
        sections = [
            {"type": MediaType.VIDEO.value, "videos": videos},
            {"type": MediaType.AUDIO.value, "tracks": tracks},
            {"type": MediaType.IMAGE.value, "images": images},
            {"type": MediaType.DOCUMENT.value, "documents": documents},
            {"type": MediaType.TEXT.value, "texts": texts}
        ]

        media_groups.append({
            **section_titles,
            "sections": _sort_sections_by_type(sections, ctx.html_settings["project_page_type_order"])
        })

    return media_groups
    
def _calculate_age_at_release(creator: Dict, project: Dict) -> str:
    dob = creator["born_or_founded"]
    release_date = project["release_date"]
    if not dob or not release_date:
        return ""
        
    return _calculate_age_from_strings(dob, release_date)
    
def _collect_participant_entries(creator: Dict, project: Dict, creators: List[Dict], ctx: BuildContext) -> List[Dict[str, str]]:
    creator_by_name = {c["name"]: c for c in creators}
    participant_names = creator["members"] if creator["is_collaboration"] else [creator["name"]]
    
    participants = []
    for name in participant_names:
        participant = creator_by_name.get(name)
        if not participant:
            continue
         
        thumb_path = _resolve_thumbnail_or_default(participant["featured_portrait"] or participant["portrait"], ctx, ThumbType.PORTRAIT)

        participants.append({
            "name": name,
            "url": f"../{CREATORS_DIRNAME}/{_get_creator_slug(participant)}.html",
            "portrait_url": get_relative_path(thumb_path, ctx.projects_dir),
            "age_at_release": _calculate_age_at_release(participant, project)
        })

    return participants
    
def _collect_project_context(creator: Dict, project: Dict, creators: List[Dict], ctx: BuildContext) -> Dict: 
    thumb_path = _resolve_thumbnail_or_default(project["featured_cover"] or project["cover"], ctx, ThumbType.POSTER)

    return {
        "title": project["title"],
        "release_date": project["release_date"],
        "thumbnail_url": get_relative_path(thumb_path, ctx.projects_dir),
        "info_layout": "row" if is_portrait(thumb_path) else "column",
        "info_html": _render_markdown(project["info"]),
        "tag_map": _group_tags_by_category(project["tags"]),
        "participants": _collect_participant_entries(creator, project, creators, ctx),
        "media_groups": _build_media_groups(project, ctx),
        "creator_name": creator["name"],
        "creator_slug": _get_creator_slug(creator),
    }

def _build_project_page(creator: Dict, project: Dict, creators: List[Dict], ctx: BuildContext):
    slug = _get_project_slug(creator, project)
    print(f"Building project page: {slug}.html")
    
    template = env.get_template("project.html.j2")
    
    output_html = template.render(
        html_settings=ctx.html_settings,
        project=_collect_project_context(creator, project, creators, ctx),
        gallery_image_max_height=ThumbType.GALLERY.height,
        MediaType=MediaType
    )

    page_path = ctx.projects_dir / f"{slug}.html"
    with open(page_path, "w", encoding="utf-8") as f:
        f.write(output_html)
    
def _build_project_pages(creators: List[Dict], ctx: BuildContext):
    print("Generating project pages...")
    
    for creator in creators:
        for project in creator['projects']:
            _build_project_page(creator, project, creators, ctx)
            
def _get_collaboration_label(collab: Dict, creator_name: str, html_settings: Dict) -> str:
    if creator_name in collab["members"]:
        others = [n for n in collab["members"] if n != creator_name]
        return " ".join(others)
    return collab["name"]
    
def _calculate_debut_age(creator: Dict) -> str:
    dob = creator["born_or_founded"]
    active_since = creator["active_since"]
    release_dates = [p["release_date"] for p in creator["projects"] if p["release_date"]]

    if not dob or (not active_since and not release_dates):
        return ""

    if active_since:
        return _calculate_age_from_strings(dob, active_since)
    
    valid_release_dates = [d for d in release_dates if _parse_date(d)]
    if valid_release_dates:
        earliest = min(valid_release_dates, key=lambda d: _parse_date(d))
        return _calculate_age_from_strings(dob, earliest)

    return ""
    
def _build_project_entries(creator: Dict, ctx: BuildContext) -> List[Dict[str, str]]:
    """
    Builds a list of dictionaries with metadata for each project of a creator,
    including title, URL, and cover URL.
    """
    project_entries = []
    for project in sorted(creator["projects"], key=_sort_project):
        thumb_path = _resolve_thumbnail_or_default(project["featured_cover"] or project["cover"], ctx, ThumbType.PROJECT)

        project_entries.append({
            "title": project["title"],
            "url": f"../{PROJECTS_DIRNAME}/{_get_project_slug(creator, project)}.html",
            "thumbnail_url": get_relative_path(thumb_path, ctx.creators_dir),
        })

    return project_entries
    
def _build_collaboration_entries(creator: Dict, creators: List[Dict], ctx: BuildContext) -> List[Dict[str, Any]]:
    """
    Builds a list of collaboration entries for a given creator.
    Each entry includes a label and a list of project entries.
    """
    creator_by_name = {c["name"]: c for c in creators}
    collab_entries = []
    for collab_name in creator["collaborations"]:
        collab = creator_by_name[collab_name]
        if not collab:
            continue

        collab_entries.append({
            "label": _get_collaboration_label(collab, creator["name"], ctx.html_settings),
            "projects": _build_project_entries(collab, ctx),
        })

    return collab_entries
    
def _collect_creator_context(creator: Dict, creators: List[Dict], ctx: BuildContext) -> Dict[str, Any]:
    """
    Builds the context dictionary for rendering a creator's page,
    including metadata, portrait, projects, collaborations, and tags.
    """
    thumb_path = _resolve_thumbnail_or_default(creator["featured_portrait"] or creator["portrait"], ctx, ThumbType.PORTRAIT)
    
    return {
        "name": creator["name"],
        "aliases": creator["aliases"],
        "date_of_birth": creator["born_or_founded"],
        "nationality": creator["nationality"],
        "portrait_url": get_relative_path(thumb_path, ctx.creators_dir),
        "info_layout": "row" if is_portrait(thumb_path) else "column",
        "debut_age": _calculate_debut_age(creator),
        "info_html": _render_markdown(creator["info"]),
        "tag_map": _group_tags_by_category(_collect_tags_from_creator(creator)),
        "projects": _build_project_entries(creator, ctx),
        "collaborations": _build_collaboration_entries(creator, creators, ctx),
    }
    
def _build_creator_page(creator: dict, creators: list, ctx: BuildContext):
    slug = _get_creator_slug(creator)
    print(f"Building creator page: {slug}.html")
    
    template = env.get_template("creator.html.j2")

    output_html = template.render(
        html_settings=ctx.html_settings,
        creator=_collect_creator_context(creator, creators, ctx),
        project_thumb_max_height=ThumbType.POSTER.height,
    )

    page_path = ctx.creators_dir / f"{slug}.html"
    with open(page_path, "w", encoding="utf-8") as f:
        f.write(output_html)
        
def _collect_member_links(creator: Dict, creators: List[Dict], ctx: BuildContext) -> List[Dict[str, str]]:
    """
    Builds a list of dictionaries representing links to member creators
    in a collaboration, including name, URL, and thumbnail URL.
    """
    if not creator["is_collaboration"]:
        return []

    creator_by_name = {c["name"]: c for c in creators}
    member_links = []

    for member_name in creator["members"]:
        member = creator_by_name.get(member_name)
        if not member:
            continue

        thumb_path = _resolve_thumbnail_or_default(member["featured_portrait"] or member["portrait"], ctx, ThumbType.THUMB)

        member_links.append({
            "name": member_name,
            "url": f"../{CREATORS_DIRNAME}/{_get_creator_slug(member)}.html",
            "thumbnail_url": get_relative_path(thumb_path, ctx.creators_dir)
        })

    return member_links
        
def _collect_collaboration_context(creator: Dict, creators: List[Dict], ctx: BuildContext) -> Dict[str, Any]:
    """
    Builds the context dictionary for rendering a collaboration page,
    including metadata, portrait, members, projects, and tags.
    """
    thumb_path = _resolve_thumbnail_or_default(creator["featured_portrait"] or creator["portrait"], ctx, ThumbType.PORTRAIT)

    return {
        "name": creator["name"],
        "member_names": creator["members"],
        "members": _collect_member_links(creator, creators, ctx),
        "founded": creator["born_or_founded"],
        "nationality": creator["nationality"],
        "active_since": creator["active_since"],
        "portrait_url": get_relative_path(thumb_path, ctx.creators_dir),
        "info_layout": "row" if is_portrait(thumb_path) else "column",
        "info_html": _render_markdown(creator["info"]),
        "tag_map": _group_tags_by_category(_collect_tags_from_creator(creator)),
        "projects": _build_project_entries(creator, ctx),
    }
    
def _build_collaboration_page(creator: dict, creators: list, ctx: BuildContext):
    slug = _get_creator_slug(creator)
    print(f"Building collaboration page: {slug}.html")

    template = env.get_template("collaboration.html.j2")

    output_html = template.render(
        html_settings=ctx.html_settings,
        creator=_collect_collaboration_context(creator, creators, ctx),
        member_thumb_max_height=ThumbType.THUMB.height,
        project_thumb_max_height=ThumbType.POSTER.height,
    )

    page_path = ctx.creators_dir / f"{slug}.html"
    with open(page_path, "w", encoding="utf-8") as f:
        f.write(output_html)
    
def _build_creator_pages(creators: List[Dict], ctx: BuildContext):
    print("Generating creator pages...")
    
    for creator in creators:
        if not creator["is_collaboration"]:
            _build_creator_page(creator, creators, ctx)
        else:
            _build_collaboration_page(creator, creators, ctx)
    
def _build_creator_search_text(creator: Dict) -> str:
    """
    Builds a lowercase search text string from a creator's name, tags,
    project titles, media group labels, and project tags.
    """
    search_terms = [creator["name"]]
    search_terms.extend(creator["tags"])

    for project in creator["projects"]:
        search_terms.append(project["title"])
        search_terms.extend(project["tags"])

    return " ".join(search_terms).lower()
    
def _build_creator_entries(creators: List[Dict], ctx: BuildContext) -> List[Dict[str, str]]:
    """
    Builds a list of dictionaries containing metadata for each creator,
    including name, thumbnail URL, profile URL, and search text.
    """
    creator_entries = []
    for creator in creators:
        thumb_path = _resolve_thumbnail_or_default(creator["featured_portrait"] or creator["portrait"], ctx, ThumbType.THUMB)

        creator_entries.append({
            "name": creator["name"],
            "url": f"{CREATORS_DIRNAME}/{_get_creator_slug(creator)}.html",
            "thumbnail_url": get_relative_path(thumb_path, ctx.output_dir),
            "search_text": _build_creator_search_text(creator),
        })

    return creator_entries
    
def _build_creator_overview_page(creators: list, ctx: BuildContext):
    print("Generating overview page...")

    template = env.get_template("creator_overview.html.j2")

    output_html = template.render(
        html_settings=ctx.html_settings,
        creator_entries=_build_creator_entries(creators, ctx),
        creator_thumb_max_height=ThumbType.THUMB.height,
    )

    with open(ctx.index_html_path, 'w', encoding='utf-8') as f:
        f.write(output_html)
        
def _filter_disabled_content(creators: list) -> list:
    """
    Removes creators and their projects that are marked as 'is_enabled': false.
    """
    filtered = []
    for creator in creators:
        if not creator["is_enabled"]:
            continue
        creator["projects"] = [p for p in creator["projects"] if p["is_enabled"]]
        filtered.append(creator)
    return filtered
    
def _collect_creator_data(input_dir: Path) -> List[Dict]:
    creator_data = []
    for creator in sorted(input_dir.iterdir()):
        if not creator.is_dir():
            continue
        json_path = creator / "cr4te.json"
        if json_path.exists():
            with open(json_path, 'r', encoding='utf-8') as f:
                creator_data.append(json.load(f))
    return creator_data
        
def _copy_assets(output_dir: Path) -> None:
    for asset_dir in [CSS_DIR, JS_DIR, DEFAULTS_DIR]:
        dst = output_dir / asset_dir.relative_to(SCRIPT_DIR)
        shutil.copytree(asset_dir, dst, dirs_exist_ok=True)
        print(f"Copied {asset_dir.name} to {dst}")
    
def _prepare_output_dirs(ctx: BuildContext) -> None:
    ctx.output_dir.mkdir(parents=True, exist_ok=True)
    ctx.creators_dir.mkdir(parents=True, exist_ok=True)
    ctx.projects_dir.mkdir(parents=True, exist_ok=True)
    ctx.thumbs_dir.mkdir(parents=True, exist_ok=True)
    
def build_html_pages(input_dir: Path, output_dir: Path, html_settings: Dict) -> Path:
    ctx = BuildContext(input_dir, output_dir, html_settings)
    
    _prepare_output_dirs(ctx)
    _copy_assets(ctx.output_dir)

    creators = _collect_creator_data(ctx.input_dir)
    creators = _filter_disabled_content(creators)
            
    _build_creator_overview_page(creators, ctx)
    _build_creator_pages(creators, ctx)
    _build_project_pages(creators, ctx)
    _build_project_overview_page(creators, ctx)
    _build_tags_page(creators, ctx)
    
    return ctx.index_html_path
    
def clear_output_folder(output_dir: Path, clear_thumbnails: bool):
    """Delete all contents of output_dir except the 'thumbnails' folder."""
    for item in output_dir.iterdir():
        if clear_thumbnails or item.name != THUMBNAILS_DIRNAME:
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
