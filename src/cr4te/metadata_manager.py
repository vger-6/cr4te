from __future__ import annotations

import copy
import json
import logging
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from json import JSONDecodeError
from pathlib import Path
from typing import Any

from .constants import CR4TE_JSON_FILE_NAME
from .creator_classification import infer_creator_type
from .build_issues import BuildIssue, IssueScope
from .enums.creator_type import CreatorType
from .enums.visible_fields import ProjectField
from .library_issues import issue_from_exception
from .library_metadata import MetadataIOError, MetadataJsonError, MetadataLoadError, MetadataShapeError
from .library_scan import iter_creator_dirs, iter_project_dirs
from .metadata_templates import (
    CollaborationMetadataTemplate,
    CreatorMetadataTemplate,
    ProjectMetadataTemplate,
)
from .schemas.config_schema import MediaRules
from .utils import text_utils

__all__ = [
    "MetadataWriteResult",
    "clean_metadata_files",
    "reconcile_metadata_files",
]

logger = logging.getLogger(__name__)


@dataclass
class MetadataWriteResult:
    created: list[Path] = field(default_factory=list)
    updated: list[Path] = field(default_factory=list)
    unchanged: list[Path] = field(default_factory=list)
    skipped: list[Path] = field(default_factory=list)
    issues: list[BuildIssue] = field(default_factory=list)

    def summary_line(self) -> str:
        return (
            "Metadata summary: "
            f"created={len(self.created)}, "
            f"updated={len(self.updated)}, "
            f"unchanged={len(self.unchanged)}, "
            f"skipped={len(self.skipped)}"
        )


def reconcile_metadata_files(
    input_dir: Path,
    media_rules: MediaRules,
    project_facet_fields: Iterable[ProjectField] = (),
    dry_run: bool = False,
) -> MetadataWriteResult:
    input_dir = input_dir.resolve()
    project_facet_fields = tuple(project_facet_fields)
    result = MetadataWriteResult()

    for creator_dir in iter_creator_dirs(input_dir, media_rules):
        metadata_path = creator_dir / CR4TE_JSON_FILE_NAME
        existing, invalid = _load_reconciliation_json(
            metadata_path,
            creator_dir,
            IssueScope.CREATOR,
            result,
        )
        nested_projects = existing.get("projects", {}) if isinstance(existing, dict) else {}
        if not isinstance(nested_projects, dict):
            nested_projects = {}
        if not invalid:
            try:
                creator_type = _selected_creator_type(existing or {}, creator_dir.name, media_rules)
                template = _creator_metadata_template(creator_dir, media_rules, creator_type)
                reconciled = _reconcile_creator_metadata(existing or {}, template, creator_type)
            except ValueError as exc:
                result.skipped.append(metadata_path)
                result.issues.append(issue_from_exception(creator_dir, IssueScope.CREATOR, exc))
            else:
                _record_metadata_write(metadata_path, existing, reconciled, result, dry_run)

        for project_dir in iter_project_dirs(creator_dir, media_rules):
            project_metadata_path = project_dir / CR4TE_JSON_FILE_NAME
            existing_project, invalid = _load_reconciliation_json(
                project_metadata_path,
                project_dir,
                IssueScope.PROJECT,
                result,
            )
            if invalid:
                continue

            seeded_project = existing_project
            if seeded_project is None:
                nested_project = nested_projects.get(project_dir.name)
                seeded_project = nested_project if isinstance(nested_project, dict) else {}

            project_template = _project_metadata_template(project_dir, project_facet_fields)
            reconciled_project = _reconcile_project_metadata(seeded_project, project_template, project_facet_fields)
            _record_metadata_write(project_metadata_path, existing_project, reconciled_project, result, dry_run)

    return result


def _creator_metadata_template(
    creator_dir: Path,
    media_rules: MediaRules,
    creator_type: CreatorType,
) -> CreatorMetadataTemplate:
    creator_name = creator_dir.name

    if creator_type == CreatorType.COLLABORATION:
        collaboration = CollaborationMetadataTemplate(
            members=text_utils.multi_split(creator_name, media_rules.collaboration_separators),
        )
        return CreatorMetadataTemplate(
            display_name=creator_name,
            type=creator_type,
            collaboration=collaboration,
        )

    return CreatorMetadataTemplate(
        display_name=creator_name,
        type=creator_type,
    )


def _project_metadata_template(project_dir: Path, project_facet_fields: Sequence[ProjectField]) -> ProjectMetadataTemplate:
    return ProjectMetadataTemplate(
        display_title=project_dir.name,
        facet_fields=tuple(project_facet_fields),
    )


