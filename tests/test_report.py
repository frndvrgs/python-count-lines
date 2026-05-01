from __future__ import annotations

import re
from pathlib import Path

from pcl.counter import FileStats
from pcl.report import Report, render

ANSI = re.compile(r"\x1b\[[0-9;]*m")


def _strip(s: str) -> str:
    return ANSI.sub("", s)


def _stats(name: str, total: int, *, comment: int = 0) -> FileStats:
    return FileStats(
        path=Path(f"/repo/{name}"),
        total=total,
        blank=0,
        comment=comment,
        docstring=0,
        code=total - comment,
    )


def test_render_without_excludes_has_no_delta() -> None:
    report = Report(
        root=Path("/repo"),
        excludes=[],
        files=[_stats("a.py", 100), _stats("b.py", 50)],
    )
    out = _strip(render(report, strip_comments=False))
    assert "Total lines" in out
    assert "150" in out
    assert "% of" not in out
    assert "Done." not in out


def test_render_with_filtered_shows_delta_on_top_rows() -> None:
    kept = [_stats("a.py", 100), _stats("b.py", 50)]
    filtered = [_stats("test_a.py", 30), _stats("test_b.py", 20)]
    report = Report(root=Path("/repo"), excludes=["*test*.py"], files=kept, filtered=filtered)
    out = _strip(render(report, strip_comments=False))

    # baseline = 200, kept = 150, reduction = 25%
    assert "(-25% of 200)" in out
    # Folders baseline is 1 (all files share /repo), no delta when value == baseline
    assert "Folders" in out
    # Python files: 2 of 4 -> -50%
    assert "(-50% of 4)" in out
    # Sub-breakdown rows must NOT carry the annotation
    code_line = next(line for line in out.splitlines() if "code" in line and "Code" not in line)
    assert "% of" not in code_line


def test_render_with_strip_comments_uses_stripped_baseline() -> None:
    kept = [_stats("a.py", 100, comment=10)]
    filtered = [_stats("t.py", 100, comment=10)]
    report = Report(root=Path("/repo"), excludes=["t.py"], files=kept, filtered=filtered)
    out = _strip(render(report, strip_comments=True))

    # Headline: code+docstrings = total - comments. kept=90, baseline=180.
    assert "Code (no comments)" in out
    assert "(-50% of 180)" in out
