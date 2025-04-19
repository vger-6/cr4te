import shutil
import markdown
from pathlib import Path
from typing import List, Dict, Optional
from PIL import Image
from datetime import datetime
from enum import Enum
from collections import defaultdict

from utils import is_collaboration, slugify, get_relative_path

SCRIPT_DIR = Path(__file__).resolve().parent

class ThumbType(Enum):
    THUMB = ("_thumb.jpg", 300)
    PORTRAIT = ("_portrait.jpg", 600)
    POSTER = ("_poster.jpg", 800)
    PROJECT = ("_project.jpg", 800)

    def __init__(self, suffix: str, width: int):
        self.suffix = suffix
        self.width = width

DEFAULT_IMAGES = {
    ThumbType.THUMB: "default_thumb.jpg",
    ThumbType.PORTRAIT: "default_portrait.jpg",
    ThumbType.POSTER: "default_poster.jpg",
    ThumbType.PROJECT: "default_poster.jpg",  # Reuse poster fallback
}

HTML_TEMPLATE = """<!DOCTYPE html><html lang="en"><head><meta charset='utf-8'><meta name="viewport" content="width=device-width, initial-scale=1"><title>{title}</title></head><body>{body}</body></html>"""

def get_thumbnail_path(thumbs_dir: Path, slug: str, original_file: Path, thumb_type: ThumbType) -> Path:
    thumb_subdir = thumbs_dir / slug
    thumb_subdir.mkdir(parents=True, exist_ok=True)
    return thumb_subdir / (original_file.stem + thumb_type.suffix)

def generate_thumbnail(source_path: Path, dest_path: Path, thumb_type: ThumbType):
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with Image.open(source_path) as img:
            img.thumbnail((thumb_type.width, thumb_type.width))
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

def build_nav_links(*links: tuple[str, Optional[str]]) -> str:
    parts = []
    for label, href in links:
        if href is None:
            parts.append(f"<span class='nav-current'>{label}</span>")
        else:
            parts.append(f"<a href='{href}'>{label}</a>")
    return f"<div class='top-link'>{' &middot; '.join(parts)}</div>"

def render_tag_section(tags: List[str]) -> str:
    tag_map = defaultdict(set)
    for tag in tags:
        if ":" in tag:
            category, tag_label = tag.split(":", 1)
            tag_map[category.strip()].add(tag_label.strip())
        else:
            tag_map["Tag"].add(tag.strip())

    if not tag_map:
        return ""

    section_html = "<div class='section-box'>"
    section_html += "<div class='section-title'>Tags</div><hr>"
    section_html += "<div class='section-content tag-list'>"

    for category in sorted(tag_map.keys()):
        section_html += f"<div class='tag-category'><strong>{category}:</strong> "
        for tag in sorted(tag_map[category]):
            section_html += f"<a class='tag' href='../index.html?tag={tag}'>{tag}</a>"
        section_html += "</div>"

    section_html += "</div></div>"
    return section_html

def build_html_pages(creators: List[Dict], output_path: Path, input_path: Path):
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
    build_overview_pages( creators, output_path,            input_path, thumbs_dir)
    build_all_creator_pages(creators, output_path / "creators", input_path, thumbs_dir)
    build_all_project_pages(creators, output_path / "projects", input_path, thumbs_dir)
    build_tags_page(creators, output_path)

