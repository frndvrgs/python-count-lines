from __future__ import annotations

from pcl.remote import is_remote_url, normalise_url


def test_detects_https_url() -> None:
    assert is_remote_url("https://github.com/psf/requests")
    assert is_remote_url("https://github.com/psf/requests.git")
    assert is_remote_url("http://example.com/foo/bar.git")


def test_detects_ssh_and_git_urls() -> None:
    assert is_remote_url("git@github.com:psf/requests.git")
    assert is_remote_url("ssh://git@github.com/psf/requests.git")
    assert is_remote_url("git://github.com/psf/requests")


def test_detects_shorthand() -> None:
    assert is_remote_url("github.com/psf/requests")
    assert is_remote_url("gitlab.com/owner/repo")
    assert is_remote_url("bitbucket.org/o/r")


def test_rejects_local_paths() -> None:
    assert not is_remote_url(".")
    assert not is_remote_url("./src")
    assert not is_remote_url("/abs/path")
    assert not is_remote_url("relative/path/file.py")
    assert not is_remote_url("github.com/onlyowner")  # missing repo segment


def test_normalise_shorthand_to_https() -> None:
    assert normalise_url("github.com/psf/requests") == "https://github.com/psf/requests.git"
    assert normalise_url("https://github.com/psf/requests.git") == "https://github.com/psf/requests.git"
    assert normalise_url("git@github.com:psf/requests.git") == "git@github.com:psf/requests.git"
