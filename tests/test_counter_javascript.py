from __future__ import annotations

from pathlib import Path
from textwrap import dedent

from pcl.counter import FileStats, count_source


def js(text: str) -> FileStats:
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
