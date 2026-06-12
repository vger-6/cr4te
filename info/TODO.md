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
