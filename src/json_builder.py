import logging
import json
from enum import Enum
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple, Callable, TypeAlias, DefaultDict
from datetime import datetime
from collections import defaultdict
from dataclasses import dataclass, field

from pydantic import ValidationError

import constants
import utils.json_utils as json_utils
import utils.text_utils as text_utils
import utils.image_utils as image_utils
from enums.orientation import Orientation
from context.json_context import JsonBuildContext
from validators.cr4te_schema import Creator as CreatorSchema

__all__ = ["build_creator_json_files", "clean_creator_json_files"]

logger = logging.getLogger(__name__)

ImageHandler: TypeAlias = Callable[[Path, Optional[Path]], tuple[Optional[Path], "ImageHandler"]]

IMAGE_EXTS = (".jpg", ".jpeg", ".png")
VIDEO_EXTS = (".mp4", ".m4v")
AUDIO_EXTS = (".mp3", ".m4a")
DOC_EXTS = (".pdf",)
TEXT_EXTS = (".md",)

# TODO: Move to utils
def _normalize_date(date_str: str) -> str:
    """
    Validates and normalizes a date string.
    Accepts:
        - YYYY
        - YYYY-MM
        - YYYY-MM-DD
    Returns normalized string if valid, otherwise "".
    """
    if not isinstance(date_str, str):
        return ""

    date_str = date_str.strip()
    if not date_str:
        return ""
        
    for fmt in ("%Y-%m-%d", "%Y-%m", "%Y"):
        try:
            parsed = datetime.strptime(date_str, fmt)
            return parsed.strftime(fmt)
        except ValueError:
            continue

    return ""
        
def _is_excluded_path(path: Path, exclude_prefixes: tuple[str, ...]) -> bool:
    return any(part.startswith(exclude_prefixes) or part.startswith('.') for part in path.parts)
        
def _validate_creator(creator: Dict[str, Any]) -> None:
    try:
        CreatorSchema(**creator)

    except ValidationError as e:
        name = creator.get("name", "<unknown>")
        error_lines = [f"[{name}] {err['loc'][0]}: {err['msg']}" for err in e.errors()]
        formatted = "\n".join(error_lines)
        raise ValueError(f"Validation failed for creator '{name}':\n{formatted}")
             
def _is_collaboration(name: str, separators: Optional[List[str]]) -> bool:
    if not separators:
        return False
    return any(sep in name for sep in separators)
    
def _load_existing_json(json_path: Path) -> Dict[str, Any]:
    if json_path.exists():
        return json_utils.load_json(json_path)
    return {}

class ImageSelector:
    def __init__(self, basename: str, orientation: Orientation, auto_find: bool = True):
        self.basename = basename
        self.orientation = orientation
        self.selected: Optional[Path] = None
        self._handler: ImageHandler = self._image_init if auto_find else self._image_by_name

    def consider(self, image_path: Path):
        self.selected, self._handler = self._handler(image_path, self.selected)

    # --- Handler methods ---
    def _image_init(self, image_path: Path, candidate: Optional[Path]) -> tuple[Optional[Path], ImageHandler]:
        stem = image_path.stem.lower()
        if stem == self.basename:
            return image_path, self._image_done
        elif image_utils.infer_image_orientation(image_path) == self.orientation:
            return image_path, self._image_by_name
        else:
            return candidate or image_path, self._image_init

    def _image_by_name(self, image_path: Path, candidate: Optional[Path]) -> tuple[Optional[Path], ImageHandler]:
        stem = image_path.stem.lower()
        if stem == self.basename:
            return image_path, self._image_done
        else:
            return candidate, self._image_by_name

    def _image_done(self, image_path: Path, candidate: Optional[Path]) -> tuple[Optional[Path], ImageHandler]:
        return candidate, self._image_done
    
class RootType(Enum):
    CREATOR = "creator"
    PROJECT = "project"

