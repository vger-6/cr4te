# cr4te

A static site generator for organizing and showcasing creative media projects. It scans your folder structure, extracts metadata and media, and builds a clean, searchable HTML gallery.

---

## Features

- **Automatically builds a gallery website** from your folder of creators and projects
- **Thumbnail generation** for portraits, posters, and images
- **Tag-based filtering** and search
- **Fast static HTML output** with no runtime dependencies

---

## Folder Structure

```
Creators/
├── Alice/
│   ├── cr4te.json           # Optional metadata override
│   ├── README.md            # Optional creator description
|   ├── Portrait1.jpg
│   └── Project1/
│       ├── Landscape1.jpg
│       ├── clip.mp4
│       └── SubGroup/
│           └── *.jpg
└── Bob & Charlie/             # Collaboration folder
    └── ProjectZ/
```

---

## Installation

```bash
git clone https://github.com/yourname/cr4te.git
cd cr4te
pip install -r requirements.txt
```

---

## Usage

### Build JSON metadata first:
```bash
python cr4te.py build-json -i /path/to/Creators
```

### Generate HTML site second:
```bash
python cr4te.py build-html -i /path/to/Creators
```

> Output will be saved to `site_output/`.

---

## Customization

- **CSS styles** live in `css/`
- **Default thumbnails** are in `defaults/`
- You can override project metadata with `cr4te.json` inside each creator folder
- Add creator/project descriptions using `README.md`

---

## Output Example

- `index.html` — Creator overview
- `creators/<name>.html` — Creator profile
- `projects/<name>.html` — Individual project page
- `tags.html` — Browse all tags

---

## Requirements

- Python 3.8+
- Pillow
- Markdown

Install via:
```bash
pip install pillow markdown
```

---

## License

This project is licensed under the terms of the LICENSE file included.

---

## Credits

Created for artists, curators, ...

---

## TODO


