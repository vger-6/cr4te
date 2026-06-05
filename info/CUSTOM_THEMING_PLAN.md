# Custom Theming Implementation Plan

This plan describes the intended implementation shape for user-provided themes. It is a feature plan, not a durable requirement. Durable product behavior must be added to `REQUIREMENTS.md` when the implementation is accepted.

## Goal

Allow users to add custom themes by placing CSS theme files in a dedicated theme folder. The filename stem becomes the theme name, and the theme appears automatically in the generated site's theme dropdown. Existing built-in themes should use the same discovery/registry path as custom themes.

## Scope Boundary

- Do enough work to make custom themes a complete, tested, documented feature.
- Do not do more work than necessary, but do not do less either.
- Do not code for the sake of coding.
- Stop when the new feature is implemented, tested, documented, and integrated into the existing build/render flow.
- Avoid unrelated cleanup unless the implementation exposes code that directly blocks the feature, creates a concrete bug, or would introduce a new anti-pattern if left untouched.
- Record newly discovered non-blocking issues in `TODO.md` instead of expanding the feature refactor.

## Design Direction

- Introduce one Python-side source of truth for available themes, likely a small `ThemeDefinition` plus a theme registry/discovery helper.
- Move built-in themes into the same system as custom themes, rather than keeping built-ins hard-coded separately.
- Render the theme dropdown from discovered theme definitions.
- Keep JavaScript generic: it should apply one of the rendered theme classes, not know the built-in theme list.
- Keep CSS authoring simple and valid enough for editor support such as VS Code IntelliSense.
- Accept a dedicated user theme folder through an explicit build option so themes remain separate from creator/project content.
- Keep output preparation and asset copying concerns in the existing output/static-asset boundary.

## Proposed User Contract

- Users place theme CSS files in a dedicated folder and pass it with `build --themes-dir`.
- The filename without extension is the display name unless a later explicit metadata mechanism is added.
- The CSS file must define the expected theme class derived from the filename, for example:

```css
.theme-my-theme {
  --theme-page-bg: #101014;
  --theme-text: #f2f2f0;
  --theme-link: #9bc7ff;
}
```

- Invalid, duplicate, or unusable theme files should produce clear structured build issues.
- The default theme should remain stable unless the requirements are deliberately changed.

## Implementation Steps

1. Define the theme data model and discovery rules.
2. Move the existing built-in themes into discoverable built-in theme files.
3. Add custom theme discovery from the explicitly supplied user theme folder.
4. Generate or copy theme CSS into the output site through the static asset pipeline.
5. Render the theme dropdown from the theme registry.
6. Update `theme_selector.js` so fallback/default behavior comes from rendered data or the first/default registry entry.
7. Ensure restricted `localStorage` access cannot break page initialization.
8. Remove the blank-page failure mode if it is still tied to theme initialization.
9. Add focused unit tests for theme discovery, naming, duplicate handling, dropdown context, and output CSS behavior.
10. Add or adjust browser tests to verify a generated custom theme appears in the dropdown and can be applied.
11. Update `REQUIREMENTS.md` with the durable custom-theme behavior.
12. Update `README.md` with user-facing instructions and an example theme file.
13. Run the established validation set from `REFACTORING_GUIDELINES.md` as far as the local environment allows.

## Tests Required

- Unit tests for built-in theme registry loading.
- Unit tests for custom theme discovery.
- Unit tests for filename-to-theme-class/name behavior.
- Unit tests for duplicate or invalid theme handling.
- Unit tests proving custom theme discovery remains separate from creator/project indexing.
- Template/rendering tests proving dropdown entries are generated from registry data.
- Browser regression test proving a custom theme appears and can be selected on generated pages.

## Non-Goals

- Do not build a full CSS parser unless a simple, concrete validation rule is insufficient.
- Do not introduce dynamic runtime theme loading unless static generated CSS proves inadequate.
- Do not store theme definitions in creator/project `cr4te.json` metadata.
- Do not add compatibility shims for old theme mechanisms after the registry replaces them.
- Do not redesign unrelated CSS, layouts, JavaScript modules, metadata loading, or asset caching as part of this feature.
