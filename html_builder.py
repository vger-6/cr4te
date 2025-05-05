import shutil
import json
from pathlib import Path
from typing import List, Dict
from datetime import datetime
from enum import Enum
from collections import defaultdict

import markdown
from PIL import Image
from jinja2 import Environment, FileSystemLoader, select_autoescape

from utils import slugify, get_relative_path

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
    GALLERY = ("_gallery.jpg", 400)

    def __init__(self, suffix: str, height: int):
        self.suffix = suffix
        self.height = height

DEFAULT_IMAGES = {
    ThumbType.THUMB: "default_thumb.jpg",
    ThumbType.PORTRAIT: "default_portrait.jpg",
    ThumbType.POSTER: "default_poster.jpg",
    ThumbType.PROJECT: "default_poster.jpg",  # Reuse poster fallback
    ThumbType.GALLERY: "default_thumb.jpg"  # Reuse thumb fallback
}

HTML_TEMPLATE = """<!DOCTYPE html><html lang="en"><head><meta charset='utf-8'><meta name="viewport" content="width=device-width, initial-scale=1"><title>{title}</title></head><body>{body}</body></html>"""

# TODO: Move to separate module. E.g. project_structure.py 
def clear_output_folder(output_path: Path):
    """Delete all contents of output_path except the 'thumbnails' folder."""
    for item in output_path.iterdir():
        if item.name != "thumbnails":
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
        
# TODO: Move to separate module. E.g. project_structure.py         
def collect_creator_data(input_path: Path) -> List[Dict]:
    creator_data = []
    for creator in sorted(input_path.iterdir()):
        if not creator.is_dir():
            continue
        json_path = creator / "cr4te.json"
        if json_path.exists():
            with open(json_path, 'r', encoding='utf-8') as f:
                creator_data.append(json.load(f))
    return creator_data

def get_thumbnail_path(thumbs_dir: Path, slug: str, original_file: Path, thumb_type: ThumbType) -> Path:
    thumb_subdir = thumbs_dir / slug
    thumb_subdir.mkdir(parents=True, exist_ok=True)
    return thumb_subdir / (original_file.stem + thumb_type.suffix)

def generate_thumbnail(source_path: Path, dest_path: Path, thumb_type: ThumbType):
    if dest_path.exists():
        return
        
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with Image.open(source_path) as img:
            img.thumbnail((thumb_type.height, thumb_type.height))
            img.save(dest_path, format='JPEG')
    except Exception as e:
        print(f"Error creating thumbnail for {source_path}: {e}")

def calculate_age(dob: datetime, date: datetime) -> str:
    try:
        age = date.year - dob.year - ((date.month, date.day) < (dob.month, dob.day))
        return str(age)
    except Exception as e:
        print(f"Error calculating age: {e}")
        return ""

def render_markdown(text: str) -> str:
    return markdown.markdown(text, extensions=["extra"])

def sort_project(project: Dict) -> tuple:
    release_date = project.get("release_date", "")
    has_date = bool(release_date)
    date_value = datetime.strptime(release_date, "%Y-%m-%d") if has_date else datetime.max
    title = project.get("title", "").lower()
    return (not has_date, date_value, title)

