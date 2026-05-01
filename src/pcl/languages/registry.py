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
