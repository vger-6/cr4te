# cr4te

![Version](https://img.shields.io/badge/version-0.0.1-blue.svg)
[![License](https://img.shields.io/badge/license-NonCommercial-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/python-3.10+-yellow.svg)

cr4te is a local-first static site generator for personal media archives. It scans a folder of creators and projects, detects images, videos, audio, documents, and Markdown files, reconciles editable metadata, generates thumbnails, and writes a responsive, searchable HTML gallery.

The generated site has no database or server requirement. You can open it directly from disk or serve the output folder with any static file server.



## Features

- Gallery generation from an existing folder hierarchy
- Images, videos, audio playlists, PDFs/documents, and Markdown text
- Creator, project, and tag overview pages
- Search, tags, pagination, lightbox, captions, and theme switching
- Responsive image gallery layouts: justified and fixed-aspect
- Domain presets for `creator`, `art`, `music`, `film`, `book`
- Editable metadata beside each creator and project folder
- Best-effort builds by default, with `--strict` available for fail-fast validation
- Static HTML/CSS/JS output with no runtime backend

## Folder Structure

cr4te expects one input folder containing creator folders. Each creator can contain media at the creator level and one level of project folders.

```text
Musicians/
|-- Astra Vey/
|   |-- portrait.png
|   |-- README.md
|   |-- cr4te.json
|   |-- Glass Circuit/
|   |   |-- cr4te.json
|   |   |-- cover.png
|   |   |-- track01.mp3
|   |   |-- README.md
|-- Milo Kest & Astra Vey/
|   |-- cr4te.json
|   |-- Split Meridian/
|   |   |-- cr4te.json
|   |   |-- cover.png
|   |   |-- track01.mp3
```

This maps naturally to many archive types:

- Artists -> works or projects
- Musicians -> albums
- Filmmakers -> movies
- Authors -> books
- General creators -> projects

## Installation

```bash
git clone https://github.com/vger-6/cr4te.git
cd cr4te
pip install -e .
```

For development checks, install the optional tools:

```bash
pip install -e ".[dev]"
```

## Quick Start

```bash
cr4te build -i path/to/Creators -o path/to/output/site --domain art
```

To try the bundled example library:

```bash
cr4te build -i data/example/Musicians -o output/example-site --domain music
```

Open the result automatically:

```bash
cr4te build -i path/to/Creators -o path/to/output/site --domain art --open
```

The `build` command also creates or reconciles creator-level and project-level `cr4te.json` files before rendering. Existing editable values are preserved; missing editable keys are added. If an older creator file still contains matching nested project metadata, build seeds the project-level file before pruning the nested entry.

If the output folder already exists, cr4te asks before clearing it. By default it keeps the `thumbnails` folder so rebuilds can reuse generated thumbnails. Use `--clean` to clear thumbnails too, and `--force` to skip the confirmation prompt.

## Commands

```bash
cr4te build -i path/to/Creators -o path/to/site
cr4te build -i path/to/Creators -o path/to/site --domain film
cr4te build -i path/to/Creators -o path/to/site --strict
cr4te build -i path/to/Creators -o path/to/site --clean --force
cr4te print-config
cr4te print-config --domain music
cr4te clean-json -i path/to/Creators --dry-run
cr4te clean-json -i path/to/Creators --force
```

Useful build options:

- `--config my_config.json`: load a JSON configuration file
- `--domain art|music|film|book|creator`: apply a domain preset
- `--image-sample-strategy none|spread|head|all`: choose how gallery images are sampled per folder
- `--portrait-strategy none|named|auto`: control portrait discovery
- `--strict`: fail fast on invalid metadata instead of skipping invalid entries
- `--open`: open `index.html` after a successful build

## Metadata

Metadata lives beside the folder it describes. Creator metadata lives in each creator folder's `cr4te.json`; project metadata lives in each project folder's `cr4te.json`.

Narrative text does not live in JSON. Creator and project descriptions come from `README.md` files in the corresponding folders.

`cr4te.json` contains editable structured metadata only. Extra or obsolete fields fail validation.

Example creator metadata:

```json
{
  "name": "Astra Vey",
  "type": "person",
  "portrait": "portrait.png",
  "person": {
    "active_since": "2015",
    "birth": {
      "date": "1986-01",
      "place": "Berlin"
    },
    "nationalities": ["Swiss"]
  },
  "aliases": [],
  "collaborations": [],
  "tags": {
    "Genre": ["Electro-pop"]
  }
}
```

Example project metadata:

```json
{
  "title": "Glass Circuit",
  "release_date": "2021-03-08",
  "cover": "extras/cover.png",
  "tags": {
    "Mood": ["Luminous"]
  },
  "facets": {
    "labels": ["Orbit"],
    "instruments": ["Synth"]
  }
}
```

Dates use `yyyy`, `yyyy-mm`, or `yyyy-mm-dd`.

For collaborations, set `"type": "collaboration"` and use the `collaboration` branch. cr4te prunes the inactive `person` or `collaboration` branch when the creator type changes.

## Configuration

cr4te ships with defaults. To create a self-contained config file:

```bash
cr4te print-config --domain art > my_config.json
```

Then build with it:

```bash
cr4te build -i path/to/Creators -o path/to/site --config my_config.json
```

Configuration is grouped into:

- `site_labels`: labels used in generated pages
- `site_rendering`: visible fields, gallery behavior, metadata rendering, and portrait display
- `media_rules`: scan rules, sampling, file discovery, and naming conventions

Project facet scaffolding comes from `site_rendering.project_metadata.fields`. Domain presets are one way to set those fields, but a saved config file should be self-contained for later builds. Passing a new `--domain` replaces the active project facet field set.

When the active project facet field set changes, empty stale facets are pruned from project `cr4te.json` files. Stale facets with values are kept so filled metadata is not lost when switching domains.

Example project metadata field configuration:

```json
{
  "site_rendering": {
    "project_metadata": {
      "fields": {
        "mediums": {
          "searchable": true,
          "clickable": true,
          "tags": true
        },
        "materials": {
          "searchable": true,
          "clickable": true,
          "tags": true
        }
      }
    }
  }
}
```

Project facet labels are configured separately under `site_labels.project_facets`:

```json
{
  "site_labels": {
    "project_facets": {
      "actors": {
        "singular": "Cast Member",
        "plural": "Cast"
      }
    }
  }
}
```

## Output

The generated site includes:

- `index.html`: creator overview with search
- `projects.html`: project overview with search
- `tags.html`: tag browser
- `html/`: generated creator and project pages
- `assets/`: static CSS, JavaScript, defaults, and favicon
- `thumbnails/`: generated thumbnails
- `symlinks/`: staged media links or copied media files when links are unavailable

## Troubleshooting

### Browser storage on file URLs

Some browsers restrict `localStorage` when opening files directly. If search, theme state, or other client-side behavior seems inconsistent, serve the output folder locally:

```bash
cd path/to/output/site
python -m http.server 8000
```

Then visit [http://localhost:8000](http://localhost:8000).

### Build behavior

- Use `--strict` when you want invalid metadata to fail the build immediately.
- Without `--strict`, invalid creators or projects are skipped and reported in the build summary where supported.
- Use `--force` to skip confirmation prompts.
- Use `--clean` with `build` when you want to regenerate thumbnails from scratch.
- Use `clean-json --dry-run` before deleting creator and project metadata files.


## License

This software is provided for personal, educational, and non-commercial purposes only.

See [LICENSE](LICENSE) for details. Commercial use requires written permission from the author.

Contributions, feedback, and bug reports are welcome.