def build_html_pages(creators: list, input_path: Path, output_path: Path, html_settings: dict):
    (output_path / "creators").mkdir(parents=True, exist_ok=True)
    (output_path / "projects").mkdir(parents=True, exist_ok=True)
    (output_path / "thumbnails").mkdir(parents=True, exist_ok=True)
    
    # copy css files
    css_source = SCRIPT_DIR / "css"
    css_dest = output_path / "css"
    if css_source.exists() and css_source.is_dir():
        shutil.copytree(css_source, css_dest, dirs_exist_ok=True)
        print(f"Copied CSS to {css_dest}")
    else:
        print(f"Warning: CSS folder not found at {css_source}")

    # copy js files
    js_source = SCRIPT_DIR / "js"
    js_dest = output_path / "js"
    if js_source.exists() and js_source.is_dir():
        shutil.copytree(js_source, js_dest, dirs_exist_ok=True)
        print(f"Copied JS to {js_dest}")
    else:
        print(f"Warning: JS folder not found at {js_source}")

    # Copy default images into thumbnails
    defaults_source = SCRIPT_DIR / "defaults"
    defaults_dest = output_path / "thumbnails"
    if defaults_source.exists():
        for img_file in defaults_source.glob("*.jpg"):
            shutil.copy(img_file, defaults_dest / img_file.name)
        print(f"Copied default images to {defaults_dest}")
    else:
        print(f"Warning: Defaults folder not found at {defaults_source}")

    thumbs_dir = output_path / "thumbnails"
    build_overview_pages(   creators, input_path, output_path,              thumbs_dir, html_settings)
    build_all_creator_pages(creators, input_path, output_path / "creators", thumbs_dir, html_settings)
    build_all_project_pages(creators, input_path, output_path / "projects", thumbs_dir, html_settings)
    build_tags_page(        creators,             output_path,                          html_settings)
    
    # Collect all projects
    # Note: assumes that all thumbs have already been generated
    all_projects = []
    for creator in creators:
        for project in creator.get("projects", []):
            #print(project)
            project_slug = slugify(f"{creator['name']}_{project['title']}")
            thumb_path = get_thumbnail_path(thumbs_dir, project_slug, Path(project['thumbnail']), ThumbType.PROJECT)
            thumb_url = get_relative_path(thumb_path, output_path)
            
            search_terms = project.get("tags", [])
            search_text = " ".join(search_terms).lower()
            all_projects.append({
                "title": project["title"],
                "url": f"projects/{project_slug}.html",
                "thumbnail_url": thumb_url,
                "creator": creator["name"],
                "search_text": search_text
            })

    # Build project overview page
    build_project_overview_page(all_projects, input_path, output_path, html_settings)

def build_overview_pages(creators: list, input_path: Path, output_path: Path, thumbs_dir: Path, html_settings: dict):
    print("Generating overview page...")

    template = env.get_template("overview.html.j2")

    creator_entries = []

    for creator in creators:
        slug = slugify(creator['name'])
        if creator.get('portrait'):
            img_abs = input_path / creator['portrait']
            thumb_path = get_thumbnail_path(thumbs_dir, slug, Path(creator['portrait']), ThumbType.THUMB)
            generate_thumbnail(img_abs, thumb_path, ThumbType.THUMB)
            thumbnail_url = get_relative_path(thumb_path, output_path)
        else:
            thumbnail_url = get_relative_path(thumbs_dir / DEFAULT_IMAGES[ThumbType.THUMB], output_path)

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

        creator_entries.append({
            "name": creator['name'],
            "url": f"creators/{slug}.html",
            "thumbnail_url": thumbnail_url,
            "search_text": search_text
        })

    output_html = template.render(
        html_settings=html_settings,
        creator_entries=creator_entries,
    )

    page_file = output_path / "index.html"
    with open(page_file, 'w', encoding='utf-8') as f:
        f.write(output_html)
        
def build_project_overview_page(projects: List[dict], input_path: Path, output_path: Path, html_settings: Dict):
    template = env.get_template("project_overview.html.j2")

    sorted_projects = sorted(projects, key=lambda p: p["title"].lower())

    rendered = template.render(
        projects=sorted_projects,
        html_settings=html_settings
    )

    output_path.mkdir(parents=True, exist_ok=True)
    with open(output_path / "projects.html", "w", encoding="utf-8") as f:
        f.write(rendered)


def build_all_creator_pages(creators: List[Dict], input_path: Path, out_dir: Path, thumbs_dir: Path, html_settings: dict):
    print("Generating creator pages...")
    
    for creator in creators:
        if not creator["is_collaboration"]:
            build_solo_page(creator, creators, input_path, out_dir, thumbs_dir, html_settings)
        else:
            build_collaboration_page(creator, creators, input_path, out_dir, thumbs_dir, html_settings)

