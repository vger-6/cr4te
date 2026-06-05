from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .enums.domain import Domain
from .enums.visible_fields import ProjectField

__all__ = [
    "FacetLabels",
    "FacetRenderSpec",
    "FacetSpec",
    "PROJECT_FACETS",
    "PROJECT_FACET_BY_FIELD",
    "get_domain_project_metadata_fields",
    "get_domain_project_visible_metadata",
    "get_project_facet",
    "get_project_facet_label_defaults",
]


@dataclass(frozen=True)
class FacetLabels:
    singular: str
    plural: str

    def as_config_dict(self) -> dict[str, str]:
        return {
            "singular": self.singular,
            "plural": self.plural,
        }


@dataclass(frozen=True)
class FacetRenderSpec:
    separator: str = ", "
    searchable: bool = False
    clickable: bool = False
    tags: bool = False

    def as_config_dict(self) -> dict[str, Any]:
        return {
            "separator": self.separator,
            "searchable": self.searchable,
            "clickable": self.clickable,
            "tags": self.tags,
        }


@dataclass(frozen=True)
class FacetSpec:
    field: ProjectField
    labels: FacetLabels
    domains: frozenset[Domain]
    render: FacetRenderSpec = FacetRenderSpec()


_FILTERABLE = FacetRenderSpec(searchable=True, clickable=True, tags=True)
_FILTERABLE_LINES = FacetRenderSpec(separator="<br>", searchable=True, clickable=True, tags=True)
_LINES = FacetRenderSpec(separator="<br>")


