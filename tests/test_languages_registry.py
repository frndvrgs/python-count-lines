from __future__ import annotations

from tree_sitter import Language as TSLanguage

from pcl.languages.registry import (
    SUPPORTED_LANGUAGES,
    language_for_name,
    language_for_path,
)


def test_python_extension_maps_to_python() -> None:
    spec = language_for_path("foo/bar.py")
    assert spec is not None
    assert spec.name == "python"


def test_typescript_extensions_map_to_typescript_or_tsx() -> None:
    ts = language_for_path("a.ts")
    tsx = language_for_path("a.tsx")
    assert ts is not None and ts.name == "typescript"
    assert tsx is not None and tsx.name == "tsx"


def test_javascript_extensions() -> None:
    for ext in (".js", ".mjs", ".cjs", ".jsx"):
        spec = language_for_path(f"a{ext}")
        assert spec is not None
        assert spec.name in {"javascript", "jsx"}


def test_rust_extension() -> None:
    spec = language_for_path("a.rs")
    assert spec is not None
    assert spec.name == "rust"


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


def test_every_language_loads_a_real_grammar() -> None:
    for spec in SUPPORTED_LANGUAGES:
        lang = spec.loader()
        assert isinstance(lang, TSLanguage), f"{spec.name} did not return a Language"
