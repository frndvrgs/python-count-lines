from __future__ import annotations

import ast
import io
import tokenize
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class FileStats:
    path: Path
    language: str
    total: int
    blank: int
    comment: int
    doc: int
    code: int

    @property
    def stripped(self) -> int:
        """Total minus comment-only lines (kept doc lines — they're real source)."""
        return self.total - self.comment


def count_file(path: Path) -> FileStats:
    text = path.read_text(encoding="utf-8", errors="replace")
    return count_source(text, path)


def count_source(text: str, path: Path = Path("<string>")) -> FileStats:
    lines = text.splitlines()
    total = len(lines)
    blank_set = {i for i, line in enumerate(lines, 1) if not line.strip()}

    comment_set = _find_comment_lines(text, lines)
    doc_set = _find_docstring_lines(text)

    # Resolve overlaps: comment > doc > blank > code.
    # Blank lines inside a multi-line docstring count as doc (they're doc content).
    doc_set -= comment_set
    blank_set -= comment_set | doc_set
    code = total - len(blank_set) - len(comment_set) - len(doc_set)

    return FileStats(
        path=path,
        language="python",
        total=total,
        blank=len(blank_set),
        comment=len(comment_set),
        doc=len(doc_set),
        code=code,
    )


def _find_comment_lines(text: str, lines: list[str]) -> set[int]:
    """Return line numbers (1-based) that are comment-only.

    A comment-only line is one whose non-whitespace content begins with '#'.
    Lines with code followed by a trailing '# comment' are NOT counted here —
    they remain code lines.
    """
    result: set[int] = set()
    try:
        for tok in tokenize.generate_tokens(io.StringIO(text).readline):
            if tok.type != tokenize.COMMENT:
                continue
            line_no = tok.start[0]
            if 1 <= line_no <= len(lines) and lines[line_no - 1].lstrip().startswith("#"):
                result.add(line_no)
    except (tokenize.TokenError, IndentationError, SyntaxError):
        # Fallback for files tokenize can't parse: scan textually.
        for i, line in enumerate(lines, 1):
            if line.lstrip().startswith("#"):
                result.add(i)
    return result


def _find_docstring_lines(text: str) -> set[int]:
    """Return line numbers occupied by module/class/function docstrings."""
    result: set[int] = set()
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return result

    targets = (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
    for node in ast.walk(tree):
        if not isinstance(node, targets) or not node.body:
            continue
        first = node.body[0]
        if not isinstance(first, ast.Expr):
            continue
        value = first.value
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            start = first.lineno
            end = first.end_lineno or start
            result.update(range(start, end + 1))
    return result
