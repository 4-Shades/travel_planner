"""Repository checks: pinned dependencies and ignored secrets (TDD plan, iteration 14)."""

import json
import re
import subprocess
import tomllib
from pathlib import Path

import pathspec
import pytest

from shared.rag import open_store
from shared.rag.destinations import alias_map, load_destinations

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


# REP-01 (TP-SRS-166): Vercel installs from pyproject.toml, so its pins must match the lock files.
def test_pyproject_matches_requirements():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    requirements = ROOT / "requirements"
    assert project["project"]["dependencies"] == list(requirement_lines(requirements / "requirements.in")), (
        "Copy requirements/requirements.in into [project] dependencies in pyproject.toml"
    )
    assert project["tool"]["uv"]["constraint-dependencies"] == list(requirement_lines(requirements / "requirements.txt")), (
        "Copy requirements/requirements.txt into [tool.uv] constraint-dependencies in pyproject.toml"
    )


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


# REP-03 (TP-SRS-152)
def test_cloud_index_committed():
    index = ROOT / "data" / "rag" / "index" / "file"
    if not (index / "identity.json").exists():
        pytest.skip("The cloud index is not built yet: run the ingest command with OpenAI embeddings (phase 8)")
    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", *(str(p.relative_to(ROOT)) for p in index.iterdir())],
        cwd=ROOT,
        capture_output=True,
    )
    assert tracked.returncode == 0, tracked.stderr.decode()
    assert open_store("file", index).identity.provider == "openai"


# The destination file lists the default 20 destinations (SRS §1.6), with unique names and aliases.
def test_destination_file():
    destinations = load_destinations(ROOT / "data" / "rag" / "destinations.txt")
    names = [alias for d in destinations for alias in (d.name, *d.aliases)]
    assert len(destinations) == 20
    assert len(names) == len(set(names))
    assert alias_map(destinations)["NYC"] == "New York City"


# REP-02 (TP-SRS-182)
@pytest.mark.parametrize("ignore_file", IGNORE_FILES)
@pytest.mark.parametrize("secret_path", SECRET_PATHS)
def test_secrets_ignored(ignore_file, secret_path):
    assert ignore_spec(ignore_file).match_file(secret_path)


# REP-02: the template that documents the variables is meant to be committed.
@pytest.mark.parametrize("ignore_file", IGNORE_FILES)
def test_env_example_not_ignored(ignore_file):
    assert not ignore_spec(ignore_file).match_file(".env.example")
