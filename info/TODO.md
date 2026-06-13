# TODO

This file tracks product ideas. Durable requirements live in [REQUIREMENTS.md](REQUIREMENTS.md); future refactoring guidance lives in [REFACTORING_GUIDELINES.md](REFACTORING_GUIDELINES.md).

## Review Backlog

These items come from the full-codebase review of the Python build pipeline, generated HTML, copied assets, JavaScript, and CSS contracts. They are TODOs, not durable requirements.

### Medium Priority

- [ ] Unify build exception handling and reporting across the full build lifecycle.
  - [ ] Fold metadata reconciliation skips and warnings into the structured build summary where practical.
  - [ ] Make CLI abort/error paths return clear non-zero exit statuses for automation-friendly command behavior.

### Low Priority

- [ ] Review generated human-readable phrases and replace fragment concatenation with complete named-placeholder label formats where it improves domain wording or localization.
  - Replace the currently unused `creator_collabs_title_prefix` with a complete collaboration-title format and use it instead of the hardcoded `{{ projects }} with {{ collaborator }}` template phrase. Support domain presets such as `{projects} with {collaborator}`, `Codirected with {collaborator}`, and `Scenes with {collaborator}`.
  - Consider deriving the search placeholder from a complete format such as `Search {creators}, {projects}, {tags}...` while preserving the option for domains to provide different complete wording.
  - Consider configurable complete formats for accessible image descriptions such as `Portrait of {creator}`, `Thumbnail for {project}`, and `Preview of {project}` if broader localization becomes a goal.
  - Revisit count summaries and badge descriptions only if broader localization requires word orders that cannot be expressed cleanly as `count` plus singular/plural labels.
  - Keep standalone nouns and control names as ordinary labels; use formats only when multiple dynamic or configurable values form one human-readable phrase.
- [ ] Consider an academic research domain preset.
  - Map creator folders to researchers or research groups and project folders to publications or studies.
  - Keep the existing person/collaboration creator model; research groups can use collaboration metadata.
  - Prefer documents first in media sections and use publication-appropriate project-card proportions.
  - Evaluate reuse of existing citation, editor, language, and collaboration-related metadata before adding new facets.
  - Decide whether journals, institutions, research fields, conferences, identifiers such as DOI, and co-authors belong in project facets.
  - Confirm whether `Publication` or the broader `Study` is the better default project label.
  - Add the preset only when its labels, facet set, media ordering, gallery defaults, tests, and wiki documentation form a coherent built-in domain.
- [ ] Add `--dry-run` flag to `build`.
- [ ] Add a `--prune-thumbnails` build option that removes orphaned cached thumbnails and hash sidecars without regenerating valid thumbnails.
- [ ] Add optional progress reporting for large folder trees.
- [ ] Avoid repeated full creator reloads while rendering collaboration/member links; use lightweight summaries where practical to preserve the streaming build shape.
