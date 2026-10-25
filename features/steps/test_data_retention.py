"""Steps for features/operations/data_retention.feature (BDD scenarios §6.3)."""

import hashlib
from pathlib import Path

import pytest
from pytest_bdd import parsers, scenarios, then, when

scenarios("operations/data_retention.feature")

DATA = Path(__file__).resolve().parents[2] / "data"


def fingerprint(*roots):
    return {
        str(path): hashlib.sha256(path.read_bytes()).hexdigest()
        for root in roots
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


@pytest.fixture
def working_directory(tmp_path, monkeypatch):
    """The agents run from an empty directory, so anything they write would show up there."""
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def before(working_directory):
    return fingerprint(working_directory, DATA)


@when(parsers.parse('I post a valid travel request with user_id "{user_id}"'), target_fixture="response")
def post_with_user_id(agent, travel_request, before, user_id):
    return agent.post("/run", json={**travel_request, "user_id": user_id})


@when("the plan arrives")
def plan_arrives(response):
    assert response.status_code == 200
    assert response.json()["errors"] == []


@then("no file in the application's data directories has changed")
def nothing_written(working_directory, before):
    assert fingerprint(working_directory, DATA) == before


@then(parsers.parse('"{text}" appears nowhere except in log lines'))
def appears_only_in_logs(response, working_directory, text):
    assert text not in response.text
    for root in (working_directory, DATA):
        for path in root.rglob("*"):
            if path.is_file():
                assert text.encode() not in path.read_bytes(), path
