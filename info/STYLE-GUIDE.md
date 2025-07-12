# Python Code Style Guide

This document provides a consistent and comprehensive guide for naming, formatting, and organizing Python code. The goal is to improve code readability, maintainability, and team collaboration.

---

## Contents

1. [General Naming Conventions](#general-naming-conventions)
2. [Code Layout and Formatting](#code-layout-and-formatting)
3. [Function and Method Design](#function-and-method-design)
4. [Class and Module Naming](#class-and-module-naming)
5. [Error Handling](#error-handling)
6. [Logging and Debugging](#logging-and-debugging)
7. [File and Directory Path Naming](#file-and-directory-path-naming)
8. [Testing Guidelines](#testing-guidelines)

---

## General Naming Conventions

*To be added.*

## Code Layout and Formatting

*To be added.*

## Function and Method Design

*To be added.*

## Class and Module Naming

*To be added.*

## Error Handling

*To be added.*

## Logging and Debugging

*To be added.*

---

## File and Directory Path Naming

This section outlines consistent naming conventions for variables and functions related to file and directory handling in Python. It applies to both string paths and `Path` objects from the `pathlib` module.

### General Principles

* Use `path` in variable names for `Path` objects (e.g., `file_path`, `output_path`).
* Use the `*_str` suffix only if you need to distinguish a raw string path from a `Path` object.
* **Treat absolute or resolved paths as the default** — no prefix is needed (e.g., `output_dir`, `thumb_path`).
* Use a `rel_` prefix only for relative paths (e.g., `rel_file_path`, `rel_assets_dir`).
* Use `dir_` / `file_` prefixes to distinguish between directories and files when not obvious from context.
* Use `*_name` only for names without any path components (e.g., `thumb_file_name`).
* Use nouns for variables and verbs for functions and methods.

### Variable Naming Conventions

| Description             | Example Value                 | Suggested Variable Name        |
| ----------------------- | ----------------------------- | ------------------------------ |
| File name only (string) | "thumb.png"                   | `thumb_file_name`              |
| Directory name (string) | "html"                        | `html_dir_name`                |
| Relative file path      | "images/thumb.png"            | `rel_file_path`                |
| Absolute file path      | "/home/user/images/thumb.png" | `file_path`                    |
| Relative directory path | "images/new"                  | `rel_dir_path`                 |
| Absolute directory path | "/home/user/images/new"       | `images_dir`                   |
| Path object             | `Path("images/thumb.png")`    | `image_path`, `rel_image_path` |

### Function Naming Conventions

| Function Purpose                  | Suggested Function Name    |
| --------------------------------- | -------------------------- |
| Build relative path to image file | `build_rel_image_path()`   |
| Build absolute path to asset file | `build_image_path()`       |
| Join base path with subdirectory  | `join_base_with_subdir()`  |
| Extract file name from a path     | `get_filename_from_path()` |

### Additional Tips

* Prefer clarity over brevity: `images_dir` is better than `imgD`.
* Be consistent across your codebase.
* Avoid mixing `file` and `dir` semantics in a single variable name.
* Document any exceptions clearly.

This section aims to make file handling code easier to read, understand, and maintain.

---

## Testing Guidelines

*To be added.*

