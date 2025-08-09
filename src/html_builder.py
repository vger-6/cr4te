import shutil
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Iterable, Set
from datetime import datetime
from collections import defaultdict

from PIL import Image
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pydantic import ValidationError

import constants
import utils.path_utils as path_utils
import utils.text_utils as text_utils
import utils.image_utils as image_utils
import utils.date_utils as date_utils
import utils.json_utils as json_utils
import utils.audio_utils as audio_utils
from enums.media_type import MediaType
from enums.thumb_type import ThumbType
from enums.image_sample_strategy import ImageSampleStrategy
from enums.image_gallery_building_strategy import ImageGalleryBuildingStrategy
from enums.orientation import Orientation
from context.html_context import HtmlBuildContext, THUMBNAILS_DIRNAME
from validators.cr4te_schema import Creator as CreatorSchema

__all__ = ["clear_output_folder", "build_html_pages"]

# Setup Jinja2 environment
env = Environment(
    loader=FileSystemLoader(str(constants.CR4TE_TEMPLATES_DIR)),
    autoescape=select_autoescape(['html', 'xml'])
)
env.globals["MediaType"] = MediaType

FILE_TREE_DEPTH = 4

# HTML files live inside: output_dir/html/<depth levels>/<file.html>
# So to get back to output_dir, we need (depth + 1) "../" segments
HTML_PATH_TO_ROOT = path_utils.get_path_to_root(FILE_TREE_DEPTH + 1)

def _build_rel_creator_html_path(creator: Dict) -> Path:
    return path_utils.build_unique_path(Path('creator', creator['name']).with_suffix(".html"), FILE_TREE_DEPTH)
    
def _build_rel_project_html_path(creator: Dict, project: Dict) -> Path:
    return path_utils.build_unique_path(Path('project', creator['name'], project['title']).with_suffix(".html"), FILE_TREE_DEPTH)
           
def _get_or_create_thumbnail(ctx: HtmlBuildContext, rel_image_path: Path, thumb_type: ThumbType) -> Path:
    thumb_path = ctx.thumbs_dir / path_utils.build_unique_path(rel_image_path)
    thumb_path = path_utils.tag_path(thumb_path, thumb_type.value)

    if not thumb_path.exists():
        try:
            thumb = image_utils.generate_thumbnail(ctx.input_dir / rel_image_path, ctx.get_thumb_height(thumb_type))
            thumb_path.parent.mkdir(parents=True, exist_ok=True)

            thumb_ext = thumb_path.suffix.lower()
            match thumb_ext:
                case '.jpg' | '.jpeg':
                    format = 'JPEG'
                case '.png':
                    format = 'PNG'
                case _:
                    raise ValueError(f"Unsupported thumbnail extension: {thumb_ext}")

            thumb.save(thumb_path, format=format)

        except Exception as e:
            print(f"Error creating thumbnail for {rel_image_path}: {e}")

    return thumb_path
    
def _resolve_thumbnail_or_default(ctx: HtmlBuildContext, rel_image_path: Optional[str], thumb_type: ThumbType) -> Path:
    """
    Returns the resolved thumbnail path for a given relative image path,
    falling back to a default image if the input is None or missing.
    """
    if rel_image_path:
        return _get_or_create_thumbnail(ctx, Path(rel_image_path), thumb_type)
    return ctx.get_default_thumb_path(thumb_type)
    
def _sample_images(rel_image_paths: List[str], max_images: int, strategy: ImageSampleStrategy) -> List[str]:
    if max_images <= 0:
        return []

    sorted_paths = sorted(rel_image_paths)

    match strategy:
        case ImageSampleStrategy.ALL:
            return sorted_paths
        case _ if len(sorted_paths) <= max_images:
            return sorted_paths
        case ImageSampleStrategy.HEAD:
            return sorted_paths[:max_images]
        case ImageSampleStrategy.SPREAD:
            step = len(sorted_paths) / max_images
            return [sorted_paths[int(i * step)] for i in range(max_images)]
        case _:
            return sorted_paths  # fallback

