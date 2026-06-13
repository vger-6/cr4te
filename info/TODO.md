# TODO

This file tracks product ideas. Durable requirements live in [REQUIREMENTS.md](REQUIREMENTS.md); future refactoring guidance lives in [REFACTORING_GUIDELINES.md](REFACTORING_GUIDELINES.md).

## Review Backlog

These items come from the full-codebase review of the Python build pipeline, generated HTML, copied assets, JavaScript, and CSS contracts. They are TODOs, not durable requirements.

### Medium Priority

- [ ] Unify build exception handling and reporting across the full build lifecycle.
  - [ ] Fold metadata reconciliation skips and warnings into the structured build summary where practical.
  - [ ] Make CLI abort/error paths return clear non-zero exit statuses for automation-friendly command behavior.
- [ ] Strengthen the `width/height` aspect-ratio configuration contract.
  - Keep one external format: a string containing two positive integers in `width/height` order, such as `"3/2"`. Do not add colon, decimal, array, or object alternatives.
  - Continue normalizing accepted values to the canonical `"width/height"` string used by Python, generated HTML, JavaScript, and CSS.
  - Rename `GalleryLayoutRendering.validate_aspect_ratio_colon_format` to reflect validation and normalization of the slash-separated format, and remove its obsolete TODO comment.
  - Make invalid-value errors state the expected format and include an example, such as: `Aspect ratio must use two positive integers in width/height format, for example 3/2.`
  - Ensure Python config validation rejects missing separators, extra separators, non-integers, zero values, and negative values.
  - Decide whether to reject impractically extreme ratios or dimensions that could cause excessive generated-thumbnail sizes. Base any limit on a documented operational reason rather than an arbitrary aesthetic range.
  - Keep the JavaScript parser defensive for generated or manually modified HTML, and verify its fallback behavior remains consistent with the validated Python contract.
  - Add focused config-schema/parser tests covering valid landscape, portrait, square, whitespace-normalized, and high-precision ratios, plus all rejected forms.
  - Add or adjust browser coverage only if JavaScript parsing or fallback behavior changes.
  - Document explicitly that width comes first in the wiki configuration example.
  - Consider adding a durable requirement only if the supported format or any practical ratio limit becomes a committed product contract.

### Low Priority

- [ ] Review CSS design tokens to make recurring spacing, typography, icon, motion, and layout values more coherent without over-tokenizing component-specific details.
  - Introduce a small foundational scale for genuinely recurring values, such as `--space-xs: 0.25rem`, `--space-sm: 0.5rem`, `--space-md: 1rem`, and body/small-text sizes.
  - Add expressive component aliases where independent fine-tuning remains useful, such as `--meta-label-value-gap`, `--meta-entry-gap`, and `--data-label-size`, backed by the foundational scale.
  - Prioritize repeated spacing values, non-heading typography sizes, common icon dimensions, transition durations, and duplicated scrollbar dimensions.
  - Keep specialized values such as slider track/thumb dimensions, search-control padding, thumbnail dimensions, and unusual compact gaps component-specific unless multiple components genuinely share the same design role.
  - Organize or document token roles as foundational, layout, theme, and component aliases while keeping `tokens.css` as the single file unless its size or ownership becomes difficult to navigate.
  - Audit existing literals before adding tokens; introduce tokens only when they express a shared design decision or remove meaningful duplication.
  - Review `--layout-mobile-breakpoint`, which cannot normally be referenced from CSS media-query conditions and currently suggests central control while the actual `72rem` breakpoint remains hardcoded.
  - Add visual/browser regression coverage only for token changes that could alter generated-site layout or appearance.
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
