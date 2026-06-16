# Empty States Implementation Plan

This plan describes the intended implementation shape for contextual empty states in the generated site. It is a feature plan, not a durable requirement. Durable product behavior must be added to `REQUIREMENTS.md` when the implementation is accepted.

## Goal

Prevent major panels and page regions from appearing unintentionally blank when content is unavailable or a search returns no matches. Use one consistent visual empty-state component while giving each cause an accurate message and appropriate behavior.

## Scope Boundary

- Do enough work to make empty states a complete, tested, accessible, and documented generated-site feature.
- Do not render an empty-state panel for every absent optional section.
- Preserve the current panel sizes, spacing, colors, typography, and general page appearance unless a specific empty-state style is agreed before implementation.
- Reuse existing theme tokens wherever possible instead of introducing theme-specific empty-state styling.
- Keep the agreed minimal appearance unless a later UI/UX review explicitly changes it.
- Avoid unrelated template, context-model, pagination, search, CSS, or JavaScript refactors unless they directly block a correct implementation.
- Record newly discovered non-blocking issues in `TODO.md` instead of expanding the feature.

## Design Direction

- Introduce one reusable empty-state template macro or partial with consistent semantic markup and CSS classes.
- Use the shared component for both static build-time states and dynamic search-result states.
- Keep messages contextual: an empty library, missing optional content, and a search with no matches are different situations.
- Render empty states as a simple message block in the affected content area, not as fake creator/project cards.
- Show an empty state only when an otherwise-visible major panel or page region would be blank.
- Continue omitting optional sections such as tags, descriptions, individual media types, and project galleries when their absence does not leave a confusing blank region.
- Keep static empty states present in generated HTML without requiring JavaScript.
- Let `search_filter.js` control only the dynamic no-results state.
- Store user-facing messages in the existing site-label configuration structure rather than hard-coding English text throughout templates and JavaScript.
- Configure domain-aware messages as complete named-placeholder formats rather than sentence fragments that templates or JavaScript concatenate with entity labels.
- Keep messages without dynamic wording as ordinary complete labels.
- Prefer Python/page-context booleans for non-trivial content-presence decisions instead of duplicating deep content checks in Jinja templates.

## Proposed User Contract

- Creator and project overview pages with entries show their existing search bar and card gallery.
- A creator overview with no creators shows a static `No creators available` empty state and omits the unusable search bar.
- A project overview with no projects shows a static `No projects available` empty state and omits the unusable search bar.
- An overview search with no matching cards keeps the existing results panel visible and replaces the blank result area with `No results match your search`.
- Clearing or changing the search hides the no-results state as soon as matching cards are available again.
- A tags page with no tags shows `No tags available`.
- A creator detail page continues to omit an empty Projects panel and other absent optional sections.
- When a creator has no projects, collaboration projects, or creator-level media, the otherwise-empty right column shows one combined `No projects or media available` panel.
- When a project has no media, the otherwise-empty media column shows `No media available`.
- Empty-state wording follows configured entity labels where appropriate so domain presets can continue using terms such as artists, albums, books, or movies.
- Domain-aware defaults use complete formats such as `No {creators} available`, `No {projects} available`, and `No {projects} or media available`; the renderer supplies the configured entity labels through named placeholders.

## UI And Accessibility Decisions

- Empty states show one short message only, without a secondary explanation.
- The dynamic search empty state does not add a visible clear-search button; the existing clear icon remains the clearing control.
- Static overview empty states omit the search bar instead of showing it disabled.
- The empty-state component uses existing section padding, muted theme text, and normal body text.
- Empty states do not use illustrations, decorative icons, oversized typography, or fake overview cards.
- Default messages do not end with punctuation.

## Implementation Steps

1. Agree on the UI and wording decisions listed above.
2. Add durable generated-site empty-state behavior to `REQUIREMENTS.md`.
3. Add focused failing template and browser tests for the agreed static and dynamic states before production changes.
4. Extend the site-label schema and defaults with the required empty-state messages. Use validated named-placeholder formats for domain-aware phrases and ordinary complete labels for messages without dynamic wording.
5. Add a reusable empty-state macro or partial with semantic markup suitable for static and dynamic use.
6. Add minimal shared empty-state CSS using existing theme tokens and panel spacing.
7. Update creator and project overview templates:
   - Omit the search bar when the corresponding complete collection is empty.
   - Render a static collection-empty state when no overview entries exist.
   - Render a hidden dynamic no-search-results state when entries exist.
8. Update `search_filter.js` to toggle the dynamic state after filtering and pagination.
9. Ensure the dynamic state uses `aria-live="polite"` or an equivalent status mechanism without repeatedly announcing unchanged messages.
10. Update the tags template to render its static empty state when no tag groups exist.
11. Add or expose clear page-context content-presence values for creator and project detail-page right columns if existing data does not make those checks simple and reliable.
12. Update creator and project detail templates to render one region-level empty state only when the complete right-column content region is empty.
13. Verify empty states remain correct with JavaScript disabled, except for the inherently dynamic search-result state.
14. Update wiki documentation only where the behavior is useful to users; avoid documenting obvious presentation details.
15. Run the established validation set from `REFACTORING_GUIDELINES.md` as far as the local environment allows.

## Tests Required

- Template/rendering test proving an empty creator overview renders its static empty state and omits the search bar.
- Template/rendering test proving an empty project overview renders its static empty state and omits the search bar.
- Template/rendering test proving populated overviews render the hidden dynamic no-results state without showing the static collection-empty state.
- Browser test proving a search with no matches shows the dynamic empty state.
- Browser test proving changing or clearing the search restores matching cards and hides the dynamic empty state.
- Browser accessibility check proving the dynamic state exposes an appropriate status/live-region semantic.
- Template/rendering test proving an empty tags page renders `No tags available`.
- Template/rendering test proving a creator with no projects, collaboration projects, or creator media renders one combined right-column empty state.
- Template/rendering test proving a creator with any right-column content does not render the combined empty state.
- Template/rendering test proving a project with no media renders one media-region empty state.
- Template/rendering test proving a project with media does not render that empty state.
- Config-schema/default tests for all newly added site-label fields.
- Config tests proving domain-aware empty-state formats accept their documented named placeholders, support different word order, and reject positional or unknown placeholders.
- Rendering tests proving domain-aware empty-state messages use configured entity labels without template- or JavaScript-level sentence construction.
- Regression tests proving absent optional sections remain omitted instead of each receiving an empty-state panel.
- Browser or rendered-markup checks proving empty states do not alter existing populated-page layout.

## Non-Goals

- Do not show separate empty panels for every absent media type, tag section, description, collaboration, or project list.
- Do not treat search no-results and genuinely absent content as the same semantic state.
- Do not add editing, upload, tagging, or content-creation actions to the generated static site.
- Do not redesign existing panels, overview cards, search controls, page columns, typography, or themes as part of this feature.
- Do not add illustrations, decorative icons, animations, or new theme color systems unless separately discussed and approved.
- Do not make static empty states depend on JavaScript.
- Do not add compatibility handling for generated sites or configuration files from earlier development versions.
- Do not expose partial empty-state sentence fragments or assemble human-readable empty-state phrases from independently configured labels in templates or JavaScript.
