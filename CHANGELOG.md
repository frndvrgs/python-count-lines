# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Tree-sitter-based parsing for Python, JavaScript (`.js`/`.mjs`/`.cjs`), JSX,
  TypeScript, TSX, and Rust.
- `--lang NAME [NAME ...]` flag to limit counting to specific languages.
- Per-language file counts shown under `Source files` in the report.

### Changed

- Renamed the `docstring` bucket to `doc` — now covers Python docstrings,
  JSDoc (`/** */`), and Rust doc-comments (`///`, `//!`, `/** */`, `/*! */`).
- Renamed the program banner from `python-count-lines` to `count-lines`.
- Counter no longer depends on Python's `ast` / `tokenize`; classification
  goes through tree-sitter grammars per file extension.
- Generalised report labels: "Python files" → "Source files",
  "No Python files found." → "No source files found.".

### Removed

- `iter_python_files` (replaced by `iter_source_files`, language-aware).

## [0.1.0] - 2026-04-29

Initial release.

### Added

- `pcl` CLI for counting lines of code in Python projects.
- Per-line classification into `code`, `docstrings`, `comments`, and `blank`.
  Comments detected via `tokenize` (so `#` inside string literals is never
  mistaken for a comment); docstrings detected via `ast`.
- Fallback textual comment scan when a file fails to parse.
- Folder count, Python file count, total lines, and a top-5 largest files panel.
- `--exclude PATTERN [...]` accepting `fnmatch` patterns matched against both
  the full relative path and every individual path component (folder names,
  filenames). Default skips: hidden directories and `__pycache__`.
- `--strip-comments` flag changing the headline LOC to exclude comment-only
  lines while keeping the full breakdown visible.
- Remote scanning: a positional target that looks like a git URL or shorthand
  (e.g. `github.com/owner/repo`) is shallow-cloned with
  `--depth 1 --filter=blob:none`, scanned, and the temp directory cleaned up.
- Dim `(-X% of N)` annotation on folder/file/headline rows when `--exclude`
  filters something out, so the impact of the excludes is visible at a glance.
- `-v` / `--version` flag to print the installed version and exit.