def _sort_project(project: Dict) -> tuple:
    release_date = project["release_date"]
    has_date = bool(release_date)
    date_value = date_utils.parse_date(release_date) if has_date else datetime.max
    title = project["title"].lower()
    return (not has_date, date_value, title)
    
def _build_project_search_text(project: Dict) -> str:
    search_terms = [project["title"]]
    search_terms.extend(project["tags"])

    return " ".join(search_terms).lower()
    
def _collect_all_projects(ctx: HtmlBuildContext, creators: List[Dict]) -> List[Dict]:
    all_projects = []
    for creator in creators:
        for project in creator["projects"]: 
            thumb_path = _resolve_thumbnail_or_default(ctx, project['cover'], ThumbType.GALLERY)

            all_projects.append({
                "title": project["title"],
                "rel_html_path": (Path(ctx.html_dir.name) / _build_rel_project_html_path(creator, project)).as_posix(),
                "rel_thumbnail_path": path_utils.relative_path_from(thumb_path, ctx.output_dir).as_posix(),
                "creator_name": creator["name"],
                "search_text": _build_project_search_text(project)
            })  
    return sorted(all_projects, key=lambda p: p["title"].lower())
    
def _build_project_overview_page(ctx: HtmlBuildContext, creators: List):
    print("Generating project overview page...")

    template = env.get_template("project_overview.html.j2")

    rendered = template.render(
        projects=_collect_all_projects(ctx, creators),
        html_settings=ctx.html_settings,
        gallery_image_max_height=ctx.get_thumb_height(ThumbType.THUMB),
        ImageGalleryBuildingStrategy=ImageGalleryBuildingStrategy,
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

def _build_tags_page(ctx: HtmlBuildContext, creators: List):
    print("Generating tags page...")

    template = env.get_template("tags.html.j2")

    output_html = template.render(
        html_settings=ctx.html_settings,
        tags=_collect_all_tags(creators),
    )

    with open(ctx.tags_html_path, "w", encoding="utf-8") as f:
        f.write(output_html)
        
def _create_symlink(input_dir: Path, rel_source_path: Path, target_dir: Path) -> Path:
    source_path = (input_dir / rel_source_path).resolve()
    target_path = target_dir / path_utils.build_unique_path(rel_source_path)
    
    if not source_path.exists():
        print(f"[Warning] Cannot create symlink: source file not found: {source_path}")
    elif not target_path.exists():
        target_path.parent.mkdir(parents=True, exist_ok=True)
        os.symlink(source_path, target_path)

    return target_path
    
def _sort_sections_by_type(sections: List[Dict], media_type_order: List[str]) -> List[Dict]:
    order_map = {t: i for i, t in enumerate(dict.fromkeys(media_type_order))}
    fallback_order = len(order_map)

    return sorted(sections, key=lambda s: order_map.get(s["type"], fallback_order))
    
def _get_section_titles(media_group: Dict, audio_section_title: str, image_section_title: str) -> Dict[str, str]:
    if not media_group["is_root"]:
        title = Path(media_group["rel_dir_path"]).name.title()

        audio_section_title = title
        image_section_title = title

    return {
        "audio_section_title": audio_section_title,
        "image_section_title": image_section_title,
    }
    
def _build_media_groups_context(ctx: HtmlBuildContext, media_groups: List) -> List[Dict[str, Any]]:  
    media_groups_context = []

    for media_group in media_groups:
        rel_image_paths = _sample_images(media_group["images"], ctx.image_gallery_sample_max, ctx.image_gallery_sample_strategy)
        rel_video_paths = media_group["videos"]
        rel_track_paths = media_group["tracks"]
        rel_document_paths = media_group["documents"]
        rel_text_paths = media_group["texts"]
        
        images = [
            {
                "rel_thumbnail_path": path_utils.relative_path_from(_get_or_create_thumbnail(ctx, Path(rel), ThumbType.GALLERY), ctx.output_dir).as_posix(),
                "rel_path": path_utils.relative_path_from(_create_symlink(ctx.input_dir, Path(rel), ctx.symlinks_dir), ctx.output_dir).as_posix(),
                "caption": Path(rel).stem
            }
            for rel in rel_image_paths
        ]

        videos = [
            {
                "rel_path": path_utils.relative_path_from(_create_symlink(ctx.input_dir, Path(rel), ctx.symlinks_dir), ctx.output_dir).as_posix(),
                "title": Path(rel).stem.title()
            }
            for rel in rel_video_paths
        ]

        tracks = [
            {
                "rel_path": path_utils.relative_path_from(_create_symlink(ctx.input_dir, Path(rel), ctx.symlinks_dir), ctx.output_dir).as_posix(),
                "title": Path(rel).stem,
                "duration_seconds": audio_utils.get_audio_duration_seconds(ctx.input_dir / Path(rel))
            }
            for rel in rel_track_paths
        ]

        documents = [
            {
                "rel_path": path_utils.relative_path_from(_create_symlink(ctx.input_dir, Path(rel), ctx.symlinks_dir), ctx.output_dir).as_posix(),
                "title": Path(rel).stem.title()
            }
            for rel in rel_document_paths
        ]
        
        texts = [
            {
                "content": text_utils.markdown_to_html(text_utils.read_text(ctx.input_dir / Path(rel))),
                "title": Path(rel).stem.title()
            }
            for rel in rel_text_paths
        ]

        section_titles = _get_section_titles(
            media_group,
            ctx.project_page_audio_section_base_title,
            ctx.project_page_image_section_base_title
        )
        
        sections = [
            {"type": MediaType.VIDEO.value, "videos": videos},
            {"type": MediaType.AUDIO.value, "tracks": tracks, "meta": {"total_duration_seconds": sum(track["duration_seconds"] for track in tracks)}},
            {"type": MediaType.IMAGE.value, "images": images},
            {"type": MediaType.DOCUMENT.value, "documents": documents},
            {"type": MediaType.TEXT.value, "texts": texts}
        ]

        media_groups_context.append({
            **section_titles,
            "sections": _sort_sections_by_type(sections, ctx.media_type_order)
        })

    return media_groups_context

def calculate_age_at_release(creator: Dict, project: Dict) -> Optional[int]:
    born_or_founded = creator["born_or_founded"]
    release_date = project["release_date"]
    if not born_or_founded or not release_date:
        return None
        
    return date_utils.calculate_age_from_strings(born_or_founded, release_date)
    
def _collect_participant_entries(ctx: HtmlBuildContext, creator: Dict, project: Dict, creators: List[Dict]) -> List[Dict[str, str]]:
    creator_by_name = {c["name"]: c for c in creators}
    participant_names = creator["members"]
    
    participants = []
    for name in participant_names:
        participant = creator_by_name.get(name)
        if not participant:
            continue

        participants.append(_collect_creator_entries(ctx, participant, project))

    return participants
    
def _collect_creator_base_entries(ctx: HtmlBuildContext, creator: Dict) -> Dict[str, str]:
    thumb_path = _resolve_thumbnail_or_default(ctx, creator["portrait"], ThumbType.PORTRAIT)

    return {
        "name": creator["name"],
        "rel_html_path": (ctx.html_dir.name / _build_rel_creator_html_path(creator)).as_posix(),
        "rel_portrait_path": path_utils.relative_path_from(thumb_path, ctx.output_dir).as_posix(),
    }

def _collect_creator_entries(ctx: HtmlBuildContext, creator: Dict, project: Dict) -> Dict[str, str]:
    entries = _collect_creator_base_entries(ctx, creator)
    
    entries["age_at_release"] = calculate_age_at_release(creator, project)

    return entries
    
def _collect_collaborator_entries(ctx: HtmlBuildContext, creator: Dict) -> Dict[str, str]:
    return _collect_creator_base_entries(ctx, creator)
    
def _collect_project_context(ctx: HtmlBuildContext, creator: Dict, project: Dict, creators: List[Dict]) -> Dict: 
    thumb_path = _resolve_thumbnail_or_default(ctx, project["cover"], ThumbType.COVER)

    project_context = {
        "title": project["title"],
        "release_date": project["release_date"],
        "rel_thumbnail_path": path_utils.relative_path_from(thumb_path, ctx.output_dir).as_posix(),
        "thumbnail_orientation": image_utils.infer_image_orientation(thumb_path),
        "info_html": text_utils.markdown_to_html(project["info"]),
        "tag_map": _group_tags_by_category(project["tags"]),
        "media_groups": _build_media_groups_context(ctx, project["media_groups"]),
    }
    
    if creator["is_collaboration"]:
        project_context["participants"] = _collect_participant_entries(ctx, creator, project, creators)
        project_context["collaboration"] = _collect_collaborator_entries(ctx, creator)
    else:
        project_context["creator"] = _collect_creator_entries(ctx, creator, project)
    
    return project_context

def _build_project_page(ctx: HtmlBuildContext, creator: Dict, project: Dict, creators: List[Dict]):
    print(f"Building project page: {creator['name']} - {project['title']}")
    
    template = env.get_template("project.html.j2")
    
    output_html = template.render(
        html_settings=ctx.html_settings,
        project=_collect_project_context(ctx, creator, project, creators),
        gallery_image_max_height=ctx.get_thumb_height(ThumbType.GALLERY),
        path_to_root=HTML_PATH_TO_ROOT,
        Orientation=Orientation,
    )

    page_path = ctx.html_dir / _build_rel_project_html_path(creator, project)
    page_path.parent.mkdir(parents=True, exist_ok=True)
    with open(page_path, "w", encoding="utf-8") as f:
        f.write(output_html)
    
def _build_project_pages(ctx: HtmlBuildContext, creators: List[Dict]):
    print("Generating project pages...")
    
    for creator in creators:
        for project in creator['projects']:
            _build_project_page(ctx, creator, project, creators)
            
def _get_collaboration_label(collab: Dict, creator_name: str) -> str:
    if creator_name in collab["members"]:
        others = [n for n in collab["members"] if n != creator_name]
        return " ".join(others)
    return collab["name"]
    
def _calculate_debut_age(creator: Dict) -> Optional[int]:
    born_or_founded = creator["born_or_founded"]
    active_since = creator["active_since"]
    projects = creator["projects"]

    if not born_or_founded:
        return None

    if active_since:
        return date_utils.calculate_age_from_strings(born_or_founded, active_since)

    release_dates = [
        p["release_date"] for p in projects
        if date_utils.parse_date(p["release_date"])
    ]

    if not release_dates:
        return None

    earliest = min(release_dates, key=lambda d: date_utils.parse_date(d))
    return date_utils.calculate_age_from_strings(born_or_founded, earliest)

    
def _build_project_entries(ctx: HtmlBuildContext, creator: Dict) -> List[Dict[str, str]]:
    """
    Builds a list of dictionaries with metadata for each project of a creator,
    including title, html path, and thumbnail path.
    """
    project_entries = []
    for project in sorted(creator["projects"], key=_sort_project):
        thumb_path = _resolve_thumbnail_or_default(ctx, project["cover"], ThumbType.GALLERY)

        project_entries.append({
            "title": project["title"],
            "rel_html_path": (ctx.html_dir.name / _build_rel_project_html_path(creator, project)).as_posix(),
            "rel_thumbnail_path": path_utils.relative_path_from(thumb_path, ctx.output_dir).as_posix(),
        })

    return project_entries
    
def _build_collaboration_entries(ctx: HtmlBuildContext, creator: Dict, creators: List[Dict]) -> List[Dict[str, Any]]:
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
            "label": _get_collaboration_label(collab, creator["name"]),
            "projects": _build_project_entries(ctx, collab),
        })

    return collab_entries
    
