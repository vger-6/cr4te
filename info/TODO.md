# TODO

This file tracks product ideas. Durable requirements live in [REQUIREMENTS.md](REQUIREMENTS.md); future refactoring guidance lives in [REFACTORING_GUIDELINES.md](REFACTORING_GUIDELINES.md).

## Test Commands

Rendered-site browser tests live in `tests_browser/`. They build the bundled example library, serve the generated HTML from a temporary local HTTP server, and exercise the JavaScript behavior on the fully rendered pages.

Install the optional browser test dependency once:

```powershell
python -m pip install -e ".[browser-test]"
python -m playwright install chromium
```

Run the browser regression tests:

```powershell
python -m unittest discover tests_browser
```

The regular Python test suite remains separate and fast:

```powershell
python -m unittest discover tests
```

## Review Backlog

These items come from the full-codebase review of the Python build pipeline, generated HTML, copied assets, JavaScript, and CSS contracts. They are TODOs, not durable requirements.

### High Priority

- [ ] Remove the blank-page failure mode caused by `body { display: none; }` depending on `theme_selector.js` to reveal the page. Prefer visible-by-default HTML or a tiny fail-safe theme bootstrap that always reveals the body.
- [ ] Make theme storage access resilient. Wrap `localStorage` reads/writes in `theme_selector.js` with fallbacks so restricted browser contexts cannot break page initialization.
- [ ] Define and implement explicit configuration precedence. Prefer defaults -> domain preset -> user config -> direct CLI flags, so `--domain` does not silently override values from `--config`.
- [ ] Prevent repeated pagination remounts from accumulating resize listeners during search. Treat pagination as a per-gallery instance that can update its items or clean up old listeners.
- [ ] Make generated/staged assets cache-aware. Refresh stale staged media and thumbnails when the source file changes, instead of reusing an existing target path unconditionally.
- [ ] Surface render and asset failures as structured build issues. Thumbnail failures, missing staged media, and similar rendering problems should appear in the build summary rather than only in logs.
- [ ] Reconsider metadata reconciliation as a default side effect of `build`. Either split it into an explicit command or add an opt-out/opt-in flag so builds do not unexpectedly modify input data.

### Medium Priority

- [ ] Compute detail-page `path_to_root` from the actual output path instead of relying on the hard-coded `FILE_TREE_DEPTH + 1` coupling.
- [ ] Detect or prevent duplicate project output paths when multiple project folders use the same rendered title.
- [ ] Avoid repeated full creator reloads while rendering collaboration/member links; use lightweight summaries where practical to preserve the streaming build shape.
- [ ] Unify build exception handling and reporting across the full build lifecycle.
  - [ ] Fold metadata reconciliation skips and warnings into the structured build summary where practical.
  - [ ] Make CLI abort/error paths return clear non-zero exit statuses for automation-friendly command behavior.

### Low Priority

- [ ] Replace the mojibake theme dropdown caret with plain ASCII text, CSS, or a correctly encoded character.
- [ ] Add `--dry-run` flag to `build`.
- [ ] Add optional progress reporting for large folder trees.

## Existing Functionality Ideas

This section is intentionally left for future product ideas that are not review findings.