def build_solo_page(creator: dict, creators: list, input_path: Path, out_dir: Path, thumbs_dir: Path, html_settings: dict):
    slug = slugify(creator['name'])
    print(f"Building creator page: {slug}.html")

    template = env.get_template("creator_solo.html.j2")

    # Process portrait thumbnail
    if creator.get('portrait'):
        img_abs = input_path / creator['portrait']
        thumb_path = get_thumbnail_path(thumbs_dir, slug, Path(creator['portrait']), ThumbType.PORTRAIT)
        generate_thumbnail(img_abs, thumb_path, ThumbType.PORTRAIT)
        portrait_url = get_relative_path(thumb_path, out_dir)
    else:
        portrait_url = get_relative_path(thumbs_dir / DEFAULT_IMAGES[ThumbType.PORTRAIT], out_dir)

    # Compute debut age
    dob = creator.get("date_of_birth")
    release_dates = [p.get("release_date") for p in creator.get("projects", []) if p.get("release_date")]
    debut_age = ""
    if dob and release_dates:
        try:
            from datetime import datetime
            dob_dt = datetime.strptime(dob, "%Y-%m-%d")
            first_release = min(datetime.strptime(d, "%Y-%m-%d") for d in release_dates)
            debut_age = calculate_age(dob_dt, first_release)
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
    for project in sorted(creator.get("projects", []), key=sort_project):
        project_slug = slugify(f"{creator['name']}_{project['title']}")
        if project.get('thumbnail'):
            img_abs = input_path / project['thumbnail']
            thumb_path = get_thumbnail_path(thumbs_dir, project_slug, Path(project['thumbnail']), ThumbType.PROJECT)
            generate_thumbnail(img_abs, thumb_path, ThumbType.PROJECT)
            thumb_url = get_relative_path(thumb_path, out_dir)
        else:
            thumb_url = get_relative_path(thumbs_dir / DEFAULT_IMAGES[ThumbType.PROJECT], out_dir)

        projects.append({
            "title": project['title'],
            "url": f"../projects/{project_slug}.html",
            "thumbnail_url": thumb_url,
        })

    # Prepare collaborations
    collaborations = []
    for collab in (m for m in creators if m.get("is_collaboration") and creator["name"] in m.get("members", [])):
        other_members = [name for name in collab.get("members", []) if name != creator["name"]]
        collab_label = " & ".join(other_members)
        collab_projects = []

        for project in sorted(collab.get("projects", []), key=sort_project):
            project_slug = slugify(f"{collab['name']}_{project['title']}")
            if project.get('thumbnail'):
                img_abs = input_path / project['thumbnail']
                thumb_path = get_thumbnail_path(thumbs_dir, project_slug, Path(project['thumbnail']), ThumbType.PROJECT)
                generate_thumbnail(img_abs, thumb_path, ThumbType.PROJECT)
                thumb_url = get_relative_path(thumb_path, out_dir)
            else:
                thumb_url = get_relative_path(thumbs_dir / DEFAULT_IMAGES[ThumbType.PROJECT], out_dir)

            collab_projects.append({
                "title": project['title'],
                "url": f"../projects/{project_slug}.html",
                "thumbnail_url": thumb_url,
            })

        collaborations.append({
            "label": collab_label,
            "projects": collab_projects
        })

    output_html = template.render(
        html_settings=html_settings,
        creator=creator,
        portrait_url=portrait_url,
        debut_age=debut_age,
        info_html=render_markdown(creator.get("info", "")),
        tag_map=tag_map,
        projects=projects,
        collaborations=collaborations,
    )

    page_path = out_dir / f"{slug}.html"
    with open(page_path, "w", encoding="utf-8") as f:
        f.write(output_html)

