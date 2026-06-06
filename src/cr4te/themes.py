from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .build_issues import BuildIssue, BuildIssueError, BuildIssuePolicy, IssueCode, IssueScope
from .constants import CR4TE_THEMES_DIR

__all__ = [
    "DEFAULT_THEME_ID",
    "ThemeDefinition",
    "ThemeRegistry",
    "discover_builtin_themes",
    "discover_themes",
    "get_default_theme",
]

DEFAULT_THEME_ID = "frozen-aurora"
THEME_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


@dataclass(frozen=True)
class ThemeDefinition:
    id: str
    display_name: str
    source_path: Path
    is_builtin: bool

    @property
    def css_class(self) -> str:
        return f"theme-{self.id}"

    @property
    def output_filename(self) -> str:
        return f"{self.id}.css"


@dataclass(frozen=True)
class ThemeRegistry:
    themes: tuple[ThemeDefinition, ...]
    issues: tuple[BuildIssue, ...] = ()

    @property
    def default_theme(self) -> ThemeDefinition:
        return get_default_theme(self.themes)


def get_default_theme(themes: tuple[ThemeDefinition, ...]) -> ThemeDefinition:
    for theme in themes:
        if theme.id == DEFAULT_THEME_ID:
            return theme
    raise ValueError(f"Default theme is unavailable: {DEFAULT_THEME_ID}")


def _theme_issue(path: Path, code: IssueCode, message: str) -> BuildIssue:
    return BuildIssue(path=path, message=message, scope=IssueScope.THEME, code=code)


def _load_theme(path: Path, is_builtin: bool) -> ThemeDefinition:
    theme_id = path.stem
    if not THEME_ID_PATTERN.fullmatch(theme_id):
        raise ValueError("Theme filenames must use lowercase letters, numbers, and single hyphens")

    css_class = f"theme-{theme_id}"
    css = path.read_text(encoding="utf-8")
    if not re.search(rf"\.{re.escape(css_class)}\s*\{{", css):
        raise ValueError(f"Theme CSS must define the expected selector: .{css_class}")

    return ThemeDefinition(
        id=theme_id,
        display_name=theme_id.replace("-", " ").title(),
        source_path=path,
        is_builtin=is_builtin,
    )


def _discover_theme_dir(
    themes_dir: Path,
    is_builtin: bool,
    seen_ids: set[str],
    policy: BuildIssuePolicy,
) -> list[ThemeDefinition]:
    if not themes_dir.exists():
        return []

    themes: list[ThemeDefinition] = []
    for path in sorted(themes_dir.iterdir(), key=lambda candidate: candidate.name.lower()):
        if not path.is_file():
            continue
        if path.suffix.lower() != ".css":
            policy.handle(_theme_issue(path, IssueCode.INVALID_THEME, "Theme folder files must use the .css extension"))
            continue

        try:
            theme = _load_theme(path, is_builtin)
        except (OSError, UnicodeError, ValueError) as exc:
            policy.handle(_theme_issue(path, IssueCode.INVALID_THEME, str(exc)), exc)
            continue

        if theme.id in seen_ids:
            policy.handle(
                _theme_issue(path, IssueCode.DUPLICATE_THEME, f"Duplicate theme id: {theme.id}"),
            )
            continue

        seen_ids.add(theme.id)
        themes.append(theme)
    return themes


def discover_themes(custom_themes_dir: Path | None, strict: bool = False) -> ThemeRegistry:
    policy = BuildIssuePolicy(strict=strict)
    seen_ids: set[str] = set()
    themes = _discover_theme_dir(CR4TE_THEMES_DIR, True, seen_ids, policy)
    if custom_themes_dir is not None:
        if not custom_themes_dir.exists():
            issue = _theme_issue(
                custom_themes_dir,
                IssueCode.MISSING_REFERENCE,
                "Custom themes folder does not exist",
            )
            raise BuildIssueError(issue)
        if not custom_themes_dir.is_dir():
            issue = _theme_issue(
                custom_themes_dir,
                IssueCode.INVALID_THEME,
                "Custom themes path must be a directory",
            )
            raise BuildIssueError(issue)
        themes.extend(_discover_theme_dir(custom_themes_dir, False, seen_ids, policy))
    registry = ThemeRegistry(tuple(themes), tuple(policy.issues))

    try:
        registry.default_theme
    except ValueError as exc:
        issue = _theme_issue(CR4TE_THEMES_DIR, IssueCode.MISSING_REFERENCE, str(exc))
        raise BuildIssueError(issue) from exc

    return registry


def discover_builtin_themes() -> tuple[ThemeDefinition, ...]:
    return discover_themes(None, strict=True).themes
