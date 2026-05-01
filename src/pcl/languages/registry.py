from __future__ import annotations

import functools
import os

import tree_sitter_javascript
import tree_sitter_python
import tree_sitter_rust
import tree_sitter_typescript
from tree_sitter import Language

from pcl.languages.base import LanguageSpec


@functools.cache
def _python_lang() -> Language:
    return Language(tree_sitter_python.language())


@functools.cache
def _javascript_lang() -> Language:
    return Language(tree_sitter_javascript.language())


@functools.cache
def _typescript_lang() -> Language:
    return Language(tree_sitter_typescript.language_typescript())


@functools.cache
def _tsx_lang() -> Language:
    return Language(tree_sitter_typescript.language_tsx())


@functools.cache
def _rust_lang() -> Language:
    return Language(tree_sitter_rust.language())


def _never_doc(_text: str) -> bool:
    return False


PYTHON = LanguageSpec(
    name="python",
    extensions=(".py",),
    loader=_python_lang,
    comment_node_types=frozenset({"comment"}),
    string_node_types=frozenset({"string"}),
    is_doc_comment=_never_doc,  # Python docs are structural, handled in counter
)

JAVASCRIPT = LanguageSpec(
    name="javascript",
    extensions=(".js", ".mjs", ".cjs"),
    loader=_javascript_lang,
    comment_node_types=frozenset({"comment"}),
    string_node_types=frozenset({"string", "template_string"}),
    is_doc_comment=lambda text: text.startswith("/**") and not text.startswith("/***"),
)

JSX = LanguageSpec(
    name="jsx",
    extensions=(".jsx",),
    # JSX is a superset handled by the JS grammar; share the cached Language.
    loader=_javascript_lang,
    comment_node_types=frozenset({"comment"}),
    string_node_types=frozenset({"string", "template_string"}),
    is_doc_comment=lambda text: text.startswith("/**") and not text.startswith("/***"),
)

TYPESCRIPT = LanguageSpec(
    name="typescript",
    extensions=(".ts",),
    loader=_typescript_lang,
    comment_node_types=frozenset({"comment"}),
    string_node_types=frozenset({"string", "template_string"}),
    is_doc_comment=lambda text: text.startswith("/**") and not text.startswith("/***"),
)

TSX = LanguageSpec(
    name="tsx",
    extensions=(".tsx",),
    loader=_tsx_lang,
    comment_node_types=frozenset({"comment"}),
    string_node_types=frozenset({"string", "template_string"}),
    is_doc_comment=lambda text: text.startswith("/**") and not text.startswith("/***"),
)


def _rust_is_doc(text: str) -> bool:
    # ORDER MATTERS: //// must be checked before /// (else Rust's regular
    # //// comments would be misclassified as doc comments). Likewise /***
    # must be excluded before /** to avoid 3-star banner comments being
    # treated as JSDoc.
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
    loader=_rust_lang,
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
