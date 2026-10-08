"""The API key must never reach the repository. These checks run on every test run."""

import re
import shutil
import subprocess

import pytest

import playbook as pb

KEY_RE = re.compile(r"sk-ant-[A-Za-z0-9_\-]{20,}")

pytestmark = pytest.mark.skipif(shutil.which("git") is None or not (pb.ROOT / ".git").exists(),
                                reason="needs git and a checkout")


def git(*args):
    return subprocess.run(["git", *args], cwd=pb.ROOT, capture_output=True, text=True)


def test_env_file_is_ignored_and_untracked():
    assert git("check-ignore", "-q", ".env").returncode == 0, ".env must be listed in .gitignore"
    tracked = git("ls-files").stdout.splitlines()
    assert not [f for f in tracked if f == ".env" or f.startswith(".env.")]


def test_no_key_shaped_strings_in_tracked_or_staged_files():
    files = set(git("ls-files").stdout.splitlines()) | set(git("diff", "--cached", "--name-only").stdout.splitlines())
    leaks = []
    for name in sorted(files):
        path = pb.ROOT / name
        if not path.is_file():
            continue
        if KEY_RE.search(path.read_bytes().decode("utf8", errors="ignore")):
            leaks.append(name)   # the file name only; never print the match
    assert not leaks, f"key-shaped text found in: {leaks}"
