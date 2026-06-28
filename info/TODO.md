# TODO

This file tracks product ideas. Durable requirements live in [REQUIREMENTS.md](REQUIREMENTS.md); future refactoring guidance lives in [REFACTORING_GUIDELINES.md](REFACTORING_GUIDELINES.md).

## Review Backlog

These items come from the full-codebase review of the Python build pipeline, generated HTML, copied assets, JavaScript, and CSS contracts. They are TODOs, not durable requirements.

### Low Priority

- [ ] Consider an academic research domain preset.
  - Map creator folders to researchers or research groups and project folders to publications or studies.
  - Keep the existing person/collaboration creator model; research groups can use collaboration metadata.
  - Prefer documents first in media sections and use publication-appropriate project-card proportions.
  - Evaluate reuse of existing citation, editor, language, and collaboration-related metadata before adding new facets.
  - Decide whether journals, institutions, research fields, conferences, identifiers such as DOI, and co-authors belong in project facets.
  - Confirm whether `Publication` or the broader `Study` is the better default project label.
  - Add the preset only when its labels, facet set, media ordering, gallery defaults, tests, and wiki documentation form a coherent built-in domain.
- [ ] Add `--dry-run` flag to `build`.
- [ ] Add a `--prune-thumbnails` build option that removes orphaned cached thumbnails and freshness sidecars without regenerating valid thumbnails.
- [ ] Add optional progress reporting for large folder trees.
- [ ] Make scan exclusions relative to the configured library root.
  - A library below a dot-prefixed ancestor directory is currently treated as empty because exclusion checks inspect absolute path components.
  - Preserve hidden and configured-prefix exclusion inside the library while ignoring ancestors above the selected input root.
- [ ] Avoid repeated full creator reloads while rendering collaboration/member links; use lightweight summaries where practical to preserve the streaming build shape.
  - Keep lightweight summaries free of payloads unused by indexing and overview rendering, including creator README narrative content.
- [ ] Consider making the left panel on two-column detail pages collapsible.
  - Treat this as a content-first affordance: collapsing the overview/context panel should make more room for the right-column content.
  - Keep a visible full-height collapsed rail instead of hiding the left panel completely.
  - Show a rotated "Overview" label on the rail and pair it with a recognizable expand/collapse icon so the control is discoverable.
  - Reuse the existing theme-specific panel border/background language so the rail still feels like the collapsed left panel.
  - Decide whether the collapsed state should be per-page only, persisted across detail pages, or not persisted at all for the first version.
  - Make the control keyboard-accessible with clear labels, focus styling, and `aria-expanded` state.
  - Ensure the right panel expands cleanly and media/document sizing is recalculated where needed after toggling.
  - Avoid applying the rail behavior on narrow screens unless a separate mobile interaction is designed; the current stacked layout may be better there.
  - Add browser coverage for expanded, collapsed, keyboard, responsive, and iframe/document-sizing behavior if the feature becomes durable.
- [ ] Add a shuffle mode to the audio player.
  - Introduce a page-local shuffle toggle while preserving the currently playing track when the mode changes.
  - Play every track once in randomized order before starting a new shuffled queue, rather than choosing each next track independently and allowing immediate repeats.
  - Make Previous follow playback history and make Next advance through the shuffled queue.
  - Give the toggle an accessible name and state, keyboard support, and theme-consistent focus and active styling.
  - Before changing playback order, add behavioral browser coverage for the existing sequential Next, Previous, and ended-event auto-advance behavior; extend those tests for shuffled ordering, queue exhaustion, and history navigation.
