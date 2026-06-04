# cr4te Requirements

These are durable product/design requirements for cr4te. They must hold during and after the refactoring unless we explicitly revise this file.

- No backwards compatibility or legacy metadata migration. The current schema is the only supported schema; obsolete or extra JSON fields should fail validation instead of being silently migrated.
- `build` is the metadata lifecycle command. It creates and reconciles editable metadata before rendering. `init-metadata` and `sync-metadata` must not return.
- Metadata lives beside the folder it describes. Creator metadata lives in each creator folder's `cr4te.json`; project metadata lives in each project folder's `cr4te.json`. Creator metadata must not nest project metadata under `projects`.
- When `build` encounters matching nested project metadata in a creator file, it should seed the corresponding project-level `cr4te.json` before pruning the nested creator entry, so existing filled metadata is not discarded during the layout change.
- `cr4te.json` contains editable structured metadata only. It must not contain generated scan output such as `media_groups`, and it must not contain narrative `info` fields.
- Narrative/descriptive text comes only from `README.md` files in creator/project folders.
- Creator type-specific metadata uses `person` and `collaboration` branches. The inactive branch is pruned when the type changes.
- Project domain metadata is stored as generic `facets` in the project-level `cr4te.json`. Empty stale facets are pruned, but stale facets with values are kept as a domain-change failsafe.
- Date metadata accepts only valid calendar dates in `yyyy`, `yyyy-mm`, or `yyyy-mm-dd` form. Display must preserve the stored precision: year-only dates display as a year, month dates display as month and year, and full dates display with day, month, and year.
- Editable project facet scaffolding is derived from the resolved configuration, specifically `site_rendering.project_metadata.fields`. Domain presets are only one way to produce that configuration; a saved config file must be self-contained for later builds. When a CLI domain override is applied, that domain replaces the active project facet field set instead of merging with existing configured facet fields.
- Best-effort builds skip invalid creators or invalid projects and report structured issues. Invalid project metadata skips only that project; it does not skip the whole creator. `--strict` fails fast on errors.
- Build issues remain structured with scope, severity, code, path, and message. Logging/reporting should happen at command/summary boundaries, not deep inside scan helpers.
- The CLI build path must preserve the streaming/two-pass concept for large libraries: avoid retaining full media group path lists for the whole library, keep only lightweight index/overview data globally, and load/render one creator at a time where practical.
- Any future cache for image dimensions, thumbnails, audio durations, or similar expensive data must be bounded or disk-backed. Do not introduce an unbounded in-memory cache for whole-library media data.
- Jinja templates may receive dict-like render contexts for now, but Python-side assembly should continue moving toward typed render/view models where that improves clarity and testability.
- Refactors should remove dead code, obsolete mappings, and unused compatibility paths as soon as their replacement is in place. Do not keep legacy shims or old data-shape handlers for hypothetical future migration.
