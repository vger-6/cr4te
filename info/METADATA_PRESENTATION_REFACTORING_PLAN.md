# Metadata Presentation Refactoring Plan

This plan describes the intended refactoring of metadata presentation on generated creator and project detail pages. Durable generated-site behavior belongs in `REQUIREMENTS.md`.

## Goal

Replace colon-separated metadata rows with one consistent stacked label-and-value component that improves visual hierarchy and readability across every relevant creator and project information block.

## Accepted UX Direction

- Render each metadata entry as a label above its value.
- Remove the colon after metadata labels.
- Render labels semibold, slightly smaller than values, and in a dedicated theme color that is visually distinct from links.
- Preserve the current value font size, colors, links, separators, and wrapping behavior.
- Use a small gap between a label and its value and a clearly larger gap between consecutive entries.
- Apply the same metadata presentation wherever creator or project metadata appears, including creator, collaboration, participant, and member information shown within detail pages.
- Present birth, death, and founding as semantic event entries, using the configurable metadata-label date-and-place format when both values exist.
- Present tag-category labels with the same shared visual label style and without trailing colons while preserving tag chips as a separate UI concept.
- Treat the initial sizing and spacing as a starting point that can be fine-tuned after browser review.

Initial CSS direction:

```css
.data-label {
  color: var(--theme-data-label-text);
  font-size: 0.875rem;
  font-weight: 600;
}
```

Start with approximately `0.25rem` between a label and its value and `1rem` between metadata entries. Adjust these values only after reviewing representative generated pages.

## Scope Boundary

- Refactor the shared metadata template markup and CSS rather than styling individual page sections independently.
- Use the shared presentation for project overview metadata, creator profile metadata, and creator, collaboration, participant, and member information embedded in detail pages.
- Preserve the underlying metadata model while configuring birth, death, and founding as semantic visible fields. Compose their related date/place values only at the rendering boundary.
- Preserve links and the existing comma, line-break, and other configured separators inside metadata values.
- Add a dedicated shared data-label text token that defaults to the existing muted text color and can be overridden independently by themes.
- Reuse the metadata-label visual style for tag-category labels and remove their separate color path.
- Preserve the current responsive detail-page structure and image sizing.
- Avoid unrelated creator/project context, metadata-generation, theme, and page-layout refactors.

## Semantic Markup

- Represent the metadata collection as one semantic description list.
- Group each label and value as one metadata entry so spacing and layout cannot separate a label from its value.
- Render labels as description terms and values as description details.
- Keep the shared metadata macro as the single renderer for ordinary metadata entries.
- Bring the currently hand-written collaboration-member metadata into the same shared presentation. Make only the smallest context or macro adjustment needed to avoid duplicating the component markup.
- Do not render punctuation as part of a metadata label.

Intended shape:

```html
<dl class="meta-list info-block__meta">
  <div class="meta-entry">
    <dt class="meta-label data-label">Release Date</dt>
    <dd class="meta-value">2001</dd>
  </div>
</dl>
```

## Image And Metadata Layout

- Preserve the two existing information-block layouts:
  - Portrait-oriented images place single-column metadata beside the image when sufficient width is available.
  - Landscape-oriented images place metadata underneath the image in two equal-width columns when sufficient width is available.
  - Information blocks without images place metadata in two equal-width columns when sufficient width is available.
  - Metadata entries sharing a grid row keep their label and value content aligned to the top.
- Preserve the existing container-query behavior that stacks portrait images and metadata on narrow information blocks.
- Present landscape metadata in one column on narrow information blocks.
- Allow long metadata collections to continue below the bottom edge of a portrait or cover while retaining their consistent metadata-column width.
- Do not wrap metadata entries around images. Structured label-and-value entries must not abruptly change width partway through a collection, and the implementation must not introduce float-based layout behavior.
- Do not truncate, collapse, scroll, or otherwise hide long metadata collections.

## Requirements Impact

- Add a durable generated-site requirement stating that metadata information on creator and project detail pages uses a consistent stacked label-and-value presentation without label colons.
- Add a durable generated-site requirement for semantic birth, death, and founding visibility and combined event presentation.
- Include preservation of the existing portrait-beside, landscape-below, and narrow-layout stacking behavior in that requirement if the current general responsive-layout requirement is not sufficiently explicit.
- Keep implementation-specific class names, HTML elements, exact font sizes, colors, and spacing values out of `REQUIREMENTS.md`.

## Implementation Steps

1. Add the accepted durable metadata-presentation behavior to `REQUIREMENTS.md`.
2. Add focused failing template tests for the shared metadata renderer before changing production markup.
3. Refactor the shared metadata macro to emit grouped semantic label-and-value entries without colons.
4. Bring collaboration-member name metadata into the shared metadata presentation with the smallest appropriate macro or context change.
5. Replace the current two-column metadata-row CSS with the stacked entry layout.
6. Style labels with the dedicated data-label token, a slightly smaller font size, and semibold weight while preserving value and link styling.
7. Remove the obsolete commented small-screen metadata CSS.
8. Add browser assertions for label/value geometry and the preserved image-orientation layouts.
9. Build the example site and review representative creator and project pages in every built-in theme at desktop and narrow viewport widths.
10. Fine-tune label size and the two vertical gaps if the initial values do not produce a balanced result.
11. Run the established validation set from `REFACTORING_GUIDELINES.md`.
12. Update README or wiki documentation only if the final behavior needs useful user-facing explanation; do not document ordinary visual styling.

## Tests Required

- Shared-macro test proving labels render without trailing colons.
- Shared-macro test proving every label and value is grouped as one metadata entry.
- Shared-macro test proving linked values and configured separators continue to render correctly.
- Metadata-rendering tests proving visible birth, death, and founding events combine their date/place values through the configurable metadata-label format and fall back cleanly to either value alone.
- Configuration tests proving the date-and-place format accepts named placeholder reordering and rejects missing, positional, or unknown placeholders.
- Template test proving collaboration-member name metadata uses the shared stacked presentation.
- Template regression test proving tag-category labels use the shared visual label style without trailing colons while tag links remain unchanged.
- Browser test proving a metadata label is positioned above its corresponding value.
- Browser test proving the next metadata entry starts below the preceding value with a larger visual gap than the label-to-value gap.
- Browser test proving metadata labels use the dedicated theme token, remain distinct from links, and remain legible in every built-in theme.
- Browser test proving portrait-oriented information blocks retain side-by-side image and metadata layout at sufficient width.
- Browser test proving landscape-oriented information blocks place metadata below the image in two equal-width columns at sufficient width.
- Browser test proving narrow landscape-oriented information blocks return metadata to one column.
- Browser test proving image-less information blocks use two equal-width metadata columns at sufficient width and return to one column when narrow.
- Browser test proving metadata entries sharing a grid row keep their content aligned to the top.
- Browser test proving tag-category and metadata labels use the same visual label style.
- Browser test proving narrow portrait-oriented information blocks stack without hiding metadata.
- Browser regression check proving long and multi-value metadata wraps without horizontal overflow or clipping.

## Non-Goals

- Do not change the underlying birth, death, or founding date/place data fields.
- Do not change tag chips, tag links, badges, breadcrumbs, section titles, search syntax, or search-index metadata.
- Do not wrap metadata around portrait or cover images.
- Do not change portrait or cover discovery, rendering visibility, thumbnails, or image aspect handling.
- Do not add metadata-specific theme configuration or new theme tokens unless browser review proves the existing accent and text tokens inadequate.
- Do not enlarge metadata values or reproduce the example image's overall typography, panel dimensions, or spacing.
- Do not add JavaScript for metadata presentation.