def build_overview_pages(creators: List[Dict], output_path: Path, input_path: Path, thumbs_dir: Path):
    print("Generating overview page...")

    css_links = """
    <link rel="stylesheet" href="css/base.css">
    <link rel="stylesheet" href="css/creator.css">
    """

    body = css_links

    body += build_nav_links(
        ("Creators", None),
        ("Tags", "tags.html")
    )
    
    title = "Creators Overview"
    
    body += f"<h1>{title}</h1>"

    body += '''
    <div class="search-bar-wrapper">
        <input type="text" id="search-input" placeholder="Search creators, tags, projects..." class="search-box">
    </div>
    '''

    body += "<div class='creator-box'>"
    body += "<div class='creator-box-title'>Creators</div>"
    body += "<hr>"
    body += "<div class='creator-gallery'>"

    for creator in creators:
        slug = slugify(creator['name'])
        portrait = creator['portrait']

        search_terms = [creator['name']]
        for project in creator.get('projects', []):
            search_terms.append(project.get('title', ''))
            for group in project.get('image_groups', []):
                search_terms.append(group.get('label', ''))
            for tag in project.get('tags', []):
                search_terms.append(tag)
        
        search_text = " ".join(search_terms).lower()
        
        body += f"<div class='creator-entry' data-search='{search_text}'>"
        body += f"<a href='creators/{slug}.html' title='{creator['name']}'>"
        if portrait:
            img_abs = input_path / portrait
            thumb_path = get_thumbnail_path(thumbs_dir, slug, Path(portrait), ThumbType.THUMB)
            generate_thumbnail(img_abs, thumb_path, ThumbType.THUMB)
            thumb_rel = get_relative_path(thumb_path, output_path)
        else:
            thumb_rel = get_relative_path(thumbs_dir / DEFAULT_IMAGES[ThumbType.THUMB], output_path)

        body += f"<img src='{thumb_rel}' width='100' alt='{creator['name']} thumbnail'><br>"
        body += f"{creator['name']}</a>"
        body += "</div>"

    body += "</div>"  # creator-gallery
    body += "</div>"  # creator-box

    body += '<script src="js/filter.js"></script>'
    
    page_file = output_path / "index.html"
    with open(page_file, 'w', encoding='utf-8') as f:
        f.write(HTML_TEMPLATE.format(title=title, body=body))

def build_all_creator_pages(creators: List[Dict], out_dir: Path, input_path: Path, thumbs_dir: Path):
    print("Generating creator pages...")
    
    for creator in creators:
        if not creator["is_collaboration"]:
            build_solo_page(creator, creators, out_dir, input_path, thumbs_dir)
        else:
            build_collaboration_page(creator, creators, out_dir, input_path, thumbs_dir)