def _collect_creator_context(ctx: HtmlBuildContext, creator: Dict, creators: List[Dict]) -> Dict[str, Any]:
    """
    Builds the context dictionary for rendering a creator's page,
    including metadata, portrait, projects, collaborations, and tags.
    """
    thumb_path = _resolve_thumbnail_or_default(ctx, creator["portrait"], ThumbType.PORTRAIT)
    
    creator_context = {
        "name": creator["name"],
        "aliases": creator["aliases"],
        "nationality": creator["nationality"],
        "rel_portrait_path": path_utils.relative_path_from(thumb_path, ctx.output_dir).as_posix(),
        "portrait_orientation": image_utils.infer_image_orientation(thumb_path),
        "info_html": text_utils.markdown_to_html(creator["info"]),
        "tag_map": _group_tags_by_category(_collect_tags_from_creator(creator)),
        "projects": _build_project_entries(ctx, creator),
        "media_groups": _build_media_groups_context(ctx, creator["media_groups"]),
    }
    
    if creator["is_collaboration"]:
        creator_context["members"] = _collect_member_links(ctx, creator, creators)
        creator_context["member_names"] = creator["members"]
        creator_context["founded"] = creator["born_or_founded"]
        creator_context["active_since"] = creator["active_since"]
    else:
        creator_context["date_of_birth"] = creator["born_or_founded"]
        creator_context["debut_age"] =  _calculate_debut_age(creator) or ""
        creator_context["collaborations"] = _build_collaboration_entries(ctx, creator, creators)
        
    return creator_context

