"""Planning when the vector-store package is missing (TDD plan, RAG-09)."""

import logging

import pytest

from tests.asgi import AppClient
from tests.fakes.index import GuidanceIndex, hide_chromadb
from tests.fakes.llm import PROVIDER_ENV, FakeEmbedder, FakeLLM

pytestmark = pytest.mark.respx(assert_all_called=False)


# RAG-09 (TP-SRS-085, TP-SRS-181)
def test_missing_package_plans_without_guidance(agent_app, respx_mock, tmp_path, monkeypatch, caplog, today, valid_request):
    index = GuidanceIndex(tmp_path, "chroma").build()
    llm = FakeLLM(respx_mock, "ollama")
    llm.answer_normally()
    embedder = FakeEmbedder(respx_mock, "ollama", dimensions=8)
    caplog.set_level(logging.INFO, logger="travel_planner")
    hide_chromadb(monkeypatch)

    app = agent_app("activities", **PROVIDER_ENV["ollama"], **index.env())
    response = AppClient(app).post("/run", json=valid_request())

    body = response.json()
    assert body["activities"] and body["error"] is None and body["sources"] == []
    assert embedder.call_count == 0
    assert "<guidance>" not in llm.prompts[0]
    assert any("chromadb is not installed" in r.getMessage() for r in caplog.records)