def build_solo_page(creator: Dict, creators: List[Dict], out_dir: Path, input_path: Path, thumbs_dir: Path):
    slug = slugify(creator['name'])
    print(f"Building creator page: {slug}.html")
    
    # Link external CSS
    css_links = """
    <link rel="stylesheet" href="../css/base.css">
    <link rel="stylesheet" href="../css/creator.css">
    """

    body = css_links
    body += build_nav_links(
        ("Creators", "../index.html"),
        ("Tags", "../tags.html")
    )

    title = creator['name']
    body += f"<h1>{title}</h1>"

    body += "<div class='creator-layout'>"

    # Left Side
    body += "<div class='creator-left'>"

    # Creator section
    #body += "<div class='section-box fit-box'>"
    body += "<div class='section-box'>"
    body += "<div class='section-title'>Profile</div><hr>"
    body += "<div class='section-content markdown'>"

    # Portrait + DOB + ...
    body += "<div class='creator-info'>"

    portrait = creator['portrait']
    if portrait:
        img_abs = input_path / portrait
        thumb_path = get_thumbnail_path(thumbs_dir, slug, Path(portrait), ThumbType.PORTRAIT)
        generate_thumbnail(img_abs, thumb_path, ThumbType.PORTRAIT)
        thumb_rel = get_relative_path(thumb_path, out_dir)
    else:
        thumb_rel = get_relative_path(thumbs_dir / DEFAULT_IMAGES[ThumbType.PORTRAIT], out_dir)

    body += f"<img src='{thumb_rel}' alt='Portrait of {creator['name']}'>"
    body += "<div>"

    body += f"<p><strong>Name:</strong> {creator['name']}</p>"
    
    if 'date_of_birth' in creator:
        body += f"<p><strong>Date of Birth:</strong> {creator['date_of_birth']}</p>"

    # Debut Age
    dob = creator.get("date_of_birth", "")
    release_dates = [project.get("release_date") for project in creator.get("projects", []) if project.get("release_date")]

    age_years = ""
    if dob and release_dates:
        try:
            dob_dt = datetime.strptime(dob, "%Y-%m-%d")
            first_release = min([datetime.strptime(sd, "%Y-%m-%d") for sd in release_dates])
            age_years = calculate_age(dob_dt, first_release)
        except Exception as e:
            print(f"Could not compute debut age: {e}")

    body += f"<p><strong>Debut Age:</strong> {age_years}</p>"
        
    # Placeholder for future description, tags, etc.
    
    body += "</div>"  
    body += "</div>"  # Close .creator-info
    body += "</div>"  # Close section-content 
    body += "</div>"  # section-box

    # Optional Info Text section
    info_text = creator.get("info", "").strip()
    if info_text:
        body += "<div class='section-box'>"
        body += "<div class='section-title'>Info</div>"
        body += "<hr>"
        body += f"<div class='section-content'>{render_markdown(info_text)}</div>"
        body += "</div>"

    # Optional Tags section
    all_tags = []
    for project in creator.get("projects", []):
        all_tags.extend(project.get("tags", []))
    
    body += render_tag_section(all_tags)

    body += "</div>"  # close creator-left

    # Right Side
    body += "<div class='creator-right'>"

    # Optional Projects section
    if creator['projects']:
        creator['projects'].sort(key=sort_project)
        body += "<div class='section-box'>"
        body += "<div class='section-title'>Projects</div>"
        body += "<hr>"
        body += "<div class='section-content project-gallery'>"
        
        for project in creator['projects']:
            project_title = project["title"]
            project_slug = slugify(f"{creator['name']}_{project_title}")
            thumb_rel = ""
            
            if project['thumbnail']:
                img_abs = input_path / project['thumbnail']
                thumb_path = get_thumbnail_path(thumbs_dir, project_slug, Path(project['thumbnail']), ThumbType.PROJECT)
                generate_thumbnail(img_abs, thumb_path, ThumbType.PROJECT)
                thumb_rel = get_relative_path(thumb_path, out_dir)
            else:
                thumb_rel = get_relative_path(thumbs_dir / DEFAULT_IMAGES[ThumbType.PROJECT], out_dir)

            body += f"<div class='project-entry'><a href='../projects/{project_slug}.html' title='{project_title}'>"
            
            if thumb_rel:
                body += f"<img src='{thumb_rel}' alt='Thumbnail for {project_title}'><br>"
                
            body += f"{project_title}</a></div>"
        body += "</div>"
        body += "</div>"

    # Optional Collaboration projects section
    collaborations = [m for m in creators if m.get("is_collaboration") and creator["name"] in m.get("members", [])]
    for collab in collaborations:
        collab['projects'].sort(key=sort_project)
        body += "<div class='section-box'>"
        body += f"<div class='section-title'>Collaborations: {collab['name']}</div><hr>"
        body += "<div class='section-content project-gallery'>"
        
        for project in collab['projects']:
            project_title = project["title"]
            project_slug = slugify(f"{collab['name']}_{project_title}")
            thumb_rel = ""
            
            if project['thumbnail']:
                img_abs = input_path / project['thumbnail']
                thumb_path = get_thumbnail_path(thumbs_dir, project_slug, Path(project['thumbnail']), ThumbType.PROJECT)
                generate_thumbnail(img_abs, thumb_path, ThumbType.PROJECT)
                thumb_rel = get_relative_path(thumb_path, out_dir)
            else:
                thumb_rel = get_relative_path(thumbs_dir / DEFAULT_IMAGES[ThumbType.PROJECT], out_dir)

            body += f"<div class='project-entry'><a href='../projects/{project_slug}.html' title='{project_title}'>"
            
            if thumb_rel:
                body += f"<img src='{thumb_rel}' alt='Thumbnail for {project_title}'><br>"
                
            body += f"{project_title}</a></div>"
        body += "</div>"
        body += "</div>"

    body += "</div>"  # close creator-right
    body += "</div>"  # close creator-layout

     # Write file
    page_path = out_dir / f"{slug}.html"
    with open(page_path, 'w', encoding='utf-8') as f:
        f.write(HTML_TEMPLATE.format(title=title, body=body))

