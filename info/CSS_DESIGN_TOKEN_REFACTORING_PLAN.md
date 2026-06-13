# CSS Design Token Refactoring Plan

This plan describes the intended cleanup of recurring CSS values and generated-site motion. It is primarily a refactoring plan. Durable generated-site behavior belongs in `REQUIREMENTS.md` only when a user-facing behavior becomes a committed product contract.

## Goal

Make recurring spacing, typography, icon, motion, and scrollbar decisions coherent and easier to maintain without replacing clear component-local values with unnecessary indirection. Preserve the current visual character while improving interaction feedback where restrained transitions provide a real UX benefit.

## Accepted Direction

- Keep the existing themes, layout proportions, colors, element sizes, and overall amount of motion.
- Treat `0.2s` as the normal duration for direct interaction feedback such as hover color changes.
- Treat `0.3s` as the normal duration for visibility changes such as controls fading in or out.
- Add transitions only to existing state changes where interpolation improves feedback without delaying expected behavior.
- Keep menus, lightboxes, captions, theme switching, focus indicators, gallery reflow, search-result changes, and slider movement immediate.
- Use existing theme hover colors for pagination-button feedback.
- Respect reduced-motion preferences for CSS transitions and pagination auto-scroll.
- Introduce tokens only when they express a shared design decision, remove meaningful duplication, or provide a useful component-level tuning point.
- Prefer refactorings that simplify selectors, declarations, and JavaScript ownership in addition to making values consistent.

## Scope Boundary

- Keep `tokens.css` as the single shared token file.
- Introduce a small foundational spacing, typography, icon, motion, and scrollbar vocabulary.
- Add expressive component aliases only where components should remain independently tunable, including metadata spacing and data-label typography.
- Replace repeated literals only when they clearly represent the same design role.
- Consolidate duplicated CSS where the resulting selector remains readable.
- Remove dead, ineffective, obsolete, and misleading declarations encountered within the touched CSS.
- Keep all built-in themes visually equivalent except for approved interaction transitions.
- Include the adjacent duplicated JavaScript aspect-ratio parser cleanup because it removes divergent behavior and simplifies gallery ownership.
- Avoid unrelated template, layout, theme-color, component-redesign, and JavaScript refactors.

## Proposed Token Structure

Organize `tokens.css` by role while keeping it in one file:

### Foundational Tokens

- A deliberately small spacing scale for genuinely recurring values:
  - `--space-xs: 0.25rem`
  - `--space-sm: 0.5rem`
  - `--space-md: 1rem`
- Shared non-heading typography sizes only where multiple components genuinely use the same role.
- Shared icon sizes for the repeated regular and compact icon dimensions.
- Motion tokens:
  - `--motion-interaction: 0.2s ease`
  - `--motion-visibility: 0.3s ease`
- Shared WebKit scrollbar dimensions for the currently duplicated width, radius, and transparent border.

### Layout And Component Aliases

- Preserve existing expressive layout and theme tokens.
- Back useful component aliases with foundational tokens where independent tuning remains valuable, including:
  - `--meta-label-value-gap`
  - `--meta-entry-gap`
  - `--data-label-size`
- Keep specialized values such as slider track/thumb dimensions, search-control padding, thumbnail dimensions, unusual compact gaps, and one-off widths component-local unless the audit proves a shared role.

### Token Removal

- Remove `--layout-mobile-breakpoint`. Ordinary CSS media-query conditions cannot use it, and retaining it implies central control that does not exist.
- Remove tokens only when they are unused or no longer represent a meaningful public theme customization point.

## Motion Review

### Preserve And Normalize

- Image-card background and border feedback.
- Audio-track hover, focus, and playing-state feedback.
- Audio-control visibility fades.
- Video-control visibility fades.
- Media-badge visibility fades.
- Tag hover feedback, restricted to the properties that actually change.

### Add

Use `--motion-interaction` for existing visual state changes on:

- Search clear-button color.
- Lightbox control colors.
- Media-control icon colors.
- Image-card captions and creator-card names.
- Pagination button hover and state colors, using existing theme colors.

These transitions must not change layout, introduce movement, or add new theme colors.

### Remove Or Simplify

- Remove ineffective pagination opacity transitions when no opacity state uses them.
- Remove the image-card transform transition while no transform state exists.
- Replace `transition: all` on tags with explicit changed properties.
- Consolidate the duplicated video-control opacity transition into one rule.
- Do not animate focus outlines; keyboard feedback must remain immediate.

### Reduced Motion

