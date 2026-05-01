from __future__ import annotations

from pathlib import Path

from pcl.scanner import is_excluded, iter_source_files


def test_default_skips_hidden_and_pycache() -> None:
    assert is_excluded(Path(".venv/foo.py"), [])
    assert is_excluded(Path("src/__pycache__/x.py"), [])
    assert not is_excluded(Path("src/app.py"), [])


def test_user_pattern_matches_component() -> None:
    assert is_excluded(Path("a/tests/b.py"), ["tests"])
    assert is_excluded(Path("tests/b.py"), ["tests"])
    assert not is_excluded(Path("a/b.py"), ["tests"])


def test_user_pattern_matches_glob_against_full_path() -> None:
    assert is_excluded(Path("src/migrations/0001.py"), ["src/migrations/*"])
    assert not is_excluded(Path("src/app.py"), ["src/migrations/*"])


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