@dataclass
class MediaBucket:
    ctx: JsonBuildContext
    portrait_selector: ImageSelector
    cover_selector: Optional[ImageSelector] = None
    videos: List[Dict[str, str]] = field(default_factory=list)
    tracks: List[str] = field(default_factory=list)
    images: List[str] = field(default_factory=list)
    documents: List[str] = field(default_factory=list)
    texts: List[str] = field(default_factory=list)

    def _find_video_poster(self, video_path: Path, input_dir: Path) -> Path | None:
        """
        Find an image in the same directory with the same stem as the video.
        Returns a Path relative to input_dir, or None if not found.
        """
        for img_ext in IMAGE_EXTS:
            candidate = video_path.with_suffix(img_ext)
            if candidate.exists():
                return candidate.relative_to(input_dir)
        return None
    
    def _is_video_poster_candidate(self, image_path: Path) -> bool:
        """
        Returns True if an image has a sibling video file with the same stem.
        """
        for vid_ext in VIDEO_EXTS:
            if image_path.with_suffix(vid_ext).exists():
                return True
        return False

    def add(self, media_path: Path, root_type: RootType) -> None:
        suffix = media_path.suffix.lower()
        stem = media_path.stem.lower()
        rel = media_path.relative_to(self.ctx.input_dir)

        if suffix in VIDEO_EXTS:
            poster = self._find_video_poster(media_path, self.ctx.input_dir)
            self.videos.append({
                "file": str(rel),
                "poster": str(poster) if poster else ""
            })

        elif suffix in AUDIO_EXTS:
            self.tracks.append(str(rel))

        elif suffix in IMAGE_EXTS and not self._is_video_poster_candidate(media_path):

            if stem not in (self.ctx.cover_basename, self.ctx.portrait_basename):
                self.images.append(str(rel))

            self.portrait_selector.consider(media_path)

            if root_type == RootType.PROJECT:
                self.cover_selector.consider(media_path)

        elif suffix in DOC_EXTS:
            self.documents.append(str(rel))

        elif suffix in TEXT_EXTS and media_path.name.lower() != self.ctx.readme_file_name.lower():
            self.texts.append(str(rel))   

@dataclass
class CreatorMediaIndex:
    ctx: JsonBuildContext
    creator_media: Dict[Path, MediaBucket] = field(default_factory=dict)
    project_media: Dict[str, Dict[Path, MediaBucket]] = field(default_factory=dict)

    def __post_init__(self):
        self.portrait_selector = ImageSelector(self.ctx.portrait_basename, Orientation.PORTRAIT, self.ctx.auto_find_portrait)
        self.cover_selectors: DefaultDict[str, ImageSelector] = defaultdict(lambda: ImageSelector(self.ctx.cover_basename, Orientation.LANDSCAPE, True))

    def _creator_bucket(self, folder: Path) -> MediaBucket:
        if folder not in self.creator_media:
            self.creator_media[folder] = MediaBucket(self.ctx, self.portrait_selector)
        return self.creator_media[folder]

    def _project_bucket(self, project_name: str, folder: Path) -> MediaBucket:
        proj = self.project_media.setdefault(project_name, {})
        if folder not in proj:
            proj[folder] = MediaBucket(self.ctx, self.portrait_selector, self.cover_selectors[project_name])
        return proj[folder]
    
    def _classify_media_path(self, path: Path, metadata_folder: str) -> tuple[RootType, Optional[str], Path]:
        parts = path.parts

        if len(parts) <= 2:
            return RootType.CREATOR, None, path.parent

        if parts[1] == metadata_folder:
            return RootType.CREATOR, None, path.parent

        project_name =  parts[1]
        return RootType.PROJECT, project_name, path.parent
    
    def add_media(self, media_path: Path) -> None:
        rel_path = media_path.relative_to(self.ctx.input_dir)

        root_type, project_name, rel_media_folder_path = self._classify_media_path(rel_path, self.ctx.metadata_folder_name)

        if root_type == RootType.CREATOR:
            bucket = self._creator_bucket(rel_media_folder_path)
        else:
            bucket = self._project_bucket(project_name, rel_media_folder_path)

        bucket.add(media_path, root_type)
    
    def get_selected_portrait(self) -> Optional[Path]:
        return self.portrait_selector.selected
    
    def get_selected_cover(self, project_name: str) -> Optional[Path]:
        return self.cover_selectors[project_name].selected
    
def _build_media_groups(media_dict: Dict[Path, MediaBucket], root_depth: int) -> List[Dict[str, Any]]:
    media_groups = []
    for rel_media_folder_path, media in media_dict.items():
       media_groups.append({
            "is_root": len(rel_media_folder_path.parts) == root_depth,
            "videos": sorted(media.videos, key=lambda v: v["file"]),
            "tracks": sorted(media.tracks),
            "images": sorted(media.images),
            "documents": sorted(media.documents),
            "texts": sorted(media.texts),
            "rel_dir_path": str(rel_media_folder_path)
        })
    return media_groups