def build_collaboration_page(creator: Dict, creators: List[Dict], out_dir: Path, input_path: Path, thumbs_dir: Path):
    slug = slugify(creator['name'])
    print(f"Building collaboration page: {slug}.html")

    css_links = """
    <link rel="stylesheet" href="../css/base.css">
    <link rel="stylesheet" href="../css/creator.css">
    """

    body = css_links
    body += build_nav_links(
        ("Creators", "../index.html"),
        ("Tags", "../tags.html")
    )

    title = creator['name']
    body += f"<h1>{title}</h1>"

    body += "<div class='creator-layout'>"

    # Left Side
    body += "<div class='creator-left'>"

    # Profile section
    #body += "<div class='section-box fit-box'>"
    body += "<div class='section-box'>"
    body += "<div class='section-title'>Profile</div><hr>"
    body += "<div class='section-content markdown'>"

    body += "<div class='creator-info'>"

    portrait = creator.get('portrait')
    if portrait:
        img_abs = input_path / portrait
        thumb_path = get_thumbnail_path(thumbs_dir, slug, Path(portrait), ThumbType.PORTRAIT)
        generate_thumbnail(img_abs, thumb_path, ThumbType.PORTRAIT)
        thumb_rel = get_relative_path(thumb_path, out_dir)
    else:
        thumb_rel = get_relative_path(thumbs_dir / DEFAULT_IMAGES[ThumbType.PORTRAIT], out_dir)

    body += f"<img src='{thumb_rel}' alt='Portrait of {creator['name']}'>"

    body += "<div>"

    # Members
    members = creator.get("members", [])
    body += "<div>"
    body += f"<p><strong>Featuring:</strong> {', '.join(members)}</p>"
    body += "</div>"

    body += "</div>"
    
    body += "</div>"  # Close .creator-info
    body += "</div>"  # Close section-content 
    body += "</div>"  # section-box

    # Optional Info section
    info_text = creator.get("info", "").strip()
    if info_text:
        body += "<div class='section-box'>"
        body += "<div class='section-title'>Info</div>"
        body += "<hr>"
        body += f"<div class='section-content'>{render_markdown(info_text)}</div>"
        body += "</div>"

    # Optional Featuring (solo) creator pages
    existing_creator_names = {m["name"]: m for m in creators if not m.get("is_collaboration")}
    featured_members = [m for m in creator.get("members", []) if m in existing_creator_names]

    if featured_members:
        body += "<div class='section-box'>"
        body += "<div class='section-title'>Featuring</div><hr>"
        body += "<div class='section-content creator-gallery'>"

        for name in featured_members:
            featured = existing_creator_names[name]
            featured_slug = slugify(featured["name"])
            portrait = featured.get("portrait")
            if portrait:
                img_abs = input_path / portrait
                thumb_path = get_thumbnail_path(thumbs_dir, featured_slug, Path(portrait), ThumbType.THUMB)
                generate_thumbnail(img_abs, thumb_path, ThumbType.THUMB)
                thumb_rel = get_relative_path(thumb_path, out_dir)
            else:
                thumb_rel = get_relative_path(thumbs_dir / DEFAULT_IMAGES[ThumbType.THUMB], out_dir)

            body += "<div class='creator-entry'>"
            body += f"<a href='../creators/{featured_slug}.html' title='{featured['name']}'>"
            body += f"<img src='{thumb_rel}' width='100' alt='{featured['name']} thumbnail'><br>"
            body += f"{featured['name']}</a></div>"

        body += "</div></div>"

    # Optional Tags section
    all_tags = []
    for project in creator.get("projects", []):
        all_tags.extend(project.get("tags", []))

    body += render_tag_section(all_tags)

    body += "</div>" # close Left Side

    # Right Side
    body += "<div class='creator-right'>"

    # Optional Projects section
    if creator['projects']:
        creator['projects'].sort(key=sort_project)
        body += "<div class='section-box'>"
        body += "<div class='section-title'>Projects</div><hr>"
        body += "<div class='section-content project-gallery'>"

        for project in creator['projects']:
            project_title = project["title"]
            project_slug = slugify(f"{creator['name']}_{project_title}")
            thumb_rel = ""

            if project['thumbnail']:
                img_abs = input_path / project['thumbnail']
                thumb_path = get_thumbnail_path(thumbs_dir, project_slug, Path(project['thumbnail']), ThumbType.PROJECT)
                generate_thumbnail(img_abs, thumb_path, ThumbType.PROJECT)
                thumb_rel = get_relative_path(thumb_path, out_dir)
            else:
                thumb_rel = get_relative_path(thumbs_dir / DEFAULT_IMAGES[ThumbType.PROJECT], out_dir)

            body += f"<div class='project-entry'><a href='../projects/{project_slug}.html' title='{project_title}'>"
            body += f"<img src='{thumb_rel}' alt='Thumbnail for {project_title}'><br>"
            body += f"{project_title}</a></div>"

        body += "</div></div>"

    body += "</div>" # close Right Side
    
    # Write file
    page_path = out_dir / f"{slug}.html"
    with open(page_path, 'w', encoding='utf-8') as f:
        f.write(HTML_TEMPLATE.format(title=title, body=body))