def _build_creator_page(ctx: HtmlBuildContext, creator: dict, creators: List):
    print(f"Building creator page: {creator['name']}")
    
    template = env.get_template("creator.html.j2")

    output_html = template.render(
        html_settings=ctx.html_settings,
        creator=_collect_creator_context(ctx, creator, creators),
        member_thumb_max_height=ctx.get_thumb_height(ThumbType.THUMB),
        project_thumb_max_height=ctx.get_thumb_height(ThumbType.GALLERY),
        gallery_image_max_height=ctx.get_thumb_height(ThumbType.GALLERY),
        path_to_root=HTML_PATH_TO_ROOT,
        Orientation=Orientation,
        ImageGalleryBuildingStrategy=ImageGalleryBuildingStrategy,
    )
    
    page_path = ctx.html_dir / _build_rel_creator_html_path(creator)
    page_path.parent.mkdir(parents=True, exist_ok=True)
    with open(page_path, "w", encoding="utf-8") as f:
        f.write(output_html)
        
def _collect_member_links(ctx: HtmlBuildContext, creator: Dict, creators: List[Dict]) -> List[Dict[str, str]]:
    """
    Builds a list of dictionaries representing links to member creators
    in a collaboration, including name, html path, and thumbnail path.
    """
    if not creator["is_collaboration"]:
        return []

    creator_by_name = {c["name"]: c for c in creators}
    member_links = []

    for member_name in creator["members"]:
        member = creator_by_name.get(member_name)
        if not member:
            continue

        thumb_path = _resolve_thumbnail_or_default(ctx, member["portrait"], ThumbType.THUMB)

        member_links.append({
            "name": member_name,
            "rel_html_path": (ctx.html_dir.name / _build_rel_creator_html_path(member)).as_posix(),
            "rel_thumbnail_path": path_utils.relative_path_from(thumb_path, ctx.output_dir).as_posix()
        })

    return member_links
    
