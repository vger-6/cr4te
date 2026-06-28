# cr4te Requirements

These are durable product and design requirements for cr4te. They must hold unless this file is explicitly revised.

## Requirement Conventions

- Each requirement has a stable ID for references from tests, documentation, issues, and commits.
- `must` and `must not` describe required behavior.
- Requirements describe durable outcomes and relationships. Exact visual values belong in the shared design tokens unless the value is itself a user-facing contract.
- Tests that primarily protect a requirement should identify its requirement ID in the test docstring.
- Every durable requirement must appear in the checked requirement-to-test map in `tests/test_requirement_traceability.py`.
- Implementation and refactoring guidance belongs in [REFACTORING_GUIDELINES.md](REFACTORING_GUIDELINES.md).
- Planned but uncommitted product ideas belong in [TODO.md](TODO.md).

## Metadata And Identity

- **META-001:** Metadata must live beside the folder it describes. Creator metadata lives in each creator folder's `cr4te.json`; project metadata lives in each project folder's `cr4te.json`. Creator metadata must not nest project metadata under `projects`.
- **META-002:** Canonical creator names and project titles must come exclusively from their folder names. They drive identity, output-path hashes, and creator-reference resolution and must not appear as `name` or `title` fields in `cr4te.json`.
- **META-003:** Creator `display_name` and project `display_title` must be editable metadata whose generated defaults are their folder names. Display values drive visible labels, user-facing sorting, and search; blank display values must fall back to the canonical folder name.
- **META-004:** Collaboration `members` and creator `collaborations` must store canonical creator folder names. Resolved references display the referenced creator's `display_name`; unresolved member strings display unchanged.
- **META-005:** `cr4te.json` must contain editable structured metadata only. It must not contain generated scan output such as `media_groups`, and it must not contain narrative `info` fields.
- **META-006:** Narrative and descriptive text must come only from `README.md` files in creator and project folders.
- **META-007:** Creator type-specific metadata must use `person` and `collaboration` branches. The inactive branch must be pruned when the creator type changes.
- **META-008:** Project domain metadata must be stored as generic `facets` in the project-level `cr4te.json`. Empty stale facets must be pruned, but stale facets with values must be retained as a domain-change failsafe.
- **META-009:** Date metadata must accept only valid calendar dates in `yyyy`, `yyyy-mm`, or `yyyy-mm-dd` form. Display must preserve the stored precision: year-only dates display as a year, month dates display as month and year, and full dates display with day, month, and year.
- **META-010:** Portrait and cover image selection must be derived exclusively from filesystem discovery.

## Metadata Lifecycle And Configuration

- **LIFE-001:** `build` must be the metadata lifecycle command. It creates and reconciles editable metadata before rendering. `init-metadata` and `sync-metadata` must not be available.
- **LIFE-002:** Editable project facet scaffolding must be derived from the resolved `site_rendering.project_metadata.fields` configuration.
- **LIFE-003:** Domain presets must be only one way to produce resolved project facet configuration. A saved configuration file must be self-contained for later builds.
- **LIFE-004:** A CLI domain override must replace the active project facet field set instead of merging with the configured facet fields.
- **LIFE-005:** Portrait discovery and portrait visibility must be independently controlled by resolved configuration. Portrait discovery and portrait-role assignment during library indexing must depend only on `media_rules` and remain invariant across portrait visibility settings. An omitted CLI portrait-discovery or portrait-visibility override must preserve its configured value.
- **LIFE-006:** Gallery aspect-ratio configuration must use a string containing two positive integers in `width/height` order, separated by one slash. Resolved configuration must normalize accepted values to canonical `width/height` form.

## Build Modes And Issue Reporting