def build_all_project_pages(creators: List[Dict], out_dir: Path, root_input: Path, thumbs_dir: Path):
    print("Generating project pages...")
    
    for creator in creators:
        for project in creator['projects']:
            build_project_page(creator['name'], project, out_dir, root_input, thumbs_dir, creators)
            
def build_project_page(creator_name: str, project: Dict, out_dir: Path, root_input: Path, thumbs_dir: Path, creators: List[Dict]):
    project_title = project['title']
    slug = slugify(f"{creator_name}_{project_title}")
    print(f"Building project page: {slug}.html") 
    
    thumb_subdir = thumbs_dir / slug
    thumb_subdir.mkdir(parents=True, exist_ok=True)

    # Link external CSS
    css_links = """
    <link rel="stylesheet" href="../css/base.css">
    <link rel="stylesheet" href="../css/project.css">
    """

    body = css_links
    body += build_nav_links(
        ("Creators", "../index.html"),
        ("Tags", "../tags.html"),
        (creator_name, f"../creators/{slugify(creator_name)}.html")
    )

    title = f"{creator_name} - {project_title}"
    body += f"<h1>{title}</h1>"

    body += "<div class='project-layout'>"

    # Left Side
    body += "<div class='project-left'>"

    # Content
    body += "<div class='section-box'>"
    body += "<div class='section-title'>Preview</div>"
    body += "<hr>"
    body += "<div class='section-content markdown'>"

    body += "<div class='project-info'>"

    if project.get("thumbnail"):
        poster_path = root_input / project['thumbnail']
        thumbnail_path = get_thumbnail_path(thumbs_dir, slug, Path(project['thumbnail']), ThumbType.POSTER)
        generate_thumbnail(poster_path, thumbnail_path, ThumbType.POSTER)
        thumbnail_rel_path = get_relative_path(thumbnail_path, out_dir)
    else:
        thumbnail_rel_path = get_relative_path(thumbs_dir / DEFAULT_IMAGES[ThumbType.POSTER], out_dir)

    body += f"<img src='{thumbnail_rel_path}' alt='Preview of {project['title']}'>"

    body += "</div>"
    
    body += "</div>"  # section-content
    body += "</div>"  # section-box

    # Optional Info Text section
    info_text = project.get("info", "").strip()
    if info_text:
        body += "<div class='section-box'>"
        body += "<div class='section-title'>Info</div>"
        body += "<hr>"
        body += f"<div class='section-content'>{render_markdown(info_text)}</div>"
        body += "</div>"  #end info text section

    # Optional Featuring section
    def get_creator_info(name: str):
        for m in creators:
            if m["name"] == name:
                return m
        return None
        
    release_date = project.get("release_date", "")
    
    participants = [creator_name] if not is_collaboration(creator_name) else [name.strip() for name in creator_name.split(" & ")]
    for name in participants:
        creator = get_creator_info(name)
        if not creator:
            continue
        
        body += "<div class='section-box'>"
        body += f"<div class='section-title'>Featuring: {name}</div>"
        body += "<hr>"
        body += "<div class='section-content'>"
        body += "<div class='creator-info'>"

        portrait = creator.get("portrait")
        
        dob = creator.get("date_of_birth", "")
        age_text = ""
        if dob and release_date:
            try:
                dob_dt = datetime.strptime(dob, "%Y-%m-%d")
                release_dt = datetime.strptime(release_date, "%Y-%m-%d")
                age_text = calculate_age(dob_dt, release_dt)
            except Exception as e:
                print(f"Could not calculate age: {e}")
                age_text = ""
        
        if portrait:
            img_abs = root_input / portrait
            thumb_path = get_thumbnail_path(thumbs_dir, slugify(name), Path(portrait), ThumbType.PORTRAIT)
            generate_thumbnail(img_abs, thumb_path, ThumbType.PORTRAIT)
            thumb_rel = get_relative_path(thumb_path, out_dir)
        else:
            thumb_rel = get_relative_path(thumbs_dir / DEFAULT_IMAGES[ThumbType.PORTRAIT], out_dir)
        
        body += f"<img src='{thumb_rel}' alt='Portrait of {creator['name']}'>"
        body += "<div>"
        body += f"<p><strong>Name:</strong> <a href='../creators/{slugify(name)}.html'>{name}</a></p>"
        body += f"<p><strong>At Age:</strong> {age_text}</p>"
        
        body += "</div>"
        body += "</div>"
        body += "</div>"
        body += "</div>"  # end featuring section

    body += render_tag_section(project.get("tags", []))
    
    body += "</div>"

     # Right Side
    body += "<div class='project-right'>"
    
    # Videos
    #poster_attr = ""
    #if project.get("thumbnail"):
    #    poster_img = root_input / project['thumbnail']
    #    poster_thumb = get_thumbnail_path(thumbs_dir, slug, Path(project['thumbnail']), ThumbType.POSTER)
    #    generate_thumbnail(poster_img, poster_thumb, ThumbType.POSTER)
    #    poster_rel = get_relative_path(poster_thumb, out_dir)
    #    poster_attr = f" poster='{poster_rel}'"
    #else:
    #    poster_rel = get_relative_path(thumbs_dir / DEFAULT_IMAGES[ThumbType.POSTER], out_dir)
    #    poster_attr = f" poster='{poster_rel}'"

    # Optional Video section
    video_paths = project.get("videos", None)
    if video_paths:
        for video_path in video_paths:
            video_file = Path(video_path)
            video_title = video_file.stem
            video_rel = get_relative_path(root_input / video_path, out_dir)
    
            #body += "<div class='section-box fit-box'>"
            body += "<div class='section-box'>"
            body += f"<div class='section-title'>{video_title}</div>"
            body += "<hr>"
            body += "<div class='section-content'>"
            body += f"<video controls><source src='{video_rel}' type='video/mp4'></video>"
            body += "</div>"
            body += "</div>"  # end video section

    # Optional Image Groups section
    image_groups = project.get("image_groups", [])
    for group in image_groups:
        label = group.get("label", "Images")
        images = group.get("images", [])
    
        if not images:
            continue
    
        body += "<div class='section-box'>"
        body += f"<div class='section-title'>{label}</div>"
        body += "<hr>"
        body += "<div class='section-content'>"
        body += "<div class='image-gallery'>"
    
        for img_path in images:
            img_abs = root_input / img_path
            thumb_path = get_thumbnail_path(thumbs_dir, slug, Path(img_path), ThumbType.THUMB)
            generate_thumbnail(img_abs, thumb_path, ThumbType.THUMB)
            thumb_rel = get_relative_path(thumb_path, out_dir)
            original_rel = get_relative_path(img_abs, out_dir)
            body += f"<a href='{original_rel}' target='_blank'><img src='{thumb_rel}' alt='{label} image'></a>"
    
        body += "</div>"  # image-gallery
        body += "</div>"  # section-content
        body += "</div>"  # section-box
        
    body += "</div>"

    page_path = out_dir / f"{slug}.html"
    with open(page_path, 'w', encoding='utf-8') as f:
        f.write(HTML_TEMPLATE.format(title=title, body=body))