PROJECT_FACETS: tuple[FacetSpec, ...] = (
    FacetSpec(ProjectField.PHOTOGRAPHERS, FacetLabels("Photographer", "Photographers"), frozenset({Domain.MODEL}), _LINES),
    FacetSpec(ProjectField.STUDIOS, FacetLabels("Studio", "Studios"), frozenset({Domain.MODEL, Domain.FILM, Domain.MUSIC}), _FILTERABLE_LINES),
    FacetSpec(ProjectField.DESIGNERS, FacetLabels("Designer", "Designers"), frozenset({Domain.MODEL}), _FILTERABLE_LINES),
    FacetSpec(ProjectField.POSES, FacetLabels("Pose", "Poses"), frozenset({Domain.MODEL}), _FILTERABLE_LINES),
    FacetSpec(ProjectField.MAKEUP_ARTISTS, FacetLabels("Makeup Artist", "Makeup Artists"), frozenset({Domain.MODEL}), _LINES),
    FacetSpec(ProjectField.STYLISTS, FacetLabels("Stylist", "Stylists"), frozenset({Domain.MODEL}), _LINES),
    FacetSpec(ProjectField.BRANDS, FacetLabels("Brand", "Brands"), frozenset({Domain.MODEL}), _FILTERABLE_LINES),
    FacetSpec(ProjectField.MAGAZINES, FacetLabels("Magazine", "Magazines"), frozenset({Domain.MODEL}), _FILTERABLE_LINES),
    FacetSpec(ProjectField.LANGUAGES, FacetLabels("Language", "Languages"), frozenset({Domain.BOOK}), _FILTERABLE),
    FacetSpec(ProjectField.PUBLISHERS, FacetLabels("Publisher", "Publishers"), frozenset({Domain.BOOK}), _FILTERABLE_LINES),
    FacetSpec(ProjectField.EDITORS, FacetLabels("Editor", "Editors"), frozenset({Domain.BOOK, Domain.FILM}), _LINES),
    FacetSpec(ProjectField.TRANSLATORS, FacetLabels("Translator", "Translators"), frozenset({Domain.BOOK}), _LINES),
    FacetSpec(ProjectField.ISBNS, FacetLabels("ISBN", "ISBNs"), frozenset({Domain.BOOK}), _FILTERABLE_LINES),
    FacetSpec(ProjectField.CITATIONS, FacetLabels("Citation", "Citations"), frozenset({Domain.BOOK}), _LINES),
    FacetSpec(ProjectField.COVER_ARTISTS, FacetLabels("Cover Artist", "Cover Artists"), frozenset({Domain.BOOK, Domain.MUSIC}), _FILTERABLE_LINES),
    FacetSpec(ProjectField.GENRES, FacetLabels("Genre", "Genres"), frozenset({Domain.BOOK, Domain.FILM, Domain.MUSIC}), _FILTERABLE),
    FacetSpec(ProjectField.ACTORS, FacetLabels("Actor", "Actors"), frozenset({Domain.FILM}), _FILTERABLE_LINES),
    FacetSpec(ProjectField.PRODUCERS, FacetLabels("Producer", "Producers"), frozenset({Domain.FILM, Domain.MUSIC}), _LINES),
    FacetSpec(ProjectField.COMPOSERS, FacetLabels("Composer", "Composers"), frozenset({Domain.MUSIC}), _FILTERABLE_LINES),
    FacetSpec(ProjectField.CINEMATOGRAPHERS, FacetLabels("Cinematographer", "Cinematographers"), frozenset({Domain.FILM}), _FILTERABLE_LINES),
    FacetSpec(ProjectField.SCORE_COMPOSERS, FacetLabels("Score Composer", "Score Composers"), frozenset({Domain.FILM}), _FILTERABLE_LINES),
    FacetSpec(ProjectField.VISUAL_EFFECTS, FacetLabels("Visual Effect", "Visual Effects"), frozenset({Domain.FILM}), _FILTERABLE_LINES),
    FacetSpec(ProjectField.WRITERS, FacetLabels("Writer", "Writers"), frozenset({Domain.FILM}), _FILTERABLE_LINES),
    FacetSpec(ProjectField.COSTUME_DESIGNERS, FacetLabels("Costume Designer", "Costume Designers"), frozenset({Domain.FILM}), _LINES),
    FacetSpec(ProjectField.MUSICIANS, FacetLabels("Musician", "Musicians"), frozenset({Domain.MUSIC}), _FILTERABLE_LINES),
    FacetSpec(ProjectField.LABELS, FacetLabels("Label", "Labels"), frozenset({Domain.MUSIC}), _FILTERABLE_LINES),
    FacetSpec(ProjectField.INSTRUMENTS, FacetLabels("Instrument", "Instruments"), frozenset({Domain.MUSIC}), _FILTERABLE),
    FacetSpec(ProjectField.MEDIUMS, FacetLabels("Medium", "Mediums"), frozenset({Domain.ART}), _FILTERABLE),
    FacetSpec(ProjectField.MATERIALS, FacetLabels("Material", "Materials"), frozenset({Domain.ART}), _FILTERABLE),
    FacetSpec(ProjectField.EXHIBITIONS, FacetLabels("Exhibition", "Exhibitions"), frozenset({Domain.ART}), _FILTERABLE_LINES),
    FacetSpec(ProjectField.PERIODS, FacetLabels("Period", "Periods"), frozenset({Domain.ART}), _FILTERABLE),
)

PROJECT_FACET_BY_FIELD = {facet.field: facet for facet in PROJECT_FACETS}


def get_project_facet(field: ProjectField) -> FacetSpec | None:
    return PROJECT_FACET_BY_FIELD.get(field)


def get_domain_project_metadata_fields(domain: Domain | None) -> tuple[ProjectField, ...]:
    selected_domain = domain or Domain.CREATOR
    if selected_domain == Domain.CREATOR:
        return ()
    return tuple(facet.field for facet in PROJECT_FACETS if selected_domain in facet.domains)


def get_domain_project_visible_metadata(domain: Domain | None) -> dict[ProjectField, dict[str, Any]]:
    return {
        field: PROJECT_FACET_BY_FIELD[field].render.as_config_dict()
        for field in get_domain_project_metadata_fields(domain)
    }


def get_project_facet_label_defaults() -> dict[str, dict[str, str]]:
    return {
        facet.field.value: facet.labels.as_config_dict()
        for facet in PROJECT_FACETS
    }
