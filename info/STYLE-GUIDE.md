# Style Guide

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

* Use `path` in variable names for `Path` objects.
* Use `*_str` suffix if you need to distinguish a string path from a `Path` object.
* Use `abs_` / `rel_` prefixes to denote absolute or relative paths.
* Use `dir_` / `file_` prefixes to differentiate between directories and files.
* Use `*_name` for names only (not full paths).
* Use nouns for variables and verbs for functions.

### Variable Naming Conventions

| Description             | Example Value                 | Suggested Variable Name        |
| ----------------------- | ----------------------------- | ------------------------------ |
| File name only (string) | "thumb.png"                   | `filename`, `file_name`        |
| Directory name (string) | "html"                        | `dirname`, `dir_name`          |
| Relative file path      | "images/thumb.png"            | `rel_file_path`                |
| Absolute file path      | "/home/user/images/thumb.png" | `abs_file_path`                |
| Relative directory path | "images/new"                  | `rel_dir_path`                 |
| Absolute directory path | "/home/user/images/new"       | `abs_dir_path`                 |
| Path object             | `Path("images/thumb.png")`    | `image_path`, `rel_image_path` |

### Function Naming Conventions

| Function Purpose                  | Suggested Function Name    |
| --------------------------------- | -------------------------- |
| Build relative path to image file | `build_rel_image_path()`   |
| Build absolute path to asset file | `build_abs_asset_path()`   |
| Join base path with subdirectory  | `join_base_with_subdir()`  |
| Extract file name from a path     | `get_filename_from_path()` |

### Additional Tips

* Prefer clarity over brevity: `abs_dir_path` is better than `adp`.
* Be consistent across your codebase.
* Avoid mixing `file` and `dir` semantics in a single variable name.
* Document any exceptions clearly.

This section aims to make file handling code easier to read, understand, and maintain.

---

## Testing Guidelines

*To be added.*