def collect_all_tags(creators: List[Dict]) -> Dict[str, set[str]]:
    tags = defaultdict(set)
    for creator in creators:
        for project in creator.get("projects", []):
            for tag in project.get("tags", []):
                if ":" in tag:
                    category, label = tag.split(":", 1)
                    tags[category.strip()].add(label.strip())
                else:
                    tags["Tag"].add(tag.strip())
    return tags

def build_tags_page(creators: List[Dict], output_path: Path):
    tags = collect_all_tags(creators)
                    
    # Link external CSS
    css_links = """
    <link rel="stylesheet" href="css/base.css">
    """

    body = css_links
    
    body += build_nav_links(
        ("Creators", "index.html"),
        ("Tags", None)
    )
    
    title = "All Tags"

    body += f"<h1>{title}</h1>"

    body += "<div class='section-box'>"
    body += "<div class='section-content tag-list'>"

    for category in sorted(tags.keys()):
        anchor = category.lower().replace(" ", "-")
        body += f"<div class='tag-category' id='{anchor}'><strong>{category}:</strong> "
        for tag in sorted(tags[category]):
            body += f"<a class='tag' href='index.html?tag={tag}'>{tag}</a>"
        body += "</div>"

    body += "</div></div>"

    tag_file = output_path / "tags.html"
    with open(tag_file, "w", encoding="utf-8") as f:
        f.write(HTML_TEMPLATE.format(title=title, body=body))