- **BUILD-001:** Best-effort builds must skip invalid creators or invalid projects and report structured issues. Invalid project metadata must skip only that project, not the whole creator.
- **BUILD-002:** `--strict` must fail fast on errors.
- **BUILD-003:** Build issues must remain structured with scope, severity, code, path, and message.
- **BUILD-004:** Render-time asset failures must be represented as structured build issues and included in the final build summary instead of existing only as logs.
- **BUILD-005:** Repeated failures with the same scope, issue code, and path must be reported only once per build.
- **BUILD-006:** Every successful build must report final phase timings for theme discovery, output preparation, metadata reconciliation, library indexing, HTML rendering, and their total.
- **BUILD-007:** Every successful build must report constant-memory asset statistics that distinguish created symbolic links, created hard links, reused media links, generated and reused source thumbnails, default-thumbnail uses, and source-hash checks.
- **BUILD-008:** Expected operational failures during a build phase must report the failed phase and return exit status `1`. Invalid command arguments, configuration, or paths must return exit status `2`. Successful builds, completed best-effort builds, and explicit user cancellation must return exit status `0`.
- **BUILD-009:** Metadata reconciliation skips must retain structured issue reasons and participate in final build reporting. Issues repeated by later build phases with the same scope, issue code, and path must appear only once.

## Command-Line Interface

- **CLI-001:** The command-line interface must expose `build`, `print-config`, and `delete-metadata` as its top-level commands. `delete-metadata` must recursively target creator and project `cr4te.json` files while preserving all media files.
- **CLI-002:** `--force` must consistently skip the confirmation prompt for the command that receives it. `build --clear-thumbnail-cache` must remove cached thumbnails before rebuilding, while `delete-metadata --dry-run` must list deletion candidates without removing them. Metadata dry-run and forced deletion modes must be mutually exclusive.
- **CLI-003:** Top-level and command-specific help must describe command purpose, option behavior, constrained values, and representative examples. Usage errors discovered after argument parsing must display usage for the active command.

## Asset Staging And Failure Handling

- **ASSET-001:** Best-effort builds must continue after recoverable asset failures without generating known-broken references.
- **ASSET-002:** Failed portrait and cover thumbnails must use generated defaults.
- **ASSET-003:** Missing media and unreadable text or gallery images must be omitted from generated pages.
- **ASSET-004:** Unavailable optional media inspection data, such as audio duration, must use a safe fallback and produce a warning.
- **ASSET-005:** `--strict` must abort immediately on asset errors but not on asset warnings.
- **ASSET-006:** Media staging during `build` must not silently copy source media when links cannot be created. It may use symbolic links or hard links.
- **ASSET-007:** If neither symbolic nor hard links can be created, media staging must abort with a structured asset error and a clear message regardless of strict mode.
- **ASSET-008:** Special-image candidate selection must use deterministic case-insensitive lexicographical path ordering with original spelling as the tie-breaker. Named portrait and cover discovery must match configured basenames case-insensitively and prefer matching images directly inside the creator or project folder they describe before matching images below that folder.
- **ASSET-009:** Named portrait discovery must use only images matching the configured portrait basename. Auto portrait discovery may fall back to the first portrait-oriented eligible image anywhere below the creator folder, including project folders.
- **ASSET-010:** Cover discovery must search only below the corresponding project folder and fall back from named matches to the first landscape-oriented eligible image, then to the first eligible image, then to the generated default cover.
- **ASSET-011:** An image in the same folder as a video and with the same case-insensitive stem is a poster candidate. The first poster candidate must be selected for the video. Poster candidates may serve as portraits or covers through explicit basename matches, but must not participate in portrait or cover fallback selection.
- **ASSET-012:** Images matching the portrait or project-cover basename, all video-poster candidates, and images selected as portrait or cover fallbacks must be excluded from gallery media before sampling. Unselected ordinary fallback candidates must remain eligible for galleries, and one image may serve multiple selected special-image roles.

## Thumbnail Freshness

- **THUMB-001:** Source-derived thumbnail freshness must be determined by comparing the source image's SHA-256 hash with the thumbnail's hash sidecar, independently of source, parent-folder, or thumbnail modified times.
- **THUMB-002:** Every generated source-derived thumbnail must have a sidecar containing only the SHA-256 hash of the source content used for that thumbnail.
- **THUMB-003:** An existing source-derived thumbnail may be reused only when its readable hash sidecar exactly matches the current source hash. A missing, unreadable, or different sidecar must cause regeneration and replacement of the sidecar.
- **THUMB-004:** Thumbnail freshness must remain correct when source files are replaced or synchronized while preserving, decreasing, or coarsening their modified times.

