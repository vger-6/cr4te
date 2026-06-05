# TODO

This file tracks product ideas. Durable requirements live in [REQUIREMENTS.md](REQUIREMENTS.md); future refactoring guidance lives in [REFACTORING_GUIDELINES.md](REFACTORING_GUIDELINES.md).

## Review Backlog

These items come from the full-codebase review of the Python build pipeline, generated HTML, copied assets, JavaScript, and CSS contracts. They are TODOs, not durable requirements.

### High Priority

- [ ] Validate and refresh existing staged media links when they are broken or stale, especially hard links whose source file has been replaced.
- [ ] Surface render and asset failures as structured build issues. Thumbnail failures, missing staged media, and similar rendering problems should appear in the build summary rather than only in logs.

### Medium Priority

- [ ] Compute detail-page `path_to_root` from the actual output path instead of relying on the hard-coded `FILE_TREE_DEPTH + 1` coupling.
- [ ] Detect or prevent duplicate project output paths when multiple project folders use the same rendered title.
- [ ] Avoid repeated full creator reloads while rendering collaboration/member links; use lightweight summaries where practical to preserve the streaming build shape.
- [ ] Unify build exception handling and reporting across the full build lifecycle.
  - [ ] Fold metadata reconciliation skips and warnings into the structured build summary where practical.
  - [ ] Make CLI abort/error paths return clear non-zero exit statuses for automation-friendly command behavior.

### Low Priority

- [ ] Add `--dry-run` flag to `build`.
- [ ] Add optional progress reporting for large folder trees.