def _iter_media_files(ctx, creator_dir):
    # Helper to check max depth
    def _is_within_search_depth(path: Path) -> bool:
        return ctx.max_search_depth is None or len(path.relative_to(creator_dir).parts) <= ctx.max_search_depth + 1
    
    for media_path in creator_dir.rglob("*"):
        if not media_path.is_file():
            continue

        if _is_excluded_path(media_path, (ctx.global_exclude_prefix,)):
            continue

        if not _is_within_search_depth(media_path):
            continue

        yield media_path

def _build_creator(ctx: JsonBuildContext, creator_dir: Path) -> Dict[str, Any]:
    media_index = CreatorMediaIndex(ctx)
    for media_path in _iter_media_files(ctx, creator_dir):
        media_index.add_media(media_path)

    existing_creator = _load_existing_json(creator_dir / constants.CR4TE_JSON_FILE_NAME)
    existing_projects = { p["title"]: p for p in existing_creator.get("projects", []) if "title" in p }
    projects = []
    for project_name, folders in media_index.project_media.items():
        cover = media_index.get_selected_cover(project_name)
        projects.append({
            "title": project_name,
            "release_date": _normalize_date(existing_projects.get(project_name, {}).get("release_date", "")),
            "cover": str(cover.relative_to(ctx.input_dir)) if cover else "",
            "info": text_utils.read_text(creator_dir / project_name / ctx.readme_file_name) or existing_projects.get(project_name, {}).get("info", ""),
            "media_groups": _build_media_groups(folders, root_depth=2),
            "tags": existing_projects.get(project_name, {}).get("tags", [])
        })
    
    creator_name = creator_dir.name
    separators = ctx.collaboration_separators
    is_collab = existing_creator.get("is_collaboration")
    if is_collab is None:
        is_collab = _is_collaboration(creator_name, separators)

    # Build creator record
    portrait = media_index.get_selected_portrait()
    creator = {
        "name": creator_name,
        "is_collaboration": is_collab,
        "born_or_founded": _normalize_date(existing_creator.get("born_or_founded", "")),
        "died_or_dissolved": _normalize_date(existing_creator.get("died_or_dissolved", "")),
        "active_since": _normalize_date(existing_creator.get("active_since", "")),
        "nationality": existing_creator.get("nationality", ""),
        "aliases": existing_creator.get("aliases", []),
        "portrait":  str(portrait.relative_to(ctx.input_dir)) if portrait else "",
        "info": text_utils.read_text(creator_dir / ctx.readme_file_name) or existing_creator.get("info", ""),
        "tags": existing_creator.get("tags", []),
        "projects": projects,
        "media_groups":  _build_media_groups(media_index.creator_media, root_depth=1),
        "collaborations": [],
    }

    if is_collab:
        members = [name.strip() for name in text_utils.multi_split(creator_name, separators)]
        creator["members"] = existing_creator.get("members", members)
    else:
        creator["members"] = []
    
    return creator
    
def _link_creator_collaborations(creators: List[Dict[str, Any]]) -> None:
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
            
def _write_json_files(creator_records: List[Tuple[Path, Dict[str, Any]]]) -> None:
    """
    Writes each creator's JSON data to <creator_dir>/cr4te.json.
    """
    for creator_dir, creator_data in creator_records:
        json_path = creator_dir / constants.CR4TE_JSON_FILE_NAME
        
        existing = _load_existing_json(json_path)
        if existing == creator_data:
            continue
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(creator_data, f, indent=2)
            
def build_creator_json_files(input_dir: Path, media_rules: dict[str, Any]) -> None:
    ctx = JsonBuildContext(input_dir, media_rules)

    creator_records = []
    for creator_dir in sorted(ctx.input_dir.iterdir()):
        if not creator_dir.is_dir() or _is_excluded_path(creator_dir, (ctx.global_exclude_prefix,)):
            continue
        logger.info(f"Processing: {creator_dir.name}")

        creator_data = _build_creator(ctx, creator_dir)
        creator_records.append((creator_dir, creator_data))

    _link_creator_collaborations([creator_data for _, creator_data in creator_records])
    
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
            logger.info(f"{'[DRY-RUN] ' if dry_run else ''}Deleting: {json_path}")
            if not dry_run:
                try:
                    json_path.unlink()
                    deleted += 1
                except Exception as e:
                    logger.error(f"Deleting {json_path}: {e}")
                    skipped += 1
        else:
            continue

    logger.info(
        f"\nSummary:\n"
        f"\tTotal {constants.CR4TE_JSON_FILE_NAME} files found: {total}\n"
        f"\tDeleted: {deleted}\n"
        f"\tSkipped/errors: {skipped}"
        )
    if dry_run:
        logger.info("\t(Dry-run mode: no files were deleted)")
