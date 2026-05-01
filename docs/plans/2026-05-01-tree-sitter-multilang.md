# Tree-sitter Multi-Language Support Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the Python-only `ast`+`tokenize` counter with a tree-sitter-based multi-language counter that supports Python, JavaScript, TypeScript, and Rust with the same accuracy bar (precise comment / docstring / doc-comment / code separation).

**Architecture:** Introduce a `languages/` package where each module declares (a) file extensions, (b) a tree-sitter grammar binding, (c) a node-type → bucket classifier including doc-comment heuristics. `counter.py` becomes language-agnostic: it parses with the right grammar, walks the tree, marks every line covered by `comment` / `docstring` / `string-literal` ranges, then derives `blank` / `code` / `total`. `scanner.py` switches from `iter_python_files` to `iter_source_files` keyed off the registry. CLI and report grow language-aware fields but keep the existing single-totals view as default.

**Tech Stack:** Python 3.11+, `tree-sitter` (Python bindings), prebuilt grammar wheels: `tree-sitter-python`, `tree-sitter-javascript`, `tree-sitter-typescript`, `tree-sitter-rust`. Existing tooling: `uv`, `pytest`, `ruff`, `mypy --strict`.

**Out of scope:** other languages (Go, Java, C, etc.), per-language CLI selection beyond a simple `--lang` filter, syntax highlighting in reports, language auto-detection beyond extension matching.

---

## Conventions

- Run all commands from repo root: `/home/frndvrgs/software/frndvrgs/python-count-lines`.
- Use `uv run pytest -q` for tests, `uv run ruff check .`, `uv run mypy src tests`.
- Commit after every passing task. Conventional Commits format. Never `--no-verify`.
- Touch only the files listed for each task. If a task uncovers new work, stop and flag it; don't expand scope silently.

---

### Task 0: Pin dependencies and verify the toolchain

**Files:**
- Modify: `pyproject.toml`

**Step 1: Add runtime deps**

Edit `pyproject.toml` to add a top-level `[project] dependencies` list (currently absent — only `optional-dependencies.dev` exists). Insert directly after `authors = [...]` on line 10:

```toml
dependencies = [
    "tree-sitter>=0.23.0",
    "tree-sitter-python>=0.23.0",
    "tree-sitter-javascript>=0.23.0",
    "tree-sitter-typescript>=0.23.0",
    "tree-sitter-rust>=0.23.0",
]
```

Rationale for `>=0.23.0`: the 0.23 line is when language packages standardised on the `language()` callable returning a `Language` object directly (vs. the older `tree_sitter_python.language()` returning a capsule that needed wrapping). Pinning lower lets `uv` pick the latest compatible.

**Step 2: Install and probe**

Run: `uv sync --extra dev`
Expected: lockfile updates, all wheels install (no native build).

Run: `uv run python -c "import tree_sitter, tree_sitter_python, tree_sitter_javascript, tree_sitter_typescript, tree_sitter_rust; print('ok')"`
Expected: `ok`

**Step 3: Probe the API for each grammar**

Run:
```
uv run python -c "
import tree_sitter_python, tree_sitter_javascript, tree_sitter_typescript, tree_sitter_rust
from tree_sitter import Language, Parser
for mod, attr in [
    (tree_sitter_python, 'language'),
    (tree_sitter_javascript, 'language'),
    (tree_sitter_typescript, 'language_typescript'),
    (tree_sitter_typescript, 'language_tsx'),
    (tree_sitter_rust, 'language'),
]:
    lang = Language(getattr(mod, attr)())
    p = Parser(lang)
    print(mod.__name__, attr, 'OK')
"
```
Expected: five `OK` lines. If any binding raises (e.g. `language_typescript` is named differently), capture the actual function name and **stop** — record the discrepancy in the task notes and adjust the registry in Task 2 accordingly.

**Step 4: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "build: add tree-sitter and language grammar dependencies"
```

---

### Task 1: Define the language-agnostic data model

**Files:**
- Modify: `src/pcl/counter.py:10-22` — extend `FileStats`
- Test: `tests/test_counter.py` — update existing assertions

**Goal:** Make `FileStats` carry the language tag and rename the docstring bucket to a more general "doc" bucket so JS/Rust doc-comments fit cleanly.

**Step 1: Write the failing test**

Add to `tests/test_counter.py`:

```python
def test_filestats_carries_language_tag() -> None:
    src = "x = 1\n"
    stats = count_source(src)
    assert stats.language == "python"