def _build_creator_pages(ctx: HtmlBuildContext, creators: List[Dict]):
    print("Generating creator pages...")
    
    for creator in creators:
        _build_creator_page(ctx, creator, creators)
    
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
    
def _build_creator_entries(ctx: HtmlBuildContext, creators: List[Dict]) -> List[Dict[str, str]]:
    """
    Builds a list of dictionaries containing metadata for each creator,
    including name, thumbnail path, and search text.
    """
    creator_entries = []
    for creator in creators:
        thumb_path = _resolve_thumbnail_or_default(ctx, creator["portrait"], ThumbType.THUMB)

        creator_entries.append({
            "name": creator["name"],
            "rel_html_path": (ctx.html_dir.name / _build_rel_creator_html_path(creator)).as_posix(),
            "rel_thumbnail_path": path_utils.relative_path_from(thumb_path, ctx.output_dir).as_posix(),
            "search_text": _build_creator_search_text(creator),
        })

    return creator_entries
    
def _build_creator_overview_page(ctx: HtmlBuildContext, creators: List):
    print("Generating overview page...")

    template = env.get_template("creator_overview.html.j2")

    output_html = template.render(
        html_settings=ctx.html_settings,
        creator_entries=_build_creator_entries(ctx, creators),
        gallery_image_max_height=ctx.get_thumb_height(ThumbType.THUMB),
        ImageGalleryBuildingStrategy=ImageGalleryBuildingStrategy,
    )

    with open(ctx.index_html_path, 'w', encoding='utf-8') as f:
        f.write(output_html)
        