- Under `prefers-reduced-motion: reduce`, resolve shared motion durations to `0s`.
- Make pagination auto-scroll use immediate behavior when reduced motion is requested.
- Do not add broad global rules that disable unrelated browser or user-agent behavior.

## CSS Simplification

- Consolidate the repeated WebKit scrollbar rules shared by overview, desktop detail columns, and mobile detail content while preserving their current ownership and responsive behavior.
- Replace recurring literals with shared tokens only where the resulting declarations become clearer.
- Remove obsolete commented declarations in touched blocks when they no longer describe an active design option.
- Prefer explicit transition properties over `all`.
- Keep theme-specific files focused on visual theme values; foundational spacing and motion decisions belong in `tokens.css`.

## JavaScript Simplification

- Move defensive aspect-ratio parsing into one shared utility owned by `utils.js`.
- Reuse the shared parser from both `aspect_gallery_builder.js` and `pagination.js`.
- Preserve the canonical `1/1` fallback for missing or malformed generated or manually modified HTML values.
- Prevent malformed aspect ratios from producing non-finite calculations or non-terminating column calculation loops.
- Keep this cleanup behavior-neutral for valid generated HTML.

## UI And UX Review Gates

- Review representative creator overview, project overview, creator detail, project detail, tags, audio, video, and lightbox interactions after the first implementation pass.
- Fine-tune durations only if the shared `0.2s` interaction and `0.3s` visibility values feel noticeably too fast or slow in browser review.
- Stop and discuss any change that would alter sizes, spacing, layout, colors, or introduce motion beyond the accepted direction.

## Requirements Impact

- Add a durable generated-site requirement only for reduced-motion behavior if it is accepted as a committed accessibility contract.
- Keep exact token names, durations, easing functions, selector structure, and CSS organization out of `REQUIREMENTS.md`.
- Do not add requirements for behavior-neutral token substitutions or selector consolidation.

## Implementation Steps

1. Add focused contract tests for shared motion tokens, reduced-motion handling, removal of `transition: all`, and the shared JavaScript aspect-ratio parser.
2. Introduce the minimal foundational token groups and useful metadata/component aliases in `tokens.css`.
3. Replace only clearly shared spacing, typography, icon, motion, and scrollbar literals.
4. Normalize existing transitions, remove ineffective transitions, and consolidate duplicate transition declarations.
5. Add the approved direct-interaction transitions without changing colors or layout.
6. Add reduced-motion CSS handling and make pagination auto-scroll preference-aware.
7. Consolidate duplicated scrollbar CSS while preserving desktop and mobile behavior.
8. Remove the misleading mobile-breakpoint token and obsolete declarations in touched blocks.
9. Extract the JavaScript aspect-ratio parser into `utils.js` and reuse it from gallery and pagination code.
10. Build and inspect representative generated pages in every built-in theme at desktop and narrow viewport widths.
11. Run the established validation set from `REFACTORING_GUIDELINES.md`.
12. Remove or revise the completed design-token TODO entry and update wiki documentation only if a user-facing behavior needs explanation.

## Tests Required

- CSS contract test proving shared interaction and visibility motion tokens exist.
- CSS contract test proving component transitions use shared motion tokens rather than duplicated duration literals.
- CSS contract test proving no `transition: all` remains.
- CSS contract test proving reduced-motion preference disables shared transition durations.
- Browser test proving direct hover states interpolate only where intended without changing geometry.
- Browser test proving video and audio control visibility behavior remains functional.
- Browser test proving media badges remain visible on touch-style input and appear on hover/focus elsewhere.
- Browser test proving reduced-motion pagination changes pages without smooth auto-scroll.
- Browser regression checks for scrollbar styling and scrollability in overview, desktop detail, and narrow detail layouts.
- JavaScript contract or browser tests proving both aspect-gallery layout and pagination use the shared defensive parser and fall back safely for malformed ratios.
- Existing theme, focus, keyboard, gallery, pagination, audio, video, and lightbox regression suites.

## Non-Goals

- Do not redesign themes or alter their color palettes.
- Do not change current element sizes, responsive breakpoints, spacing relationships, or layout proportions merely to fit a token scale.
- Do not tokenize every numeric literal.
- Do not create a multi-file design-system package or utility-class framework.
- Do not animate layout, focus outlines, theme switching, menus, lightboxes, captions, gallery reflow, search filtering, or slider values.
- Do not add decorative movement, transforms, scaling, bouncing, or spring effects.
- Do not add compatibility handling for previous CSS, configuration, or generated HTML versions.