```

Also rename every existing `stats.docstring` reference in `tests/test_counter.py` to `stats.doc` (the field is being renamed; existing test semantics stay identical for Python).

**Step 2: Run tests to verify the new test fails**

Run: `uv run pytest tests/test_counter.py -q`
Expected: `test_filestats_carries_language_tag` FAILS with `AttributeError: 'FileStats' object has no attribute 'language'`. Other tests fail because `docstring` → `doc` rename hasn't landed in the source yet.

**Step 3: Update `FileStats`**

In `src/pcl/counter.py`, replace the dataclass:

```python
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
```

Update `count_source` to set `language="python"` for now (full multi-language dispatch lands in Task 3). Rename internal variables `docstring_set` → `doc_set` and the keyword in the constructor call.

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_counter.py -q`
Expected: all tests pass.

**Step 5: Update report.py callers**

`src/pcl/report.py:42-43` references `f.docstring` and the row label `"  docstrings"`. Rename to `f.doc` and `"  doc lines"` respectively. Also rename the `Report.docstring` property to `Report.doc`.

Run: `uv run pytest -q && uv run ruff check . && uv run mypy src tests`
Expected: clean.

**Step 6: Commit**

```bash
git add src/pcl/counter.py src/pcl/report.py tests/test_counter.py
git commit -m "refactor: rename docstring bucket to doc and add language tag to FileStats"
```

---

### Task 2: Create the language registry skeleton

**Files:**
- Create: `src/pcl/languages/__init__.py`
- Create: `src/pcl/languages/base.py`
- Create: `src/pcl/languages/registry.py`
- Test: `tests/test_languages_registry.py`

**Goal:** A pure-data registry mapping extensions → language descriptors. No tree-sitter calls yet; that's Task 3.

**Step 1: Write the failing tests**

Create `tests/test_languages_registry.py`:

