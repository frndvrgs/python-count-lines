from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

_URL_PATTERNS = (
    re.compile(r"^https?://"),
    re.compile(r"^git@[^:]+:"),
    re.compile(r"^ssh://git@"),
    re.compile(r"^git://"),
)
_SHORTHAND = re.compile(r"^(github\.com|gitlab\.com|bitbucket\.org|codeberg\.org)/[^/]+/[^/]+/?$")


def is_remote_url(target: str) -> bool:
    if any(p.match(target) for p in _URL_PATTERNS):
        return True
    return bool(_SHORTHAND.match(target))


def normalise_url(target: str) -> str:
    """Turn shorthand like 'github.com/owner/repo' into a clonable https URL."""
    if _SHORTHAND.match(target):
        return f"https://{target.rstrip('/')}.git"
    return target


@contextmanager
def materialise_remote(target: str) -> Iterator[Path]:
    """Clone target into a temp dir; yield the path; clean up on exit.

    Uses a shallow clone (--depth 1) without history or submodules — we only
    need a snapshot of the working tree.
    """
    if shutil.which("git") is None:
        raise RuntimeError("git is required to scan remote repositories but was not found on PATH")

    url = normalise_url(target)
    tmp = Path(tempfile.mkdtemp(prefix="pcl-"))
    try:
        result = subprocess.run(
            ["git", "clone", "--depth", "1", "--quiet", "--filter=blob:none", url, str(tmp)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"git clone failed: {result.stderr.strip() or result.stdout.strip()}")
        yield tmp
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
