from __future__ import annotations

from textwrap import dedent

from pcl.counter import count_source


def test_blank_comment_code_split() -> None:
    src = dedent(
        """\
        # top-level comment
        x = 1
        y = 2  # trailing comment, still code

        # another comment
        z = x + y
        """
    )
    stats = count_source(src)
    assert stats.total == 6
    assert stats.blank == 1
    assert stats.comment == 2
    assert stats.docstring == 0
    assert stats.code == 3


def test_module_and_function_docstrings() -> None:
    src = dedent(
        '''\
        """Module docstring.

        Spanning multiple lines.
        """

        def f() -> int:
            """One-liner."""
            return 1
        '''
    )
    stats = count_source(src)
    # Module docstring: 4 lines (line 1-4). Function docstring: 1 line.
    assert stats.docstring == 5
    assert stats.comment == 0
    # blank line between docstring and def
    assert stats.blank == 1
    # def f() and return 1 = 2 code lines
    assert stats.code == 2


def test_inline_comment_does_not_count_as_comment_line() -> None:
    src = "x = 1  # inline\n"
    stats = count_source(src)
    assert stats.comment == 0
    assert stats.code == 1


def test_stripped_excludes_comment_only_lines() -> None:
    src = dedent(
        """\
        # comment
        x = 1
        """
    )
    stats = count_source(src)
    assert stats.total == 2
    assert stats.stripped == 1


def test_syntax_error_falls_back_to_textual_comment_scan() -> None:
    # Not parseable as Python, but lines starting with # are still comments.
    src = "def broken(:\n    # still a comment line\n    pass\n"
    stats = count_source(src)
    assert stats.comment >= 1