```python
from __future__ import annotations

from pcl.languages.registry import (
    SUPPORTED_LANGUAGES,
    language_for_path,
    language_for_name,
)


def test_python_extension_maps_to_python() -> None:
    assert language_for_path("foo/bar.py").name == "python"


def test_typescript_extensions_map_to_typescript_or_tsx() -> None:
    assert language_for_path("a.ts").name == "typescript"
    assert language_for_path("a.tsx").name == "tsx"


def test_javascript_extensions() -> None:
    for ext in (".js", ".mjs", ".cjs", ".jsx"):
        assert language_for_path(f"a{ext}").name in {"javascript", "jsx"}


def test_rust_extension() -> None:
    assert language_for_path("a.rs").name == "rust"


def test_unknown_extension_returns_none() -> None:
    assert language_for_path("a.md") is None


def test_language_for_name_lookup() -> None:
    assert language_for_name("python") is not None
    assert language_for_name("nope") is None


def test_supported_languages_listing_is_stable_and_unique() -> None:
    names = [lang.name for lang in SUPPORTED_LANGUAGES]
    assert names == sorted(set(names))
    assert "python" in names
    assert "rust" in names
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_languages_registry.py -q`
Expected: import errors (module doesn't exist).

**Step 3: Implement `base.py`**

Create `src/pcl/languages/base.py`:

```python
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class LanguageSpec:
    """Static description of a supported language.

    `loader` returns a tree-sitter Language at call time so import of this
    module stays cheap (grammars are loaded only when a file is parsed).
    `comment_node_types` and `string_node_types` list AST node kinds whose
    byte-spans cover comment-only and string-literal regions respectively.
    `is_doc_comment` decides whether a comment node is a doc-comment based on
    its source text (e.g. `///` for Rust, `/** ... */` for JSDoc, Python module
    /class/function leading-string detection lives in counter.py because it's
    structural, not textual).
    """

    name: str
    extensions: tuple[str, ...]
    loader: Callable[[], Any]
    comment_node_types: frozenset[str]
    string_node_types: frozenset[str]
    is_doc_comment: Callable[[str], bool]
```

**Step 4: Implement `registry.py` with stub loaders**

Create `src/pcl/languages/registry.py`. Use stub loaders that raise — Task 3 wires real grammars:

```python
from __future__ import annotations

import os
from typing import Any

from pcl.languages.base import LanguageSpec


def _not_yet(name: str) -> Any:
    raise NotImplementedError(f"grammar loader for {name} wired in Task 3")


def _never_doc(_text: str) -> bool:
    return False


PYTHON = LanguageSpec(
    name="python",
    extensions=(".py",),
    loader=lambda: _not_yet("python"),
    comment_node_types=frozenset({"comment"}),
    string_node_types=frozenset({"string"}),
    is_doc_comment=_never_doc,  # Python docs are structural, handled in counter
)

JAVASCRIPT = LanguageSpec(
    name="javascript",
    extensions=(".js", ".mjs", ".cjs"),
    loader=lambda: _not_yet("javascript"),
    comment_node_types=frozenset({"comment"}),
    string_node_types=frozenset({"string", "template_string"}),
    is_doc_comment=lambda text: text.startswith("/**") and not text.startswith("/***"),
)

JSX = LanguageSpec(
    name="jsx",
    extensions=(".jsx",),
    loader=lambda: _not_yet("jsx"),
    comment_node_types=frozenset({"comment"}),
    string_node_types=frozenset({"string", "template_string"}),
    is_doc_comment=lambda text: text.startswith("/**") and not text.startswith("/***"),
)

TYPESCRIPT = LanguageSpec(
    name="typescript",
    extensions=(".ts",),
    loader=lambda: _not_yet("typescript"),
    comment_node_types=frozenset({"comment"}),
    string_node_types=frozenset({"string", "template_string"}),
    is_doc_comment=lambda text: text.startswith("/**") and not text.startswith("/***"),
)

TSX = LanguageSpec(
    name="tsx",
    extensions=(".tsx",),
    loader=lambda: _not_yet("tsx"),
    comment_node_types=frozenset({"comment"}),
    string_node_types=frozenset({"string", "template_string"}),
    is_doc_comment=lambda text: text.startswith("/**") and not text.startswith("/***"),
)


def _rust_is_doc(text: str) -> bool:
    # Outer doc: ///, inner doc: //!, block outer: /** ..., block inner: /*! ...
    # Exclude /// followed by / (////) which is just a regular comment in Rust.
    if text.startswith("////"):
        return False
    if text.startswith("///") or text.startswith("//!"):
        return True
    if text.startswith("/**") and not text.startswith("/***"):
        return True
    if text.startswith("/*!"):
        return True
    return False


RUST = LanguageSpec(
    name="rust",
    extensions=(".rs",),
    loader=lambda: _not_yet("rust"),
    comment_node_types=frozenset({"line_comment", "block_comment"}),
    string_node_types=frozenset({"string_literal", "raw_string_literal"}),
    is_doc_comment=_rust_is_doc,
)


SUPPORTED_LANGUAGES: tuple[LanguageSpec, ...] = (
    JAVASCRIPT,
    JSX,
    PYTHON,
    RUST,
    TSX,
    TYPESCRIPT,
)


_BY_EXT: dict[str, LanguageSpec] = {
    ext: spec for spec in SUPPORTED_LANGUAGES for ext in spec.extensions
}
_BY_NAME: dict[str, LanguageSpec] = {spec.name: spec for spec in SUPPORTED_LANGUAGES}


def language_for_path(path: str | os.PathLike[str]) -> LanguageSpec | None:
    ext = os.path.splitext(os.fspath(path))[1].lower()
    return _BY_EXT.get(ext)


def language_for_name(name: str) -> LanguageSpec | None:
    return _BY_NAME.get(name)
```

Create `src/pcl/languages/__init__.py` (empty file is fine — keeps `pcl.languages` importable).

**Step 5: Run tests**

Run: `uv run pytest tests/test_languages_registry.py -q`
Expected: all pass.

Run: `uv run mypy src tests`
Expected: clean.

**Step 6: Commit**

```bash
git add src/pcl/languages/ tests/test_languages_registry.py
git commit -m "feat: add language registry with extension and name lookup"
```

---

### Task 3: Wire real tree-sitter grammar loaders

**Files:**
- Modify: `src/pcl/languages/registry.py`
- Test: `tests/test_languages_registry.py`

**Step 1: Add a probe test**

Append to `tests/test_languages_registry.py`:

```python
from tree_sitter import Language as TSLanguage


def test_every_language_loads_a_real_grammar() -> None:
    for spec in SUPPORTED_LANGUAGES:
        lang = spec.loader()
        assert isinstance(lang, TSLanguage), f"{spec.name} did not return a Language"
```

**Step 2: Run to verify failure**

Run: `uv run pytest tests/test_languages_registry.py::test_every_language_loads_a_real_grammar -q`
Expected: FAIL with `NotImplementedError: grammar loader for python wired in Task 3`.

**Step 3: Replace the stub loaders**

In `src/pcl/languages/registry.py`, top of file:

```python
import tree_sitter_javascript
import tree_sitter_python
import tree_sitter_rust
import tree_sitter_typescript
from tree_sitter import Language
```

Remove `_not_yet`. Replace each `loader=lambda: _not_yet(...)` with:

- `PYTHON.loader = lambda: Language(tree_sitter_python.language())`
- `JAVASCRIPT.loader = lambda: Language(tree_sitter_javascript.language())`
- `JSX.loader = lambda: Language(tree_sitter_javascript.language())` (same grammar — JSX is a superset handled by the JS grammar)
- `TYPESCRIPT.loader = lambda: Language(tree_sitter_typescript.language_typescript())`
- `TSX.loader = lambda: Language(tree_sitter_typescript.language_tsx())`
- `RUST.loader = lambda: Language(tree_sitter_rust.language())`

If Task 0's probe found different attribute names, use those instead.

**Step 4: Cache grammars**

To avoid reloading on every file, wrap each loader in `functools.cache`:

```python
import functools

@functools.cache
def _python_lang() -> Language: return Language(tree_sitter_python.language())
# ... one per grammar

PYTHON = LanguageSpec(..., loader=_python_lang, ...)
```

**Step 5: Run tests**

Run: `uv run pytest tests/test_languages_registry.py -q`
Expected: all pass, including the new probe.

**Step 6: Commit**

```bash
git add src/pcl/languages/registry.py tests/test_languages_registry.py
git commit -m "feat: wire real tree-sitter grammar loaders with caching"
```

---

### Task 4: Build the tree-sitter-based counter core

**Files:**
- Modify: `src/pcl/counter.py` (significant rewrite)
- Test: `tests/test_counter.py`

**Goal:** Replace `_find_comment_lines` and `_find_docstring_lines` with a generic tree-walker that uses the language spec. Behaviour for Python must remain identical to the existing test suite.

**Step 1: Add a regression test asserting current Python behaviour is unchanged**

Add to `tests/test_counter.py` (existing tests still apply; add an explicit dispatch test):

```python
from pathlib import Path
from pcl.counter import count_source


def test_count_source_explicit_python_language() -> None:
    src = '"""doc."""\nx = 1\n# c\n'
    stats = count_source(src, Path("a.py"))
    assert stats.language == "python"
    assert stats.doc == 1
    assert stats.comment == 1
    assert stats.code == 1
```

**Step 2: Run to confirm the existing suite still passes against the old implementation**

Run: `uv run pytest tests/test_counter.py -q`
Expected: pass (this is the baseline before rewriting).

**Step 3: Rewrite `count_source` to use tree-sitter**

Replace the entire body of `src/pcl/counter.py` below `FileStats` with:

```python
from pcl.languages.base import LanguageSpec
from pcl.languages.registry import language_for_path


def count_file(path: Path) -> FileStats:
    text = path.read_text(encoding="utf-8", errors="replace")
    return count_source(text, path)


def count_source(text: str, path: Path = Path("<string>")) -> FileStats:
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
        path=path, language=language,
        total=total, blank=blank, comment=0, doc=0, code=total - blank,
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
        if node.type in spec.comment_node_types:
            node_text = source[node.start_byte:node.end_byte].decode("utf-8", errors="replace")
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
        path=path, language=spec.name,
        total=total, blank=len(blank_set),
        comment=len(comment_lines), doc=len(doc_lines), code=code,
    )


def _comment_only_lines(node: Any, lines: list[str]) -> Iterable[int]:
    """Yield line numbers (1-based) where the comment node covers the entire
    non-whitespace content of the line."""
    start_row = node.start_point[0]  # 0-based
    end_row = node.end_point[0]
    start_col = node.start_point[1]
    end_col = node.end_point[1]
    for row in range(start_row, end_row + 1):
        if row >= len(lines):
            continue
        line = lines[row]
        if not line.strip():
            continue
        # Determine the comment's span on this row.
        col_lo = start_col if row == start_row else 0
        col_hi = end_col if row == end_row else len(line)
        prefix = line[:col_lo]
        suffix = line[col_hi:]
        if prefix.strip() or suffix.strip():
            # Trailing or leading code present — not a comment-only line.
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
    block = node.child_by_field_name("body")
    if block is None:
        return []
    return [c for c in block.children if c.is_named]
```

Add the necessary imports at the top:

```python
from collections.abc import Iterable
from typing import Any
```

Remove the old `_find_comment_lines` and `_find_docstring_lines` functions and the `ast` / `tokenize` / `io` imports.

**Step 4: Run the full suite**

Run: `uv run pytest -q`
Expected: every existing Python test still passes. If `test_syntax_error_falls_back_to_textual_comment_scan` fails, tree-sitter's `ERROR` recovery should still surface comments — investigate the actual output before patching. The fallback may need adjustment: if tree-sitter's parse drops the `# still a comment line` node on broken input, add a textual fallback for `language="unknown"` only **after** confirming tree-sitter's behaviour, and **stop** to flag the change in expected-coverage before adjusting the test.

Run: `uv run mypy src tests` — expected clean.

**Step 5: Commit**

```bash
git add src/pcl/counter.py tests/test_counter.py
git commit -m "feat: replace ast/tokenize counter with tree-sitter walker"
```

---

### Task 5: Add JavaScript fixture tests

**Files:**
- Test: `tests/test_counter_javascript.py`

**Step 1: Write tests covering the tricky cases**

Create `tests/test_counter_javascript.py`:

```python
from __future__ import annotations

from pathlib import Path
from textwrap import dedent

from pcl.counter import count_source


def js(text: str) -> object:
    return count_source(dedent(text), Path("a.js"))


def test_line_and_block_comments() -> None:
    s = js(
        """\
        // top comment
        const x = 1; // trailing
        /* block
           comment */
        const y = 2;
        """
    )
    assert s.language == "javascript"
    assert s.comment == 3  # // top, /* block, comment */
    assert s.code == 2     # both const lines
    assert s.doc == 0


def test_jsdoc_recognised_as_doc() -> None:
    s = js(
        """\
        /**
         * Adds two numbers.
         * @param {number} a
         */
        function add(a, b) { return a + b; }
        """
    )
    assert s.doc == 4
    assert s.comment == 0
    assert s.code == 1


def test_string_with_slash_slash_is_not_a_comment() -> None:
    s = js('const url = "http://example.com";\n')
    assert s.comment == 0
    assert s.code == 1


def test_template_literal_is_code() -> None:
    s = js("const x = `hello\nworld`;\n")
    assert s.code == 2
    assert s.comment == 0


def test_regex_literal_with_slash_is_not_a_comment() -> None:
    s = js("const r = /\\/\\//g;\n")
    assert s.comment == 0
    assert s.code == 1
```

**Step 2: Run**

Run: `uv run pytest tests/test_counter_javascript.py -q`
Expected: pass. If `test_line_and_block_comments` reports `comment == 2` instead of 3, tree-sitter is treating the multi-line block as a single comment node spanning two lines — that's already correctly counted by `_comment_only_lines` as 2 lines (start row + end row). Update the assertion to `s.comment == 3` only if the block comment really spans 2 lines plus the `// top` line. Re-derive the expected value from the input before changing source code.

**Step 3: Commit**

```bash
git add tests/test_counter_javascript.py
git commit -m "test: add javascript counter fixtures for comments, jsdoc, strings"
```

---

### Task 6: Add TypeScript fixture tests

**Files:**
- Test: `tests/test_counter_typescript.py`

**Step 1: Write the tests**

```python
from __future__ import annotations

from pathlib import Path
from textwrap import dedent

from pcl.counter import count_source


def ts(text: str, suffix: str = ".ts") -> object:
    return count_source(dedent(text), Path(f"a{suffix}"))


def test_typescript_basic() -> None:
    s = ts(
        """\
        // header
        export const x: number = 1;
        """
    )
    assert s.language == "typescript"
    assert s.comment == 1
    assert s.code == 1


def test_tsx_dispatches_to_tsx_grammar() -> None:
    s = ts(
        """\
        // header
        export const E = () => <div>hi</div>;
        """,
        suffix=".tsx",
    )
    assert s.language == "tsx"
    assert s.comment == 1
    assert s.code == 1


def test_jsdoc_in_typescript() -> None:
    s = ts(
        """\
        /** doc */
        export function f(): void {}
        """
    )
    assert s.doc == 1
    assert s.code == 1
```

**Step 2: Run**

Run: `uv run pytest tests/test_counter_typescript.py -q`
Expected: pass.

**Step 3: Commit**

```bash
git add tests/test_counter_typescript.py
git commit -m "test: add typescript and tsx counter fixtures"
```

---

### Task 7: Add Rust fixture tests

**Files:**
- Test: `tests/test_counter_rust.py`

**Step 1: Write the tests covering Rust's edge cases**

```python
from __future__ import annotations

from pathlib import Path
from textwrap import dedent

from pcl.counter import count_source


def rs(text: str) -> object:
    return count_source(dedent(text), Path("a.rs"))


def test_line_comments_and_doc_comments() -> None:
    s = rs(
        """\
        // regular
        /// outer doc
        //! inner doc
        //// quadruple is regular comment
        fn main() {}
        """
    )
    assert s.language == "rust"
    assert s.doc == 2          # ///, //!
    assert s.comment == 2      # //, ////
    assert s.code == 1


def test_block_doc_comments() -> None:
    s = rs(
        """\
        /** outer block doc
            line two */
        /*! inner block doc */
        fn main() {}
        """
    )
    assert s.doc == 3          # 2 lines + 1 line
    assert s.code == 1


def test_nested_block_comments_are_a_single_comment_span() -> None:
    s = rs(
        """\
        /* outer /* nested */ still outer */
        fn main() {}
        """
    )
    # Rust grammar treats the whole thing as one block_comment.
    assert s.comment == 1
    assert s.code == 1


def test_raw_string_with_slashes_is_not_a_comment() -> None:
    s = rs(
        """\
        fn main() {
            let s = r#"// not a comment"#;
        }
        """
    )
    assert s.comment == 0
    assert s.code == 3
```

**Step 2: Run**

Run: `uv run pytest tests/test_counter_rust.py -q`
Expected: pass. If the doc-comment classifier flags `////` as doc, fix `_rust_is_doc` in `registry.py` (Task 2 included the guard, but verify the order of `startswith` checks — `////` must short-circuit before `///`).

**Step 3: Commit**

```bash
git add tests/test_counter_rust.py
git commit -m "test: add rust counter fixtures for line, doc, block, raw-string"
```

---

### Task 8: Generalise the file scanner

**Files:**
- Modify: `src/pcl/scanner.py`
- Test: `tests/test_scanner.py`

**Goal:** Replace `iter_python_files` with `iter_source_files(root, languages, excludes)` where `languages` is a set of language names; default = all supported. Keep `is_excluded` unchanged.

**Step 1: Update tests first**

Edit `tests/test_scanner.py`. Change the import to:

```python
from pcl.scanner import is_excluded, iter_source_files
```

Replace `test_iter_python_files_walks_and_excludes` and `test_iter_python_files_handles_single_file` with multi-language equivalents:

```python
def test_iter_source_files_finds_multiple_languages(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("x = 1\n")
    (tmp_path / "src" / "main.rs").write_text("fn main() {}\n")
    (tmp_path / "src" / "ui.tsx").write_text("export const X = () => null;\n")
    (tmp_path / "README.md").write_text("# not source\n")

    found = sorted(p.name for p in iter_source_files(tmp_path, languages=None, excludes=[]))
    assert found == ["app.py", "main.rs", "ui.tsx"]


def test_iter_source_files_filters_by_language(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("x = 1\n")
    (tmp_path / "a.rs").write_text("fn main(){}\n")

    found = sorted(p.name for p in iter_source_files(tmp_path, languages={"python"}, excludes=[]))
    assert found == ["a.py"]


def test_iter_source_files_handles_single_file(tmp_path: Path) -> None:
    f = tmp_path / "solo.py"
    f.write_text("x = 1\n")
    assert list(iter_source_files(f, languages=None, excludes=[])) == [f.resolve()]


def test_iter_source_files_skips_unsupported_extensions(tmp_path: Path) -> None:
    (tmp_path / "a.go").write_text("package main\n")
    assert list(iter_source_files(tmp_path, languages=None, excludes=[])) == []
```

**Step 2: Run to verify failures**

Run: `uv run pytest tests/test_scanner.py -q`
Expected: import error.

**Step 3: Implement `iter_source_files`**

In `src/pcl/scanner.py`, replace `iter_python_files` with:

```python
from pcl.languages.registry import SUPPORTED_LANGUAGES, language_for_path


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
        else {ext for spec in SUPPORTED_LANGUAGES if spec.name in languages for ext in spec.extensions}
    )

    root = root.resolve()
    if root.is_file():
        if root.suffix.lower() in selected:
            yield root
        return

    for current_dir, dirs, files in os.walk(root):
        current = Path(current_dir)
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
```

Keep `is_excluded` and `DEFAULT_SKIP_DIRS` exactly as they are. Delete `iter_python_files`.

**Step 4: Run**

Run: `uv run pytest tests/test_scanner.py -q`
Expected: pass.

Run: `uv run mypy src tests` — clean.

**Step 5: Commit**

```bash
git add src/pcl/scanner.py tests/test_scanner.py
git commit -m "feat: generalise scanner to walk all supported languages"
```

---

### Task 9: Update the CLI

**Files:**
- Modify: `src/pcl/cli.py`

**Step 1: Add `--lang` flag and switch to `iter_source_files`**

In `src/pcl/cli.py`:

- Replace `from pcl.scanner import is_excluded, iter_python_files` with `from pcl.scanner import is_excluded, iter_source_files` and `from pcl.languages.registry import SUPPORTED_LANGUAGES`.
- Add an argument:

```python
parser.add_argument(
    "--lang",
    nargs="+",
    default=None,
    metavar="NAME",
    choices=[spec.name for spec in SUPPORTED_LANGUAGES],
    help="languages to include (default: all supported)",
)
```

- Update the description: change `"Count lines of code in a Python project (...)"` to `"Count lines of code across multiple languages (Python, JS/TS, Rust). Local path or remote git URL."`.

- Update `_scan_and_render` signature to accept `languages: set[str] | None` and pass it through to `iter_source_files(root, languages=languages, excludes=[])`.

- In `main`, convert `args.lang` (list or None) to a set and pass it down.

**Step 2: Smoke-test the CLI**

Run: `uv run pcl src --lang python -q || true` (a quick visual check; non-zero exit is fine if implementation is half-done — we're just checking it doesn't crash on argparse).

Run: `uv run pytest -q`
Expected: full suite still passes (no test changes, just CLI wiring).

Run: `uv run mypy src tests` — clean.

**Step 3: Commit**

```bash
git add src/pcl/cli.py
git commit -m "feat: add --lang filter and wire CLI through multi-language scanner"
```

---

### Task 10: Update the report header and labels

**Files:**
- Modify: `src/pcl/report.py`
- Test: `tests/test_report.py`

**Step 1: Read current report tests to understand assertions**

Run: `uv run cat tests/test_report.py` (or use Read tool in IDE).
Identify any string assertions on `"Python files"` or `"docstrings"` — those need updating.

**Step 2: Replace fixed Python-only labels**

In `src/pcl/report.py`:

- Change `"No Python files found."` → `"No source files found."`
- Change `"Python files"` row label → `"Source files"`
- Add a new row showing per-language file counts. Insert before the headline rows:

```python
lang_counts: dict[str, int] = {}
for f in report.files:
    lang_counts[f.language] = lang_counts.get(f.language, 0) + 1
```

Then below `"Source files"`, add one indented row per language (sorted by count desc, then name):

```python
for lang in sorted(lang_counts, key=lambda n: (-lang_counts[n], n)):
    rows.append((f"  {lang}", lang_counts[lang], DIM, None))
```

- Update the program-name banner line `"python-count-lines"` to `"count-lines"` to reflect the wider scope.

**Step 3: Update `tests/test_report.py`**

Adjust string assertions to match new labels. Add one test:

```python
def test_report_shows_per_language_counts() -> None:
    # Given a Report with mixed-language FileStats, the rendered output
    # contains a row for each language with its count.
    ...
```

(Fill in concrete fixtures based on what the existing test file uses.)

**Step 4: Run full suite**

Run: `uv run pytest -q`
Expected: pass.

Run: `uv run ruff check . && uv run mypy src tests` — clean.

**Step 5: Commit**

```bash
git add src/pcl/report.py tests/test_report.py
git commit -m "feat: report per-language file counts and generalise labels"
```

---

### Task 11: Refresh README and CHANGELOG

**Files:**
- Modify: `README.md`
- Modify: `CHANGELOG.md`

**Step 1: README**

Update the README to:
- State the new supported languages.
- Show example output with multiple languages.
- Document the `--lang` flag.
- Note that doc-comments (`///`, `//!`, JSDoc, Python docstrings) are bucketed separately as "doc lines".

**Step 2: CHANGELOG**

Add an entry under `## [Unreleased]` (create the section if absent):

```
### Added
- Tree-sitter-based parsing for Python, JavaScript, JSX, TypeScript, TSX, Rust.
- `--lang` flag to filter which languages to count.
- Per-language file counts in the report.

### Changed
- Renamed the `docstring` bucket to `doc` (covers Python docstrings, JSDoc, Rust ///, //!, /** */, /*! */).
- Renamed the program label from `python-count-lines` to `count-lines`.
- Counter no longer depends on Python `ast`/`tokenize` for accuracy; uses tree-sitter grammars.

### Removed
- `iter_python_files` (replaced by `iter_source_files`).
```

**Step 3: Commit**

```bash
git add README.md CHANGELOG.md
git commit -m "docs: document multi-language support and --lang flag"
```

---

### Task 12: End-to-end verification

**Step 1: Run the full quality gate**

Run: `uv run pytest -q && uv run ruff check . && uv run mypy src tests`
Expected: all green.

**Step 2: Real-world smoke**

Pick a small public repo with mixed languages (e.g. a TS+Rust project from the user's local checkouts) and run:
`uv run pcl /path/to/repo`
Confirm the per-language counts look plausible (ratios match `git ls-files | awk -F. '{print $NF}' | sort | uniq -c`).

**Step 3: Final commit if tweaks needed**

If smoke testing surfaces a real bug, fix it as a separate commit referencing the symptom. Don't squash into earlier commits — the trail matters for review.

---

## Risks & Open Questions

1. **`tree_sitter_typescript` API name** — Task 0 verifies. If wrong, Task 3's TS/TSX loaders need the actual attribute name.
2. **Tree-sitter ERROR recovery on broken Python** — the existing `test_syntax_error_falls_back_to_textual_comment_scan` may need its expectation refined (Task 4, Step 4 flags this).
3. **JSX comment classification** — JSX comment syntax inside markup (`{/* ... */}`) parses as expressions wrapping a `comment` node; the walker should still pick them up because `comment_node_types` is `{"comment"}` and the walk visits all descendants. If a fixture surfaces a miss, add a JSX-specific fixture in Task 5.
4. **Performance** — tree-sitter is fast (~MB/s), but parsing every file is more work than the current line-level regex would be. If the user reports a slowdown on large repos, parallelising with `concurrent.futures.ProcessPoolExecutor` is the obvious next step (out of scope here).
5. **Rust nested block comments** — verified by Task 7's fixture; the grammar handles it natively.
