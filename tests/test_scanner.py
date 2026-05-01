from __future__ import annotations

from pathlib import Path

from pcl.scanner import is_excluded, iter_python_files


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


def test_iter_python_files_walks_and_excludes(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("x = 1\n")
    (tmp_path / "src" / "lib.py").write_text("y = 2\n")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_app.py").write_text("z = 3\n")
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "ignored.py").write_text("ignored\n")
    (tmp_path / "README.md").write_text("# not python\n")

    found_default = sorted(p.name for p in iter_python_files(tmp_path, []))
    assert found_default == ["app.py", "lib.py", "test_app.py"]

    found_excl = sorted(p.name for p in iter_python_files(tmp_path, ["tests"]))
    assert found_excl == ["app.py", "lib.py"]


def test_iter_python_files_handles_single_file(tmp_path: Path) -> None:
    f = tmp_path / "solo.py"
    f.write_text("x = 1\n")
    assert list(iter_python_files(f, [])) == [f.resolve()]
