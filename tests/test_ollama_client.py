"""The Ollama model client (TDD plan, iteration 5)."""

import httpx
import pytest

from shared.llm import LLMError, LLMTimeout, OllamaClient
from shared.schemas import FlightSuggestions
from tests.fakes.llm import PROVIDER_ENV, FakeEmbedder, FakeLLM

pytestmark = pytest.mark.asyncio

SCHEMA = FlightSuggestions.model_json_schema()
MESSAGES = [
    {"role": "system", "content": "You suggest flights."},
    {"role": "user", "content": "Manila to Tokyo"},
]


@pytest.fixture
def client(settings):
    return OllamaClient.from_settings(settings(**PROVIDER_ENV["ollama"], LLM_TIMEOUT_SECONDS="60"))


@pytest.fixture
def llm(respx_mock):
    return FakeLLM(respx_mock, "ollama")


# LLM-01 (TP-SRS-071)
async def test_ollama_requests_schema_json_at_temperature_zero(client, llm):
    llm.answer({"flights": []})
    result = await client.chat(MESSAGES, SCHEMA)
    body = llm.requests[0]
    assert body["format"] == SCHEMA
    assert body["options"]["temperature"] == 0
    assert body["stream"] is False
    assert body["model"] == "qwen2.5:3b"
    assert body["messages"] == MESSAGES
    assert result.content == {"flights": []}


# LLM-03 (TP-SRS-073)
@pytest.mark.parametrize("status", [400, 404, 500, 503])
async def test_http_error_raises_llm_error(client, llm, status):
    llm.fail(status)
    with pytest.raises(LLMError):
        await client.chat(MESSAGES, SCHEMA)


# LLM-03 (TP-SRS-073)
async def test_unreachable_raises_llm_error(client, llm):
    llm.unreachable()
    with pytest.raises(LLMError):
        await client.chat(MESSAGES, SCHEMA)


# LLM-04 (TP-SRS-073)
async def test_request_uses_llm_timeout(client, llm):
    llm.answer({"flights": []})
    await client.chat(MESSAGES, SCHEMA)
    assert llm.last_request.extensions["timeout"]["read"] == 60


# LLM-04 (TP-SRS-073)
async def test_timeout_raises_llm_error(client, llm):
    llm.time_out()
    with pytest.raises(LLMTimeout) as excinfo:
        await client.chat(MESSAGES, SCHEMA)
    assert isinstance(excinfo.value, LLMError)


# LLM-06 (TP-SRS-072, TP-SRS-073)
@pytest.mark.parametrize("text", ["not json", '["a", "list"]', '{"flights": [', ""])
async def test_non_json_answer_raises(client, llm, text):
    llm.answer_text(text)
    with pytest.raises(LLMError):
        await client.chat(MESSAGES, SCHEMA)


# LLM-06 (TP-SRS-073): an answer without the expected envelope is an error too.
@pytest.mark.parametrize("body", [{}, {"message": {}}, {"message": "text"}])
async def test_malformed_envelope_raises(client, llm, body):
    llm.answer_raw(body)
    with pytest.raises(LLMError):
        await client.chat(MESSAGES, SCHEMA)


# LLM-06 (TP-SRS-073)
async def test_body_that_is_not_json_raises(client, llm):
    llm.route.mock(return_value=httpx.Response(200, text="<html>proxy error</html>"))
    with pytest.raises(LLMError):
        await client.chat(MESSAGES, SCHEMA)


# LLM-07 (TP-SRS-120)
async def test_token_usage_reported(client, llm):
    llm.answer({"flights": []}, prompt_tokens=123, completion_tokens=45)
    result = await client.chat(MESSAGES, SCHEMA)
    assert (result.prompt_tokens, result.completion_tokens) == (123, 45)


# LLM-08 (TP-SRS-085, TP-SRS-086)
async def test_embeddings_have_configured_size(client, respx_mock):
    embedder = FakeEmbedder(respx_mock, "ollama", dimensions=768)
    vectors = await client.embed(["Get in", "Get around"])
    assert [len(v) for v in vectors] == [768, 768]
    assert embedder.requests == [{"model": "nomic-embed-text", "input": ["Get in", "Get around"]}]


# LLM-08 (TP-SRS-086)
async def test_embedding_of_wrong_size_raises(client, respx_mock):
    FakeEmbedder(respx_mock, "ollama", dimensions=512)
    with pytest.raises(LLMError, match="768"):
        await client.embed(["Get in"])


# LLM-08 (TP-SRS-085)
async def test_embedding_failure_raises(client, respx_mock):
    FakeEmbedder(respx_mock, "ollama", dimensions=768).fail(500)
    with pytest.raises(LLMError):
        await client.embed(["Get in"])
