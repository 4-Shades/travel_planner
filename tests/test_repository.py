"""Repository checks: pinned dependencies and ignored secrets (TDD plan, iteration 14)."""

import json
import re
from pathlib import Path

import pathspec
import pytest

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"

SECRET_PATHS = [
    ".env",
    ".env.local",
    "web/.env.production",
    "infra/terraform.tfstate",
    "infra/terraform.tfstate.backup",
    "infra/.terraform/providers/lock",
]
IGNORE_FILES = [".gitignore", ".dockerignore", ".vercelignore"]


def requirement_lines(path):
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line and not line.startswith("-"):
            yield line


def ignore_spec(name):
    lines = (ROOT / name).read_text(encoding="utf-8").splitlines()
    return pathspec.GitIgnoreSpec.from_lines(lines)


# REP-01 (TP-SRS-166)
REQUIREMENT_FILES = sorted(p.name for p in (ROOT / "requirements").glob("requirements*.*") if p.suffix in (".in", ".txt"))


def test_requirement_files_found():
    # Each input file has a compiled lock file beside it.
    inputs = {name[: -len(".in")] for name in REQUIREMENT_FILES if name.endswith(".in")}
    locks = {name[: -len(".txt")] for name in REQUIREMENT_FILES if name.endswith(".txt")}
    assert inputs >= {"requirements", "requirements-rag", "requirements-dev"}
    assert inputs == locks


@pytest.mark.parametrize("name", REQUIREMENT_FILES)
def test_python_dependencies_pinned(name):
    lines = list(requirement_lines(ROOT / "requirements" / name))
    assert lines, f"{name} lists no dependencies"
    unpinned = [line for line in lines if not re.match(r"^[A-Za-z0-9._\[\]-]+==[^=<>~!*]+(\s*;.*)?$", line)]
    assert unpinned == []


# REP-01 (TP-SRS-166)
def test_web_dependencies_pinned():
    package_json = WEB / "package.json"
    if not package_json.exists():
        pytest.skip("The web application is added in phase 11")
    package = json.loads(package_json.read_text(encoding="utf-8"))
    versions = {
        name: version
        for section in ("dependencies", "devDependencies")
        for name, version in package.get(section, {}).items()
    }
    unpinned = {name: v for name, v in versions.items() if not re.fullmatch(r"\d+\.\d+\.\d+(-[0-9A-Za-z.-]+)?", v)}
    assert unpinned == {}
    assert (WEB / "package-lock.json").exists()


# REP-02 (TP-SRS-182)
@pytest.mark.parametrize("ignore_file", IGNORE_FILES)
@pytest.mark.parametrize("secret_path", SECRET_PATHS)
def test_secrets_ignored(ignore_file, secret_path):
    assert ignore_spec(ignore_file).match_file(secret_path)


# REP-02: the template that documents the variables is meant to be committed.
@pytest.mark.parametrize("ignore_file", IGNORE_FILES)
def test_env_example_not_ignored(ignore_file):
    assert not ignore_spec(ignore_file).match_file(".env.example")