def build_collaboration_page(creator: dict, creators: list, input_path: Path, out_dir: Path, thumbs_dir: Path, html_settings: dict):
    slug = slugify(creator['name'])
    print(f"Building collaboration page: {slug}.html")

    template = env.get_template("creator_collaboration.html.j2")

    # Process portrait thumbnail
    if creator.get('portrait'):
        img_abs = input_path / creator['portrait']
        thumb_path = get_thumbnail_path(thumbs_dir, slug, Path(creator['portrait']), ThumbType.PORTRAIT)
        generate_thumbnail(img_abs, thumb_path, ThumbType.PORTRAIT)
        portrait_url = get_relative_path(thumb_path, out_dir)
    else:
        portrait_url = get_relative_path(thumbs_dir / DEFAULT_IMAGES[ThumbType.PORTRAIT], out_dir)

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
            member_slug = slugify(member)
            member_portrait = existing_creator_names[member].get("portrait")
            if member_portrait:
                img_abs = input_path / member_portrait
                thumb_path = get_thumbnail_path(thumbs_dir, member_slug, Path(member_portrait), ThumbType.THUMB)
                generate_thumbnail(img_abs, thumb_path, ThumbType.THUMB)
                thumb_url = get_relative_path(thumb_path, out_dir)
            else:
                thumb_url = get_relative_path(thumbs_dir / DEFAULT_IMAGES[ThumbType.THUMB], out_dir)

            member_links.append({
                "name": member,
                "url": f"../creators/{member_slug}.html",
                "thumbnail_url": thumb_url
            })

    # Prepare projects
    projects = []
    for project in sorted(creator.get("projects", []), key=sort_project):
        project_slug = slugify(f"{creator['name']}_{project['title']}")
        if project.get('thumbnail'):
            img_abs = input_path / project['thumbnail']
            thumb_path = get_thumbnail_path(thumbs_dir, project_slug, Path(project['thumbnail']), ThumbType.PROJECT)
            generate_thumbnail(img_abs, thumb_path, ThumbType.PROJECT)
            thumb_url = get_relative_path(thumb_path, out_dir)
        else:
            thumb_url = get_relative_path(thumbs_dir / DEFAULT_IMAGES[ThumbType.PROJECT], out_dir)

        projects.append({
            "title": project['title'],
            "url": f"../projects/{project_slug}.html",
            "thumbnail_url": thumb_url,
        })

    output_html = template.render(
        html_settings=html_settings,
        creator=creator,
        portrait_url=portrait_url,
        info_html=render_markdown(creator.get("info", "")),
        tag_map=tag_map,
        member_links=member_links,
        projects=projects,
    )

    page_path = out_dir / f"{slug}.html"
    with open(page_path, "w", encoding="utf-8") as f:
        f.write(output_html)

def build_all_project_pages(creators: List[Dict], root_input: Path, out_dir: Path, thumbs_dir: Path, html_settings: dict):
    print("Generating project pages...")
    
    for creator in creators:
        for project in creator['projects']:
            build_project_page(creator['name'], project, root_input, out_dir, thumbs_dir, creators, html_settings)
            
