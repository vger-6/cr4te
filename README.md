# cr4te

![Version](https://img.shields.io/badge/version-0.0.1-blue.svg)
[![License](https://img.shields.io/badge/license-NonCommercial-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/python-3.10+-yellow.svg)

cr4te is a local-first static site generator for personal media archives. It scans a folder of creators and projects, reconciles editable metadata, generates thumbnails, and writes a responsive, searchable HTML gallery for images, videos, audio, documents, and Markdown text.

The generated site has no database or server requirement. You can open it directly from disk or serve the output folder with any static file server.

## Features

- Gallery generation from an existing folder hierarchy
- Creator, project, and tag overview pages
- Creator and project detail pages
- Images, videos, audio playlists, PDFs/documents, and Markdown text
- Search, tags, pagination, lightbox, captions, media controls, and built-in or custom themes
- Responsive image gallery layouts: fixed-aspect and justified
- Domain presets for `creator`, `art`, `music`, `film`, and `book`
- Editable `cr4te.json` metadata beside creator and project folders
- Best-effort builds by default, with `--strict` available for fail-fast validation
- Static HTML/CSS/JS output with no runtime backend

## Quick Start

Install from a local checkout:

```bash
git clone https://github.com/vger-6/cr4te.git
cd cr4te
pip install -e .
```

Try the bundled music example:

```bash
cr4te build -i data/example/Musicians -o output/example-site --domain music
```

Open `output/example-site/index.html`, or serve it locally:

```bash
cd output/example-site
python -m http.server 8000
```

Then visit [http://localhost:8000](http://localhost:8000).

Build your own archive:

```bash
cr4te build -i path/to/Creators -o path/to/site --domain music
```

## Library Shape

cr4te expects one input folder containing creator folders. Each creator can contain media directly and one level of project folders.

```text
Musicians/
|-- Astra Vey/
|   |-- portrait.png
|   |-- README.md
|   |-- cr4te.json
|   |-- Glass Circuit/
|   |   |-- cr4te.json
|   |   |-- cover.png
|   |   |-- README.md
|   |   |-- 01 - Chrome Pulse.mp3
```

`cr4te.json` contains editable structured metadata. `README.md` contains narrative/descriptive text.
Portraits and covers are selected from image filenames. Portrait discovery can use only named matches or also fall back to a portrait-oriented image. Portrait visibility independently controls whether discovered portraits appear nowhere, only on detail pages, or everywhere; it does not change library discovery or classification. Covers use named matches, then landscape-oriented and arbitrary image fallbacks.

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
- `--domain art|music|film|book|model|creator`: apply a domain preset
- `--image-sample-strategy none|spread|head|all`: choose how gallery images are sampled per folder
- `--portrait-discovery named|auto`: control how portrait images are selected
- `--portrait-visibility disabled|details|all`: control where portraits are rendered
- `--strict`: fail fast on invalid metadata instead of skipping invalid entries
- `--open`: open `index.html` after a successful build

## Output

The generated site includes:

- `index.html`: creator overview
- `projects.html`: project overview
- `tags.html`: tag browser
- `html/`: generated creator and project pages
- `assets/`: static CSS, JavaScript, defaults, and favicon
- `thumbnails/`: generated thumbnails
- `symlinks/`: staged media links

Media staging uses symbolic links first, then hard links. If neither can be created, cr4te aborts instead of copying media files.

## Documentation

The wiki is the full manual:

- [Getting Started](https://github.com/vger-6/cr4te/wiki/Getting-Started)
- [Library Structure](https://github.com/vger-6/cr4te/wiki/Library-Structure)
- [Metadata](https://github.com/vger-6/cr4te/wiki/Metadata)
- [Configuration](https://github.com/vger-6/cr4te/wiki/Configuration)
- [Domain Presets](https://github.com/vger-6/cr4te/wiki/Domain-Presets)
- [Build Command](https://github.com/vger-6/cr4te/wiki/Build-Command)
- [Generated Site](https://github.com/vger-6/cr4te/wiki/Generated-Site)
- [Media and Galleries](https://github.com/vger-6/cr4te/wiki/Media-and-Galleries)
- [Tags and Search](https://github.com/vger-6/cr4te/wiki/Tags-and-Search)
- [Custom Themes](https://github.com/vger-6/cr4te/wiki/Custom-Themes)
- [Troubleshooting](https://github.com/vger-6/cr4te/wiki/Troubleshooting)

## Development

Install development tools:

```bash
pip install -e ".[dev]"
```

Run unit tests:

```bash
python -m unittest discover tests
```

Browser tests live in `tests_browser` and require the `browser-test` extra.

## Project History

This repository contains the current development codebase for cr4te.

An earlier codebase is archived at:

https://github.com/vger-6/cr4te-old

The archived repository is kept for historical reference only. Active development continues in this repository.

## License

This software is provided for personal, educational, and non-commercial purposes only.

See [LICENSE](LICENSE) for details. Commercial use requires written permission from the author.

Contributions, feedback, and bug reports are welcome.