## Generated Site Behavior

- **SITE-001:** Generated detail pages must allow only one audio or video element to play at a time.
- **SITE-002:** Starting playback must pause the previously active media element without resetting its source, selection, or playback position, regardless of whether playback started through cr4te controls, native browser behavior, or JavaScript.
- **SITE-003:** Generated pages must remain usable when browser storage is unavailable. Features that persist preferences must continue operating for the current page without producing unhandled errors.
- **SITE-004:** Generated media markup must not misidentify the format of supported media files.
- **SITE-005:** Generated gallery images must have meaningful alternative text derived from available image metadata.
- **SITE-006:** Generated-site controls must use keyboard-operable native controls where the interaction supports them and must have accessible names.
- **SITE-007:** Keyboard-focused generated-site controls must display a visible focus indicator that does not alter layout and is not shown solely because of mouse interaction.
- **SITE-008:** Generated-site toggle controls must expose their current state to assistive technologies.
- **SITE-009:** The theme menu must support conventional keyboard navigation, selection, and Escape-to-close behavior.
- **SITE-010:** Generated media players must provide conventional, control-scoped keyboard operation without overriding the native keyboard behavior of their buttons and sliders.
- **SITE-011:** Every generated page must display a consistently styled cr4te logo that links to the creator overview, including when the creator overview is already the current page.
- **SITE-012:** Generated detail-page content must remain available without JavaScript at every supported viewport width. Narrow layouts must present profile and overview content before media and other regular sections without moving content nodes at runtime.
- **SITE-013:** Generated-site lightboxes must behave as modal dialogs with keyboard-operable native controls. Opening a lightbox must move focus into it, focus must remain inside while it is open, and closing it must return focus to its trigger. Escape-to-close and arrow-key image navigation must remain available.
- **SITE-014:** The `disabled` portrait-visibility mode must omit portrait markup, perform no portrait-thumbnail work, and render creator overview entries as text cards.
- **SITE-015:** The `details` portrait-visibility mode must omit portrait markup when discovery finds no eligible image. The `all` mode must use generated default portraits when discovery finds no eligible image.
- **SITE-016:** Creator and project detail pages must present metadata consistently as stacked label-and-value entries without label colons, including creator, collaboration, participant, and member information embedded in those pages. Portrait-oriented information blocks must place single-column metadata beside the image when sufficient width is available. Landscape-oriented and image-less information blocks must present metadata in two equal-width columns when sufficient width is available, with landscape metadata placed below the image and entries sharing a row remaining top-aligned. Narrow layouts must stack images and metadata and present metadata in one column without hiding content.
- **SITE-017:** Birth, death, and founding metadata must each be configurable as one visible event entry. When both the event's date and place have values, the generated value must use the configured named-placeholder date-and-place format; when only one value is available, it must render alone.
- **SITE-018:** Tag category labels must use the same visual label presentation as metadata labels and omit trailing colons, while tags must preserve their distinct linked-chip presentation.
- **SITE-019:** Creator and project media must be presented as folder-derived groups. The actual root group must appear first, groups whose final folder name matches the configured metadata folder must appear second, and remaining groups must follow in lexicographical order by their complete relative folder paths.
- **SITE-020:** Generated pages must respect reduced-motion preferences by removing nonessential interface transition durations and avoiding smooth programmatic scrolling.
- **SITE-021:** Generated human-readable phrases that combine dynamic or configurable values must use validated complete named-placeholder label formats where wording or word order may vary. Collaboration project titles, overview search placeholders, site-logo accessible labels, and creator/project image descriptions must not be assembled from hardcoded sentence fragments.
- **SITE-022:** Generated pages must apply a previously selected available theme before visible page content is rendered.
- **SITE-023:** Empty creator and project overviews must omit unusable search controls and show configured collection-empty messages. Overview searches with no matches must keep the search control visible and show a configured polite no-results state.
- **SITE-024:** Generated navigation must clearly identify the current overview and expose a project page's creator or collaboration as contextual navigation without redundantly repeating creator-page context. On narrow screens, contextual navigation must be able to wrap independently while the logo, primary navigation, and theme control remain together.
- **SITE-025:** Every generated page must place global navigation on a full-width theme-controlled surface and place its level-one title inside the shared inset content region. Creator, project, and tag overview pages must keep that title available to assistive technology while omitting the visible title strip; detail-page titles must use a theme-controlled background strip, border, spacing, and corner radius with padded text. Overview search controls and overview or detail panels must align with the shared content edges. Search controls must use body typography and retain usable single-line input behavior. Every theme must provide coherent contrast for navigation, visible titles, search controls, and panels.
- **SITE-026:** Generated-site typography must keep content visually primary through a restrained hierarchy: page titles must be more prominent than section titles, section titles must be more prominent than body text, and Markdown headings must remain subordinate to their section while preserving readable, distinguishable levels.
- **SITE-027:** Generated pages must use the shared spacing scale consistently. Spacing within a component or semantic group must be tighter than spacing between independent sections; switching between horizontal and stacked responsive layouts must preserve that grouping. Component-owned spacing must prevent browser-default terminal margins from creating accidental extra space.
- **SITE-028:** The `details` portrait-visibility mode must use text cards on creator overviews while rendering discovered portraits on creator and project detail pages. The `all` mode must preserve portrait image cards and their icon badges.
- **SITE-029:** Text creator-overview cards must present the creator name and non-zero project and media counts. Project counts must occupy a separate line above media counts. Count phrases, badge tooltips, and badge accessible labels must use dedicated count labels independently from entity labels used for headings and navigation.
- **SITE-030:** Within each folder-derived media group, sections must follow the resolved configured media-type order. Media directly in a creator or project folder and media in its configured metadata folder must use root-group section labels.
- **SITE-031:** Standalone nouns, control names, and count labels must remain ordinary labels with roles independent from complete configurable phrase formats.
- **SITE-032:** JavaScript-enhanced image galleries must not expose their unbuilt startup layout during normal initialization, while generated pages must retain usable no-JavaScript gallery fallback markup.
- **SITE-033:** Empty tag pages and empty major detail-page regions must show configured contextual empty states. Absent optional sections must remain omitted rather than each receiving an empty state, and static empty states must not require JavaScript.
- **SITE-034:** Tag overview categories must use a responsive grid that adapts its column count to the available width while keeping each category comfortably scannable.

