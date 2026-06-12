# Portrait Refactoring Plan

This plan describes the intended refactoring of portrait discovery, rendering, and creator overview cards. Durable product behavior belongs in `REQUIREMENTS.md`.

## Goal

Separate portrait discovery from portrait visibility so each concern lives in its natural configuration section. Make every supported combination coherent across scanning, thumbnail generation, page contexts, and rendering.

## Scope Boundary

- Store portrait selection policy under `media_rules`.
- Store portrait presentation policy under `site_rendering`.
- Keep library discovery, classification, and indexing independent of portrait visibility.
- Replace the previous combined portrait control directly, following the project compatibility guidelines.
- Preserve the current portrait image-card appearance when portraits are visible on overview pages.
- Use deliberate text cards when overview portraits are not visible.
- Keep cover discovery behavior fixed and independently tested.
- Avoid unrelated card, scanner, and configuration refactors.

## Configuration Contract

```json
{
  "media_rules": {
    "portrait_discovery": "named",
    "portrait_basename": "portrait"
  },
  "site_rendering": {
    "portraits": {
      "visibility": "all"
    }
  }
}
```

CLI overrides:

```text
--portrait-discovery named|auto
--portrait-visibility disabled|details|all
```

An omitted CLI override preserves the corresponding resolved configuration value.

## Discovery Semantics

### `named`

1. Select the lexicographically first matching image directly inside the creator folder.
2. Otherwise select the lexicographically first matching image below the creator folder.
3. Otherwise leave the discovered portrait empty.

### `auto`

1. Apply the named-match priorities.
2. Otherwise select the lexicographically first portrait-oriented image.
3. Otherwise leave the discovered portrait empty.

Portrait discovery never selects an arbitrary landscape image.
Portrait discovery and role assignment run for every visibility setting. Portrait-role images do not additionally appear as gallery media.

## Visibility Semantics

### `disabled`

- Discover and assign portraits according to `media_rules.portrait_discovery`.
- Skip portrait-thumbnail work.
- Omit portrait markup on creator and project detail pages.
- Render creator overview entries as text cards.

### `details`

- Discover portraits according to `media_rules.portrait_discovery`.
- Render discovered portraits on creator and project detail pages.
- Omit portrait markup when discovery finds no portrait.
- Render creator overview entries as text cards.

### `all`

- Discover portraits according to `media_rules.portrait_discovery`.
- Render portraits on detail pages and portrait image cards on the creator overview.
- Use generated defaults where no portrait is discovered.
- Preserve overview icon badges and image-gallery behavior.

A discovered portrait that cannot be read or thumbnailed continues through the existing asset-issue and generated-default behavior.

## Cover Selection Contract

Keep one fixed cover policy:

1. Select the lexicographically first configured-basename match directly inside the project folder.
2. Otherwise select the lexicographically first matching image below the project folder.
3. Otherwise select the lexicographically first landscape-oriented image.
4. Otherwise select the lexicographically first available image.
5. Otherwise use the generated default cover.

Portrait and cover selection may share candidate-selection code, but their fallback policies remain independently specified and tested.

## Creator Overview Cards

### Shared Behavior

- Preserve card border, background, hover styling, link behavior, whole-card keyboard focus, search, and pagination.
- Preserve configured project and media labels.

### Image Cards

- Used only with `portrait-visibility all`.
- Preserve the current portrait layout and overlay icon badges.

### Text Cards

- Used with `portrait-visibility disabled` and `details`.
- Use a dedicated responsive grid without image-gallery layout builders.
- Render the creator name and only non-zero project and media counts.
- Use configured singular and plural labels.
- Render only the creator name when every count is zero.
- Render the project count on a separate line above media counts.
- Use dedicated sentence-style project count labels rather than heading/navigation entity labels.
- Use ` | ` between media counts and an existing muted theme color for both count lines.

## Implementation Steps

1. Record the accepted discovery and visibility behavior in `REQUIREMENTS.md`.
2. Add focused tests for configuration, CLI overrides, scanning, thumbnail work, contexts, and templates.
3. Add separate discovery and visibility enums in their owned configuration sections.
4. Keep scanning and library-index APIs independent of portrait visibility.
5. Keep named and automatic discovery policy inside media scanning.
6. Make detail contexts distinguish a missing portrait from a generated default.
7. Render overview image cards only for all visibility and text cards for disabled/details.
8. Prepare only the default portrait assets required by the selected visibility.
9. Update README and wiki documentation.
10. Run the established refactoring validation set and browser checks.

## Tests Required

- Configuration and CLI tests for independent discovery and visibility overrides.
- Regression tests proving omitted overrides preserve resolved values.
- Scanner tests for named and auto discovery behavior independent of visibility.
- Tests proving portrait-role images do not additionally appear in galleries.
- Context and asset tests proving disabled performs no portrait-thumbnail work.
- Context tests proving details renders discovered portraits and omits absent ones.
- Tests proving all visibility uses portrait defaults and image overview cards.
- Template tests for image cards, text cards, count summaries, and omitted detail markup.
- Browser tests for responsive text cards, search, pagination, focus, and unchanged all-visibility cards.
- Documentation and dead-code scans for obsolete combined-control references.
