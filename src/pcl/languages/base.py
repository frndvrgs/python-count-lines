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