## Themes

- **THEME-001:** Built-in and user-provided themes must use the same discovery, registry, rendering, and output-copy path.
- **THEME-002:** Custom themes must be loaded only from an explicitly supplied `build --themes-dir` directory.
- **THEME-003:** Custom themes must be self-contained CSS files named with lowercase portable slugs and must define the matching `.theme-<slug>` selector.
- **THEME-004:** Custom themes must not override built-in theme IDs.
- **THEME-005:** A supplied themes path that is missing or is not a directory must abort before build side effects.
- **THEME-006:** Frozen Aurora must remain the explicit default theme.
- **THEME-007:** Theme initialization failures must never leave generated pages hidden.
- **THEME-008:** The public theme-token surface must allow built-in and custom themes to control the navigation surface, pagination-button corner radius, and optional audio-track separators. Shared defaults must remain usable when a custom theme does not override those tokens, including square pagination buttons and disabled track separators.

## Architecture And Scalability Invariants

- **ARCH-001:** The CLI build path must preserve a streaming, two-pass design suitable for large libraries.
- **ARCH-002:** The build path must not retain full media-group path lists for the whole library and must keep only lightweight index and overview data globally.
- **ARCH-003:** Any cache for image dimensions, thumbnails, audio durations, or similarly expensive data must be bounded or disk-backed. Whole-library media data must not be retained in an unbounded in-memory cache.