def _validate_creator(creator: Dict) -> Dict:
    try:
        return CreatorSchema(**creator)
    except ValidationError as e:
        name = creator.get("name", "<unknown>")
        error_lines = [f"[{name}] {err['loc'][0]}: {err['msg']}" for err in e.errors()]
        formatted = "\n".join(error_lines)
        raise ValueError(f"Validation failed for creator '{name}':\n{formatted}")
    
def _collect_all_creators(input_dir: Path) -> List[Dict]:
    creators = []
    for creator_path in sorted(input_dir.iterdir()):
        if not creator_path.is_dir():
            continue
        json_path = creator_path / constants.CR4TE_JSON_FILE_NAME
        if json_path.exists():
            raw_data = json_utils.load_json(json_path)
            # Validate and normalize structure
            validated = _validate_creator(raw_data)
            creators.append(validated.model_dump())

    return creators
        
# TODO: Take aspect ratio and name from html_settings
def _prepare_static_assets(ctx: HtmlBuildContext) -> None:
    shutil.copytree(constants.CR4TE_CSS_DIR, ctx.css_dir, dirs_exist_ok=True)
    print(f"Copied {constants.CR4TE_CSS_DIR.name} to {ctx.css_dir}")
       
    shutil.copytree(constants.CR4TE_JS_DIR, ctx.js_dir, dirs_exist_ok=True)
    print(f"Copied {constants.CR4TE_JS_DIR.name} to {ctx.js_dir}")
       
    ctx.defaults_dir.mkdir(parents=True, exist_ok=True)
    thumb_height = ctx.get_thumb_height(ThumbType.THUMB)
    image_utils.create_centered_text_image(int(thumb_height * 3 / 4), thumb_height, "Thumb", ctx.defaults_dir / ctx.get_default_thumb_path(ThumbType.THUMB))
    portrait_height = ctx.get_thumb_height(ThumbType.PORTRAIT)
    image_utils.create_centered_text_image(int(portrait_height * 3 / 4), portrait_height, "Portrait", ctx.defaults_dir / ctx.get_default_thumb_path(ThumbType.PORTRAIT))
    cover_height = ctx.get_thumb_height(ThumbType.COVER)
    image_utils.create_centered_text_image(int(cover_height * 4 / 3), cover_height, "Cover", ctx.get_default_thumb_path(ThumbType.COVER))
    
def _prepare_output_dirs(ctx: HtmlBuildContext) -> None:
    ctx.output_dir.mkdir(parents=True, exist_ok=True)
    ctx.html_dir.mkdir(parents=True, exist_ok=True)
    ctx.thumbs_dir.mkdir(parents=True, exist_ok=True)
    
def build_html_pages(input_dir: Path, output_dir: Path, html_settings: Dict) -> Path:
    ctx = HtmlBuildContext(input_dir, output_dir, html_settings)
    
    _prepare_output_dirs(ctx)
    _prepare_static_assets(ctx)

    creators = _collect_all_creators(ctx.input_dir)
            
    _build_creator_overview_page(ctx, creators)
    _build_creator_pages(ctx, creators)
    _build_project_pages(ctx, creators)
    _build_project_overview_page(ctx, creators)
    _build_tags_page(ctx, creators)
    
    return ctx.index_html_path
    
def clear_output_folder(output_dir: Path, clear_thumbnails: bool):
    """Delete all contents of output_dir except the 'thumbnails' folder."""
    for item in output_dir.iterdir():
        if clear_thumbnails or item.name != THUMBNAILS_DIRNAME:
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()

