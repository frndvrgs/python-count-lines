from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pcl.languages.base import LanguageSpec
from pcl.languages.registry import language_for_path


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
        """Total minus comment-only lines.

        Doc lines (Python docstrings, JSDoc, Rust ///, //!) are kept — they're
        intentional API documentation, not noise.
        """
        return self.total - self.comment


def count_file(path: Path) -> FileStats:
    text = path.read_text(encoding="utf-8", errors="replace")
    return count_source(text, path)


def count_source(text: str, path: Path = Path("<string>.py")) -> FileStats:
    spec = language_for_path(path)
    if spec is None:
        # Unknown extension — count blank/code only, no comment parsing.
        return _count_plain(text, path, language="unknown")
    return _count_with_grammar(text, path, spec)


def _count_plain(text: str, path: Path, *, language: str) -> FileStats:
    lines = text.splitlines()
    total = len(lines)
    blank = sum(1 for line in lines if not line.strip())
    return FileStats(
        path=path,
        language=language,
        total=total,
        blank=blank,
        comment=0,
        doc=0,
        code=total - blank,
    )


def _count_with_grammar(text: str, path: Path, spec: LanguageSpec) -> FileStats:
    from tree_sitter import Parser  # local import to keep cold-start cheap

    source = text.encode("utf-8")
    parser = Parser(spec.loader())
    tree = parser.parse(source)

    lines = text.splitlines()
    total = len(lines)

    comment_lines: set[int] = set()
    doc_lines: set[int] = set()

    # Walk the tree once collecting comment ranges.
    cursor = tree.walk()
    visited_children = False
    while True:
        node = cursor.node
        if (
            not visited_children
            and node is not None
            and node.type in spec.comment_node_types
        ):
            node_text = source[node.start_byte : node.end_byte].decode(
                "utf-8", errors="replace"
            )
            target = doc_lines if spec.is_doc_comment(node_text) else comment_lines
            # Only count lines whose non-whitespace content lies inside the
            # node — a `code  // trailing` line should remain code.
            for line_no in _comment_only_lines(node, lines):
                target.add(line_no)
        if not visited_children and cursor.goto_first_child():
            continue
        if cursor.goto_next_sibling():
            visited_children = False
            continue
        if not cursor.goto_parent():
            break
        visited_children = True

    # Python-specific: structural docstrings (first string-expression in
    # module/function/class body) become doc lines.
    if spec.name == "python":
        doc_lines |= _python_docstring_lines(tree.root_node)

    # Resolve overlap precedence: comment > doc > blank > code.
    blank_set = {i for i, line in enumerate(lines, 1) if not line.strip()}
    doc_lines -= comment_lines
    blank_set -= comment_lines | doc_lines
    code = total - len(blank_set) - len(comment_lines) - len(doc_lines)

    return FileStats(
        path=path,
        language=spec.name,
        total=total,
        blank=len(blank_set),
        comment=len(comment_lines),
        doc=len(doc_lines),
        code=code,
    )


def _comment_only_lines(node: Any, lines: list[str]) -> Iterable[int]:
    """Yield line numbers (1-based) where the comment node covers the entire
    non-whitespace content of the line.

    Tree-sitter reports start_point/end_point columns as byte offsets, so we
    slice in bytes to stay correct on multi-byte UTF-8 source, then decode
    back to str for the whitespace check (str.strip strips Unicode whitespace
    such as NBSP, matching the blank-line semantics elsewhere in this module).
    """
    start_row, start_col = node.start_point
    end_row, end_col = node.end_point
    for row in range(start_row, end_row + 1):
        if row >= len(lines):
            continue
        line_bytes = lines[row].encode("utf-8")
        if not line_bytes.decode("utf-8", errors="replace").strip():
            continue
        col_lo = start_col if row == start_row else 0
        col_hi = end_col if row == end_row else len(line_bytes)
        prefix = line_bytes[:col_lo].decode("utf-8", errors="replace")
        suffix = line_bytes[col_hi:].decode("utf-8", errors="replace")
        if prefix.strip() or suffix.strip():
            continue
        yield row + 1


def _python_docstring_lines(root: Any) -> set[int]:
    """Walk the tree-sitter parse for module/class/function bodies whose first
    statement is a bare string expression."""
    result: set[int] = set()
    targets = {"module", "function_definition", "class_definition"}
    stack = [root]
    while stack:
        node = stack.pop()
        if node.type in targets:
            body = _python_body(node)
            if body and body[0].type == "expression_statement":
                expr = body[0]
                if expr.child_count == 1 and expr.children[0].type == "string":
                    s, e = expr.start_point[0], expr.end_point[0]
                    result.update(range(s + 1, e + 2))  # 1-based, inclusive
        stack.extend(node.children)
    return result


def _python_body(node: Any) -> list[Any]:
    # `module` has no "body" field — its named children ARE the body.
    if node.type == "module":
        return [c for c in node.children if c.is_named]
    block = node.child_by_field_name("body")
    if block is None:
        return []
    return [c for c in block.children if c.is_named]
