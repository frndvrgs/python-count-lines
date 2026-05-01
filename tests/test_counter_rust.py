from __future__ import annotations

from pathlib import Path
from textwrap import dedent

from pcl.counter import FileStats, count_source


def rs(text: str) -> FileStats:
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
