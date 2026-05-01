from __future__ import annotations

from pathlib import Path
from textwrap import dedent

from pcl.counter import FileStats, count_source


def ts(text: str, suffix: str = ".ts") -> FileStats:
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
