from __future__ import annotations

import os
from collections.abc import Iterator
from fnmatch import fnmatch
from pathlib import Path

from pcl.languages.registry import SUPPORTED_LANGUAGES

DEFAULT_SKIP_DIRS = frozenset({"__pycache__", "node_modules"})


def is_excluded(rel_path: Path, patterns: list[str]) -> bool:
    """Whether a path (relative to the scan root) should be excluded.

    Excluded if:
    - any path component starts with '.' (hidden dirs/files)
    - any path component is in DEFAULT_SKIP_DIRS
    - the relative path matches a user pattern (fnmatch on full path),
      or any single component matches the pattern.
    """
    parts = rel_path.parts
    for part in parts:
        if part.startswith(".") and part not in (".", ".."):
            return True
        if part in DEFAULT_SKIP_DIRS:
            return True

    rel_str = rel_path.as_posix()
    for pat in patterns:
        if fnmatch(rel_str, pat):
            return True
        if any(fnmatch(part, pat) for part in parts):
            return True
    return False


def iter_source_files(
    root: Path,
    *,
    languages: set[str] | None,
    excludes: list[str],
) -> Iterator[Path]:
    """Yield source files under root with extensions in supported languages.

    `languages=None` means all supported languages. Unknown extensions are
    skipped silently — this is not a generic file walker.
    """
    selected = (
        {ext for spec in SUPPORTED_LANGUAGES for ext in spec.extensions}
        if languages is None
        else {
            ext
            for spec in SUPPORTED_LANGUAGES
            if spec.name in languages
            for ext in spec.extensions
        }
    )

    root = root.resolve()
    if root.is_file():
        if root.suffix.lower() in selected:
            yield root
        return

    for current_dir, dirs, files in os.walk(root):
        current = Path(current_dir)
        # prune subdirs in-place so os.walk skips them
        dirs[:] = [
            d for d in dirs
            if not is_excluded((current / d).relative_to(root), excludes)
        ]
        for fname in files:
            ext = os.path.splitext(fname)[1].lower()
            if ext not in selected:
                continue
            file_path = current / fname
            if is_excluded(file_path.relative_to(root), excludes):
                continue
            yield file_path


def iter_python_files(root: Path, excludes: list[str]) -> Iterator[Path]:
    """Deprecated shim — Task 9 removes the last caller (pcl.cli)."""
    return iter_source_files(root, languages={"python"}, excludes=excludes)