def _selected_creator_type(existing: dict[str, Any], creator_name: str, media_rules: MediaRules) -> CreatorType:
    raw_type = existing.get("type")
    if raw_type:
        return CreatorType(raw_type)
    return infer_creator_type(creator_name, media_rules.collaboration_separators)


def _record_metadata_write(
    metadata_path: Path,
    existing: dict[str, Any] | None,
    reconciled: dict[str, Any],
    result: MetadataWriteResult,
    dry_run: bool,
) -> None:
    if not metadata_path.exists():
        logger.info(f"{'[DRY-RUN] ' if dry_run else ''}Creating metadata: {metadata_path}")
        if not dry_run:
            _write_json(metadata_path, reconciled)
        result.created.append(metadata_path)
        return

    if reconciled == existing:
        result.unchanged.append(metadata_path)
        return

    logger.info(f"{'[DRY-RUN] ' if dry_run else ''}Updating metadata: {metadata_path}")
    if not dry_run:
        _write_json(metadata_path, reconciled)
    result.updated.append(metadata_path)


def _reconcile_creator_metadata(
    existing: dict[str, Any],
    template: CreatorMetadataTemplate,
    creator_type: CreatorType,
) -> dict[str, Any]:
    merged = _merge_missing(existing, template.as_json())
    merged["type"] = creator_type.value

    _prune_inactive_creator_branch(merged, creator_type)
    merged.pop("projects", None)
    return merged


def _prune_inactive_creator_branch(merged: dict[str, Any], creator_type: CreatorType) -> None:
    if creator_type == CreatorType.COLLABORATION:
        inactive_key = "person"
    else:
        inactive_key = "collaboration"

    merged.pop(inactive_key, None)


def _reconcile_project_metadata(
    existing: dict[str, Any],
    project_template: ProjectMetadataTemplate,
    project_facet_fields: Sequence[ProjectField],
) -> dict[str, Any]:
    merged = _merge_missing(existing, project_template.as_json())
    _prune_project_facets(merged, project_facet_fields)
    return merged


def _prune_project_facets(project: dict[str, Any], project_facet_fields: Sequence[ProjectField]) -> None:
    facets = project.get("facets")
    if not isinstance(facets, dict):
        return

    configured_fields = {field.value for field in project_facet_fields}
    for configured_field in configured_fields:
        facets.setdefault(configured_field, [])

    for facet_name in list(facets):
        if facet_name not in configured_fields and not _has_user_values(facets[facet_name], []):
            del facets[facet_name]


def _merge_missing(existing: dict[str, Any], template: dict[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(existing)
    for key, template_value in template.items():
        if key not in merged:
            merged[key] = copy.deepcopy(template_value)
            continue

        existing_value = merged[key]
        if isinstance(existing_value, dict) and isinstance(template_value, dict):
            merged[key] = _merge_missing(existing_value, template_value)

    return merged


def _has_user_values(value: Any, default: Any) -> bool:
    if value == default:
        return False

    if isinstance(value, dict):
        default_dict = default if isinstance(default, dict) else {}
        return any(_has_user_values(child_value, default_dict.get(key)) for key, child_value in value.items())

    if isinstance(value, list):
        return bool(value)

    if isinstance(value, str):
        return bool(value.strip())

    if value is None:
        return False

    return value != default


def _load_reconciliation_json(
    metadata_path: Path,
    owner_path: Path,
    scope: IssueScope,
    result: MetadataWriteResult,
) -> tuple[dict[str, Any] | None, bool]:
    try:
        return _load_optional_json(metadata_path), False
    except MetadataLoadError as exc:
        result.skipped.append(metadata_path)
        result.issues.append(issue_from_exception(owner_path, scope, exc))
        return None, True


def _load_optional_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None

    try:
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)
    except JSONDecodeError as exc:
        raise MetadataJsonError(f"Invalid JSON in metadata file {path}: {exc.msg}") from exc
    except OSError as exc:
        raise MetadataIOError(f"Unable to read metadata file {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise MetadataShapeError(f"Metadata file must contain a JSON object: {path}")

    return data


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(data, indent=2, ensure_ascii=False)
    path.write_text(rendered + "\n", encoding="utf-8")


def clean_metadata_files(input_dir: Path, dry_run: bool = False) -> None:
    metadata_files = sorted(path for path in input_dir.rglob(CR4TE_JSON_FILE_NAME) if path.is_file())

    for json_path in metadata_files:
        logger.info(f"{'[DRY-RUN] ' if dry_run else ''}Deleting: {json_path}")
        if not dry_run:
            json_path.unlink()

    logger.info(f"{'Would delete' if dry_run else 'Deleted'} {len(metadata_files)} metadata files")
