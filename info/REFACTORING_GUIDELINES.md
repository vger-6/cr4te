# cr4te Refactoring Guidelines

These guidelines are for future refactors after the metadata/library refactor. Durable product requirements live in [REQUIREMENTS.md](REQUIREMENTS.md); use those as hard constraints.

## When To Refactor

- Refactor only when it removes real complexity, deletes duplication or dead code, improves a meaningful boundary, protects a durable requirement, or makes behavior easier to test or reason about.
- Stop when the stated goal is achieved. Do not continue structural cleanup when the remaining changes are only aesthetic.
- If a new issue clearly needs attention, record the reason and keep the change focused.
- Prefer concrete bug fixes, product features, or requirement updates over continued structural reshuffling once the architecture goals are met.

## Project Maturity And Compatibility

- cr4te is currently version `0.0.1`. Do not implement backwards-compatibility shims, legacy metadata or configuration handlers, schema migrations, or other treatment of obsolete data shapes.
- Change current schemas, configuration, and data shapes directly. Update bundled examples, tests, and documentation in the same change.
- Keep validation strict: obsolete and extra JSON fields fail validation instead of being silently accepted, migrated, or pruned as legacy data.
- Do not add conversion or recovery paths to preserve legacy user data when current data shapes change.
- Remove obsolete helpers, mappings, and data-shape handlers as soon as their replacements are in place.
- Reconsider compatibility behavior only when the project adopts an explicit versioning and compatibility policy.

## Design Boundaries

- Preserve the streaming/two-pass build shape for large libraries: keep only lightweight overview/index data globally and load/render full creator data one creator at a time where practical.
- Keep caches bounded or disk-backed. Do not introduce unbounded whole-library media caches.
- Keep output preparation separate from render assets. Output folders and static files belong in `output_preparation.py`; thumbnail generation and media staging belong in `render_assets.py`.
- Keep enum modules value-focused. Classification, inference, routing, and policy helpers belong in dedicated concept modules.
- Keep the current top-level module layout unless a package move solves a real navigation, ownership, or testability problem.
- Keep label roles separate. Heading and navigation entity labels live under `site_labels.entity`; sentence-style project count labels live under `site_labels.counts`; core metadata labels live under `site_labels.metadata`; facet defaults live in `taxonomy.py`; user facet-label overrides live under `site_labels.project_facets`.

## Data Shapes

- Prefer typed Python-side models where they reduce ambiguity or make behavior easier to test. Raw dicts are acceptable at external JSON boundaries and Jinja-facing edges when that is the simpler interface.
- Avoid adding mappings in multiple places. If adding a field or facet requires touching many unrelated modules, look for the missing registry or typed boundary.
- Remove obsolete imports as soon as their replacement is in place.

## Errors And Logging

- Keep build issues structured with scope, severity, code, path, and message.
- Log/report at command and summary boundaries. Avoid deep scan/helper code that logs instead of returning structured issues, unless the event is genuinely local and recoverable.
- Best-effort behavior should be explicit and tested; strict-mode failures should remain easy to trace.

## Tests And Validation

- Add or adjust focused unit tests with each design-moving refactor.
- Run dead-code and accidental compatibility-path scans after meaningful refactors.
- Before considering a refactor complete, run the established validation set: linter, unit tests, pyflakes, vulture, diff whitespace check, and the example build.
- Update docs and the plan/audit files when a refactor changes a durable decision or user-facing config shape.
