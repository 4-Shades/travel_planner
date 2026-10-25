"""Configuration from environment variables (TDD plan, iteration 2)."""

import pytest
from uvicorn.importer import import_from_string

from shared.config import ConfigError, Settings
from tests.asgi import AppClient


# CFG-01 (TP-SRS-163)
def test_settings_come_from_environment(settings):
    assert settings(RAG_TOP_K="5").rag_top_k == 5


# CFG-01 (TP-SRS-163)
def test_no_configuration_file_is_read(settings, tmp_path, monkeypatch):
    (tmp_path / ".env").write_text("RAG_TOP_K=9\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert settings().rag_top_k == 2


# CFG-04 (TP-SRS-142)
@pytest.mark.parametrize(
    "llm, downstream, accepted",
    [("60", "45", False), ("60", "60", False), ("60", "90", True), ("60", "179", True), ("60", "180", False)],
)
def test_timeouts_must_nest(settings, llm, downstream, accepted):
    env = {"LLM_TIMEOUT_SECONDS": llm, "DOWNSTREAM_TIMEOUT_SECONDS": downstream}
    if accepted:
        assert settings(**env).downstream_timeout_seconds == float(downstream)
    else:
        with pytest.raises(ConfigError, match="DOWNSTREAM_TIMEOUT_SECONDS"):
            settings(**env)


# CFG-04: a value that is not a number stops startup and names the variable.
@pytest.mark.parametrize("name", ["LLM_TIMEOUT_SECONDS", "DOWNSTREAM_TIMEOUT_SECONDS", "RAG_TOP_K"])
def test_invalid_number_names_variable(settings, name):
    with pytest.raises(ConfigError, match=name):
        settings(**{name: "soon"})


# CFG-05 (TP-SRS-142)
def test_default_timeouts_nest():
    defaults = Settings()
    assert defaults.llm_timeout_seconds < defaults.downstream_timeout_seconds < 180


# CFG-06 (TP-SRS-080)
def test_rag_top_k_defaults_to_two(settings):
    assert settings().rag_top_k == 2


# CFG-07 (TP-SRS-161)
@pytest.mark.parametrize("service", ["host", "flight", "stay", "activities"])
def test_app_module_selects_agent(service):
    app = import_from_string(f"agents.{service}.app:app")
    response = AppClient(app).get("/healthz")
    assert response.json()["service"] == service
