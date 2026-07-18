from __future__ import annotations

import argparse
import sys
from importlib.metadata import version
from pathlib import Path

from pcl.counter import count_file
from pcl.languages.registry import SUPPORTED_LANGUAGES
from pcl.remote import is_remote_url, materialise_remote
from pcl.report import Report, render
from pcl.scanner import is_excluded, iter_source_files
from pcl.styles import DIM, RESET


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="pcl",
        description=(
            "Count lines of code across multiple languages (Python, JS/TS, Rust). "
            "Local path or remote git URL."
        ),
    )
    parser.add_argument(
        "-v", "--version",
        action="version",
        version=f"pcl {version('python-count-lines')}",
    )
    parser.add_argument(
        "target",
        nargs="?",
        default=".",
        help="folder, file, or git URL (https://, git@, github.com/owner/repo); defaults to '.'",
    )
    parser.add_argument(
        "--exclude",
        nargs="+",
        default=[],
        metavar="PATTERN",
        help="paths or fnmatch patterns to skip (matched against full relpath and each component)",
    )
    parser.add_argument(
        "--strip-comments",
        action="store_true",
        help="exclude comment-only lines from the headline LOC total",
    )
    parser.add_argument(
        "--lang",
        nargs="+",
        default=None,
        metavar="NAME",
        choices=[spec.name for spec in SUPPORTED_LANGUAGES],
        help="languages to include (default: all supported)",
    )
    args = parser.parse_args()

    languages = set(args.lang) if args.lang else None

    if is_remote_url(args.target):
        try:
            with materialise_remote(args.target) as cloned:
                sys.stderr.write(f"{DIM}Cloning {args.target}...{RESET}\n")
                _scan_and_render(
                    cloned,
                    args.exclude,
                    args.strip_comments,
                    languages=languages,
                    display=args.target,
                )
        except RuntimeError as exc:
            sys.stderr.write(f"pcl: {exc}\n")
            sys.exit(1)
    else:
        root = Path(args.target).expanduser().resolve()
        if not root.exists():
            parser.error(f"path not found: {root}")
        _scan_and_render(root, args.exclude, args.strip_comments, languages=languages)

    sys.exit(0)


def _scan_and_render(
    root: Path,
    excludes: list[str],
    strip_comments: bool,
    *,
    languages: set[str] | None,
    display: str | None = None,
) -> None:
    # Walk once with defaults-only; partition by user patterns afterwards
    # so the report can show how much the excludes filtered out.
    report = Report(root=root, excludes=list(excludes), display_root=display)
    for fp in iter_source_files(root, languages=languages, excludes=[]):
        try:
            stats = count_file(fp)
        except OSError:
            # Vanished between walk and read, permission-denied, or an unresolvable
            # link — one unreadable file must not abort the whole scan.
            continue
        if excludes and is_excluded(fp.relative_to(root), excludes):
            report.filtered.append(stats)
        else:
            report.files.append(stats)
    sys.stdout.write(render(report, strip_comments=strip_comments))
