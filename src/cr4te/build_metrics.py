from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "AssetStatistics",
    "BuildTimings",
]


@dataclass
class AssetStatistics:
    symbolic_links_created: int = 0
    hard_links_created: int = 0
    media_links_reused: int = 0
    source_thumbnails_generated: int = 0
    source_thumbnails_reused: int = 0
    default_thumbnail_uses: int = 0
    source_freshness_checks: int = 0


@dataclass(frozen=True)
class BuildTimings:
    theme_discovery_seconds: float = 0
    output_preparation_seconds: float = 0
    metadata_reconciliation_seconds: float = 0
    library_indexing_seconds: float = 0
    html_rendering_seconds: float = 0

    @property
    def total_seconds(self) -> float:
        return (
            self.theme_discovery_seconds
            + self.output_preparation_seconds
            + self.metadata_reconciliation_seconds
            + self.library_indexing_seconds
            + self.html_rendering_seconds
        )
