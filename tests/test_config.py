"""Configuration from environment variables (TDD plan, iteration 2)."""

import pytest
from uvicorn.importer import import_from_string

from shared.config import ConfigError, Settings
from shared.llm import OllamaClient, OpenAIClient, create_llm_client
from tests.asgi import AppClient
from tests.fakes.llm import PROVIDER_ENV


# CFG-01 (TP-SRS-163)
def test_settings_come_from_environment(settings):
    assert settings(RAG_TOP_K="5").rag_top_k == 5


# CFG-01 (TP-SRS-163)
def test_no_configuration_file_is_read(settings, tmp_path, monkeypatch):
    (tmp_path / ".env").write_text("RAG_TOP_K=9\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert settings().rag_top_k == 2


# CFG-02 (TP-SRS-077, TP-SRS-186)
@pytest.mark.parametrize("provider, client_class", [("ollama", OllamaClient), ("openai", OpenAIClient)])
def test_provider_selects_model_client(settings, provider, client_class):
    client = create_llm_client(settings(**PROVIDER_ENV[provider]))
    assert isinstance(client, client_class)


# CFG-02 (TP-SRS-077): each provider has its own default models.
@pytest.mark.parametrize(
    "provider, chat_model, embedding_model, dimensions",
    [("ollama", "qwen2.5:3b", "nomic-embed-text", 768), ("openai", "gpt-4.1-mini", "text-embedding-3-small", 1536)],
)
def test_provider_default_models(settings, provider, chat_model, embedding_model, dimensions):
    config = settings(LLM_PROVIDER=provider)
    assert (config.llm_model, config.embedding_model, config.embedding_dimensions) == (
        chat_model,
        embedding_model,
        dimensions,
    )


# CFG-02 (TP-SRS-077)
def test_models_can_be_overridden(settings):
    config = settings(LLM_MODEL="llama3.2:3b", EMBEDDING_MODEL="mxbai-embed-large", EMBEDDING_DIMENSIONS="1024")
    assert (config.llm_model, config.embedding_model, config.embedding_dimensions) == (
        "llama3.2:3b",
        "mxbai-embed-large",
        1024,
    )


# CFG-02 (TP-SRS-183): only agents that call OpenAI need its key, so it is checked when the client is made.
def test_openai_client_needs_api_key(settings):
    with pytest.raises(ConfigError, match="OPENAI_API_KEY"):
        create_llm_client(settings(LLM_PROVIDER="openai"))


# CFG-02: the OpenAI key never appears in a printed settings object.
def test_settings_repr_hides_openai_key(settings):
    assert "sk-secret" not in repr(settings(OPENAI_API_KEY="sk-secret"))


# CFG-03 (TP-SRS-077)
def test_unknown_provider_fails_at_startup(settings):
    with pytest.raises(ConfigError, match="LLM_PROVIDER"):
        settings(LLM_PROVIDER="other")


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
@pytest.mark.parametrize(
    "name", ["LLM_TIMEOUT_SECONDS", "DOWNSTREAM_TIMEOUT_SECONDS", "RAG_TOP_K", "EMBEDDING_DIMENSIONS"]
)
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
