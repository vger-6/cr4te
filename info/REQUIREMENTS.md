# cr4te Requirements

These are durable product and design requirements for cr4te. They must hold unless this file is explicitly revised.

## Requirement Conventions

- Each requirement has a stable ID for references from tests, documentation, issues, and commits.
- `must` and `must not` describe required behavior.
- Implementation and refactoring guidance belongs in [REFACTORING_GUIDELINES.md](REFACTORING_GUIDELINES.md).
- Planned but uncommitted product ideas belong in [TODO.md](TODO.md).

## Metadata And Identity

- **META-001:** Metadata must live beside the folder it describes. Creator metadata lives in each creator folder's `cr4te.json`; project metadata lives in each project folder's `cr4te.json`. Creator metadata must not nest project metadata under `projects`.
- **META-002:** Canonical creator names and project titles must come exclusively from their folder names. They drive identity, output-path hashes, and creator-reference resolution and must not appear as `name` or `title` fields in `cr4te.json`.
- **META-003:** Creator `display_name` and project `display_title` must be editable metadata whose generated defaults are their folder names. Display values drive visible labels, user-facing sorting, and search; blank display values must fall back to the canonical folder name.
- **META-004:** Collaboration `members` and creator `collaborations` must store canonical creator folder names. Resolved references display the referenced creator's `display_name`; unresolved member strings display unchanged.
- **META-005:** `cr4te.json` must contain editable structured metadata only. It must not contain generated scan output such as `media_groups`, and it must not contain narrative `info` fields.
- **META-006:** Narrative and descriptive text must come only from `README.md` files in creator and project folders.
- **META-007:** Creator type-specific metadata must use `person` and `collaboration` branches. The inactive branch must be pruned when the creator type changes.
- **META-008:** Project domain metadata must be stored as generic `facets` in the project-level `cr4te.json`. Empty stale facets must be pruned, but stale facets with values must be retained as a domain-change failsafe.
- **META-009:** Date metadata must accept only valid calendar dates in `yyyy`, `yyyy-mm`, or `yyyy-mm-dd` form. Display must preserve the stored precision: year-only dates display as a year, month dates display as month and year, and full dates display with day, month, and year.

## Metadata Lifecycle And Configuration

- **LIFE-001:** `build` must be the metadata lifecycle command. It creates and reconciles editable metadata before rendering. `init-metadata` and `sync-metadata` must not be available.
- **LIFE-002:** Editable project facet scaffolding must be derived from the resolved `site_rendering.project_metadata.fields` configuration.
- **LIFE-003:** Domain presets must be only one way to produce resolved project facet configuration. A saved configuration file must be self-contained for later builds.
- **LIFE-004:** A CLI domain override must replace the active project facet field set instead of merging with the configured facet fields.

## Build Modes And Issue Reporting

- **BUILD-001:** Best-effort builds must skip invalid creators or invalid projects and report structured issues. Invalid project metadata must skip only that project, not the whole creator.
- **BUILD-002:** `--strict` must fail fast on errors.
- **BUILD-003:** Build issues must remain structured with scope, severity, code, path, and message.
- **BUILD-004:** Render-time asset failures must be represented as structured build issues and included in the final build summary instead of existing only as logs.
- **BUILD-005:** Repeated failures with the same scope, issue code, and path must be reported only once per build.
- **BUILD-006:** Every successful build must report final phase timings for theme discovery, output preparation, metadata reconciliation, library indexing, HTML rendering, and their total.
- **BUILD-007:** Every successful build must report constant-memory asset statistics that distinguish created symbolic links, created hard links, reused media links, generated and reused source thumbnails, default-thumbnail uses, and source-hash checks.

## Asset Staging And Failure Handling

- **ASSET-001:** Best-effort builds must continue after recoverable asset failures without generating known-broken references.
- **ASSET-002:** Failed portrait and cover thumbnails must use generated defaults.
- **ASSET-003:** Missing media and unreadable text or gallery images must be omitted from generated pages.
- **ASSET-004:** Unavailable optional media inspection data, such as audio duration, must use a safe fallback and produce a warning.
- **ASSET-005:** `--strict` must abort immediately on asset errors but not on asset warnings.
- **ASSET-006:** Media staging during `build` must not silently copy source media when links cannot be created. It may use symbolic links or hard links.
- **ASSET-007:** If neither symbolic nor hard links can be created, media staging must abort with a structured asset error and a clear message regardless of strict mode.

## Thumbnail Freshness

- **THUMB-001:** A source-derived thumbnail must be regenerated when its source image has a newer modified time than the existing thumbnail.
- **THUMB-002:** When only the source image's parent folder is newer, thumbnail freshness must be determined by comparing the source image's SHA-256 hash with a sidecar containing only the hash.
- **THUMB-003:** A thumbnail must be regenerated when the required hash sidecar is missing or differs, and reused when the hash matches.
- **THUMB-004:** Source hashes must be calculated only for the parent-folder freshness check. Other thumbnail regeneration paths must remove any stale hash sidecar.

## Generated Site Behavior

- **SITE-001:** Generated detail pages must allow only one audio or video element to play at a time.
- **SITE-002:** Starting playback must pause the previously active media element without resetting its source, selection, or playback position, regardless of whether playback started through cr4te controls, native browser behavior, or JavaScript.
- **SITE-003:** Generated pages must remain usable when browser storage is unavailable. Features that persist preferences must continue operating for the current page without producing unhandled errors.
- **SITE-004:** Generated media markup must not misidentify the format of supported media files.
- **SITE-005:** Generated gallery images must have meaningful alternative text derived from available image metadata.
- **SITE-006:** Generated-site controls must use keyboard-operable native controls where the interaction supports them and must have accessible names.
- **SITE-007:** Keyboard-focused generated-site controls must display a visible focus indicator that does not alter layout and is not shown solely because of mouse interaction.
- **SITE-008:** Generated-site toggle controls must expose their current state to assistive technologies.
- **SITE-009:** The theme menu must support conventional keyboard navigation, selection, and Escape-to-close behavior.
- **SITE-010:** Generated media players must provide conventional, control-scoped keyboard operation without overriding the native keyboard behavior of their buttons and sliders.

## Themes

- **THEME-001:** Built-in and user-provided themes must use the same discovery, registry, rendering, and output-copy path.
- **THEME-002:** Custom themes must be loaded only from an explicitly supplied `build --themes-dir` directory.
- **THEME-003:** Custom themes must be self-contained CSS files named with lowercase portable slugs and must define the matching `.theme-<slug>` selector.
- **THEME-004:** Custom themes must not override built-in theme IDs.
- **THEME-005:** A supplied themes path that is missing or is not a directory must abort before build side effects.
- **THEME-006:** Frozen Aurora must remain the explicit default theme.
- **THEME-007:** Theme initialization failures must never leave generated pages hidden.

## Architecture And Scalability Invariants

- **ARCH-001:** The CLI build path must preserve a streaming, two-pass design suitable for large libraries.
- **ARCH-002:** The build path must not retain full media-group path lists for the whole library and must keep only lightweight index and overview data globally.
- **ARCH-003:** Any cache for image dimensions, thumbnails, audio durations, or similarly expensive data must be bounded or disk-backed. Whole-library media data must not be retained in an unbounded in-memory cache.
