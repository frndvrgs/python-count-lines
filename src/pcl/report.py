from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from pcl.counter import FileStats
from pcl.styles import BOLD, CYAN, DIM, RESET, YELLOW

TOP_FILES_LIMIT = 5


@dataclass(slots=True)
class Report:
    root: Path
    excludes: list[str]
    files: list[FileStats] = field(default_factory=list)
    filtered: list[FileStats] = field(default_factory=list)
    display_root: str | None = None

    @property
    def folder_count(self) -> int:
        return len({f.path.parent for f in self.files})

    @property
    def file_count(self) -> int:
        return len(self.files)

    @property
    def total(self) -> int:
        return sum(f.total for f in self.files)

    @property
    def blank(self) -> int:
        return sum(f.blank for f in self.files)

    @property
    def comment(self) -> int:
        return sum(f.comment for f in self.files)

    @property
    def docstring(self) -> int:
        return sum(f.docstring for f in self.files)

    @property
    def code(self) -> int:
        return sum(f.code for f in self.files)

    @property
    def baseline_folders(self) -> int:
        return len({f.path.parent for f in (*self.files, *self.filtered)})

    @property
    def baseline_files(self) -> int:
        return len(self.files) + len(self.filtered)

    @property
    def baseline_total(self) -> int:
        return sum(f.total for f in (*self.files, *self.filtered))

    @property
    def baseline_comment(self) -> int:
        return sum(f.comment for f in (*self.files, *self.filtered))


def render(report: Report, *, strip_comments: bool) -> str:
    out: list[str] = []
    p = out.append

    p(f"\n{BOLD}python-count-lines{RESET}")
    label = "Source:" if report.display_root else "Path:"
    p(f"  {DIM}{label:<9}{RESET}{report.display_root or report.root}")
    if report.excludes:
        p(f"  {DIM}Excludes:{RESET} {', '.join(report.excludes)}")

    if not report.files:
        p(f"\n  {YELLOW}No Python files found.{RESET}\n")
        return "\n".join(out) + "\n"

    headline_label = "Code (no comments)" if strip_comments else "Total lines"
    headline_value = (report.total - report.comment) if strip_comments else report.total
    headline_baseline = (
        (report.baseline_total - report.baseline_comment) if strip_comments else report.baseline_total
    )

    show_delta = bool(report.filtered)

    # (label, value, style, baseline-or-None). Sub-breakdown rows have no baseline annotation.
    rows: list[tuple[str, int, str, int | None]] = [
        ("Folders", report.folder_count, "", report.baseline_folders if show_delta else None),
        ("Python files", report.file_count, "", report.baseline_files if show_delta else None),
        (headline_label, headline_value, BOLD, headline_baseline if show_delta else None),
        ("  code", report.code, DIM, None),
        ("  docstrings", report.docstring, DIM, None),
        ("  comments", report.comment, DIM, None),
        ("  blank", report.blank, DIM, None),
    ]

    label_w = max(len(lbl) for lbl, _, _, _ in rows) + 2
    value_w = max(len(f"{val:,}") for _, val, _, _ in rows)

    p("")
    for lbl, value, style, baseline in rows:
        core = f"  {lbl:<{label_w}}{value:>{value_w},}"
        styled = f"{style}{core}{RESET}" if style else core
        annotation = _delta(value, baseline)
        p(styled + annotation)

    if report.file_count > 1:
        top = sorted(report.files, key=lambda f: f.total, reverse=True)[:TOP_FILES_LIMIT]
        p(f"\n  {DIM}Top {len(top)} largest files{RESET}")
        path_w = max(len(_relpath(f.path, report.root)) for f in top)
        for f in top:
            rel = _relpath(f.path, report.root)
            p(f"  {CYAN}{rel:<{path_w}}{RESET}  {f.total:>{value_w},}")

    p("")
    return "\n".join(out) + "\n"


def _delta(value: int, baseline: int | None) -> str:
    if baseline is None or baseline <= 0 or baseline == value:
        return ""
    pct = round((baseline - value) / baseline * 100)
    return f" {DIM}(-{pct}% of {baseline:,}){RESET}"


def _relpath(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)
