from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from time import perf_counter
from typing import Callable, TypeVar

from .build_issues import BuildIssueError
from .build_metrics import BuildTimings
from .build_summary import BuildSummary
from .html_builder import build_html_pages_streaming
from .library_builder import build_library_index, load_indexed_creator
from .metadata_manager import MetadataWriteResult, reconcile_metadata_files
from .output_preparation import clear_output_folder
from .schemas.config_schema import AppConfig
from .themes import discover_themes

__all__ = [
    "BuildPhase",
    "BuildPhaseError",
    "BuildRequest",
    "BuildRunResult",
    "run_build",
]

logger = logging.getLogger(__name__)
PhaseResult = TypeVar("PhaseResult")


class BuildPhase(str, Enum):
    THEME_DISCOVERY = "theme discovery"
    OUTPUT_PREPARATION = "output preparation"
    METADATA_RECONCILIATION = "metadata reconciliation"
    LIBRARY_INDEXING = "library indexing"
    HTML_RENDERING = "HTML rendering"


class BuildPhaseError(RuntimeError):
    def __init__(self, phase: BuildPhase, exc: OSError):
        self.phase = phase
        super().__init__(f"Build failed during {phase.value}: {exc}")


@dataclass(frozen=True)
class BuildRequest:
    input_dir: Path
    output_dir: Path
    config: AppConfig
    custom_themes_dir: Path | None = None
    clear_thumbnail_cache: bool = False
    strict: bool = False


@dataclass(frozen=True)
class BuildRunResult:
    summary: BuildSummary
    index_html_path: Path
    metadata_result: MetadataWriteResult


def _run_phase(phase: BuildPhase, action: Callable[[], PhaseResult]) -> tuple[PhaseResult, float]:
    started = perf_counter()
    try:
        result = action()
    except BuildIssueError:
        raise
    except OSError as exc:
        raise BuildPhaseError(phase, exc) from exc
    return result, perf_counter() - started


def _prepare_output(request: BuildRequest) -> None:
    if request.output_dir.exists():
        clear_output_folder(request.output_dir, request.clear_thumbnail_cache)
    else:
        request.output_dir.mkdir(parents=True, exist_ok=True)


def run_build(request: BuildRequest) -> BuildRunResult:
    logger.info("Discovering themes...")
    theme_registry, theme_discovery_seconds = _run_phase(
        BuildPhase.THEME_DISCOVERY,
        lambda: discover_themes(request.custom_themes_dir, strict=request.strict),
    )

    _, output_preparation_seconds = _run_phase(
        BuildPhase.OUTPUT_PREPARATION,
        lambda: _prepare_output(request),
    )

    logger.info("Reconciling metadata...")
    project_facet_fields = request.config.site_rendering.project_metadata.configured_fields()
    metadata_result, metadata_reconciliation_seconds = _run_phase(
        BuildPhase.METADATA_RECONCILIATION,
        lambda: reconcile_metadata_files(
            request.input_dir,
            request.config.media_rules,
            project_facet_fields=project_facet_fields,
        ),
    )
    logger.info(metadata_result.summary_line())

    logger.info("Indexing media library...")
    library_index, library_indexing_seconds = _run_phase(
        BuildPhase.LIBRARY_INDEXING,
        lambda: build_library_index(
            request.input_dir,
            request.config.media_rules,
            strict=request.strict,
        ),
    )

    logger.info("Building HTML site...")
    html_result, html_rendering_seconds = _run_phase(
        BuildPhase.HTML_RENDERING,
        lambda: build_html_pages_streaming(
            library_index,
            theme_registry,
            request.output_dir,
            request.config.site_labels,
            request.config.site_rendering,
            lambda summary: load_indexed_creator(
                library_index,
                summary,
                request.config.media_rules,
            ),
            strict=request.strict,
        ),
    )

    summary = BuildSummary.from_library_index(
        library_index,
        additional_issues=(*metadata_result.issues, *theme_registry.issues, *html_result.issues),
        timings=BuildTimings(
            theme_discovery_seconds=theme_discovery_seconds,
            output_preparation_seconds=output_preparation_seconds,
            metadata_reconciliation_seconds=metadata_reconciliation_seconds,
            library_indexing_seconds=library_indexing_seconds,
            html_rendering_seconds=html_rendering_seconds,
        ),
        asset_statistics=html_result.asset_statistics,
    )
    return BuildRunResult(summary, html_result.index_html_path, metadata_result)