def build_project_page(creator_name: str, project: dict, root_input: Path, out_dir: Path, thumbs_dir: Path, creators: list, html_settings: dict):
    slug = slugify(f"{creator_name}_{project['title']}")
    print(f"Building project page: {slug}.html")

    template = env.get_template("project_page.html.j2")

    # Thumbnail
    if project.get('thumbnail'):
        img_abs = root_input / project['thumbnail']
        thumb_path = get_thumbnail_path(thumbs_dir, slug, Path(project['thumbnail']), ThumbType.POSTER)
        generate_thumbnail(img_abs, thumb_path, ThumbType.POSTER)
        thumbnail_url = get_relative_path(thumb_path, out_dir)
    else:
        thumbnail_url = get_relative_path(thumbs_dir / DEFAULT_IMAGES[ThumbType.POSTER], out_dir)

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
    for name in ([creator_name] if " & " not in creator_name else creator_name.split(" & ")):
        name = name.strip()
        creator = next((c for c in creators if c["name"] == name), None)
        if creator:
            if creator.get('portrait'):
                img_abs = root_input / creator['portrait']
                thumb_path = get_thumbnail_path(thumbs_dir, slugify(name), Path(creator['portrait']), ThumbType.PORTRAIT)
                generate_thumbnail(img_abs, thumb_path, ThumbType.PORTRAIT)
                portrait_url = get_relative_path(thumb_path, out_dir)
            else:
                portrait_url = get_relative_path(thumbs_dir / DEFAULT_IMAGES[ThumbType.PORTRAIT], out_dir)

            age_at_release = ""
            if creator.get("date_of_birth") and project.get("release_date"):
                from datetime import datetime
                try:
                    dob_dt = datetime.strptime(creator['date_of_birth'], "%Y-%m-%d")
                    release_dt = datetime.strptime(project['release_date'], "%Y-%m-%d")
                    age_at_release = calculate_age(dob_dt, release_dt)
                except Exception as e:
                    print(f"Error calculating age: {e}")

            participants.append({
                "name": name,
                "url": f"../creators/{slugify(name)}.html",
                "portrait_url": portrait_url,
                "age_at_release": age_at_release
            })

    # Media groups
    slug = slugify(f"{creator_name}_{project['title']}")
    media_groups = []
    for media_group in project.get("media_groups", []):
        # TODO: Add method: def create_media_group(folder_name: str, is_root: bool, videos: list, images: list) -> Dict
        images = []
        for image_rel_path in media_group.get("images", []):
            image_abs = root_input / image_rel_path
            thumb_path = get_thumbnail_path(thumbs_dir, slug, Path(image_rel_path), ThumbType.GALLERY)
            generate_thumbnail(image_abs, thumb_path, ThumbType.GALLERY)
            thumb_url = get_relative_path(thumb_path, out_dir)
            full_url = get_relative_path(image_abs, out_dir)

            images.append({
                "thumb_url": thumb_url,
                "full_url": full_url
            })
            
        videos = [get_relative_path(root_input / video_path, out_dir) for video_path in media_group.get("videos", [])]
        
        image_label = html_settings.get("project_page_images_label", "Images")
        video_label = html_settings.get("project_page_videos_label", "Videos")
        is_root = media_group.get("is_root", False)
        if not is_root:
            has_images = bool(images)
            has_videos = bool(videos)
            
            folder_name = media_group.get("folder_name", "").replace("/", " - ")
            if has_videos and not has_images:
                image_label = ""
                video_label = folder_name
            elif has_images and not has_videos:
                image_label = folder_name
                video_label = ""
            else:
                image_label = f"{folder_name} - {image_label}"
                video_label = f"{folder_name} - {video_label}"

        media_groups.append({
            "image_label": image_label,
            "video_label": video_label,
            "images": images,
            "videos": videos
        })

    output_html = template.render(
        html_settings=html_settings,
        creator_name=creator_name,
        project_title=project['title'],
        thumbnail_url=thumbnail_url,
        info_html=render_markdown(project.get("info", "")),
        tag_map=tag_map,
        participants=participants,
        media_groups=media_groups,
        root_input=root_input,
        out_dir=out_dir,
        get_relative_path=get_relative_path,
    )

    page_path = out_dir / f"{slug}.html"
    with open(page_path, "w", encoding="utf-8") as f:
        f.write(output_html)

def collect_all_tags(creators: List[Dict]) -> Dict[str, set[str]]:
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

def build_tags_page(creators: list, output_path: Path, html_settings: dict):
    print("Generating tags page...")

    template = env.get_template("tags.html.j2")

    tags = collect_all_tags(creators)

    output_html = template.render(
        html_settings=html_settings,
        tags=tags,
    )

    tag_file = output_path / "tags.html"
    with open(tag_file, "w", encoding="utf-8") as f:
        f.write(output_html)
