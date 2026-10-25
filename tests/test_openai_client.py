"""The OpenAI model client (TDD plan, iteration 5)."""

import copy

import pytest

from shared.llm import LLMError, LLMTimeout, OpenAIClient
from shared.llm.openai_client import strict_schema
from shared.schemas import SPECIALISTS, FlightSuggestions
from tests.fakes.llm import OPENAI_KEY, PROVIDER_ENV, FakeEmbedder, FakeLLM

pytestmark = pytest.mark.asyncio

SCHEMA = FlightSuggestions.model_json_schema()
MESSAGES = [
    {"role": "system", "content": "You suggest flights."},
    {"role": "user", "content": "Manila to Tokyo"},
]


@pytest.fixture
def client(settings):
    return OpenAIClient.from_settings(settings(**PROVIDER_ENV["openai"], LLM_TIMEOUT_SECONDS="60"))


@pytest.fixture
def llm(respx_mock):
    return FakeLLM(respx_mock, "openai")


def object_nodes(schema):
    if isinstance(schema, dict):
        if schema.get("type") == "object" or "properties" in schema:
            yield schema
        for value in schema.values():
            yield from object_nodes(value)
    elif isinstance(schema, list):
        for value in schema:
            yield from object_nodes(value)


# LLM-02 (TP-SRS-071)
async def test_openai_requests_strict_schema_at_temperature_zero(client, llm):
    llm.answer({"flights": []})
    result = await client.chat(MESSAGES, SCHEMA)
    body = llm.requests[0]
    assert body["temperature"] == 0
    assert body["model"] == "gpt-4.1-mini"
    assert body["messages"] == MESSAGES
    response_format = body["response_format"]
    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["strict"] is True
    assert response_format["json_schema"]["name"] == "FlightSuggestions"
    assert response_format["json_schema"]["schema"] == strict_schema(SCHEMA)
    assert result.content == {"flights": []}


# LLM-02 (TP-SRS-071)
async def test_request_sends_api_key(client, llm):
    llm.answer({"flights": []})
    await client.chat(MESSAGES, SCHEMA)
    assert llm.last_request.headers["Authorization"] == f"Bearer {OPENAI_KEY}"


# LLM-02: strict mode needs every object closed and every property required.
@pytest.mark.parametrize("service", SPECIALISTS)
async def test_strict_schema_closes_every_object(service):
    schema = SPECIALISTS[service].model_output.model_json_schema()
    original = copy.deepcopy(schema)
    strict = strict_schema(schema)
    nodes = list(object_nodes(strict))
    assert nodes
    for node in nodes:
        assert node["additionalProperties"] is False
        assert sorted(node["required"]) == sorted(node["properties"])
    assert schema == original


# LLM-03 (TP-SRS-073)
@pytest.mark.parametrize("status", [400, 401, 429, 500])
async def test_http_error_raises_llm_error(client, llm, status):
    llm.fail(status)
    with pytest.raises(LLMError):
        await client.chat(MESSAGES, SCHEMA)


# LLM-03 (TP-SRS-073, TP-SRS-132): the error describes the failure without the API key.
async def test_error_does_not_reveal_api_key(client, llm):
    llm.fail(401)
    with pytest.raises(LLMError) as excinfo:
        await client.chat(MESSAGES, SCHEMA)
    assert OPENAI_KEY not in str(excinfo.value)


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


# LLM-05 (TP-SRS-073)
async def test_refusal_raises_llm_error(client, llm):
    llm.refuse()
    with pytest.raises(LLMError, match="refused"):
        await client.chat(MESSAGES, SCHEMA)


# LLM-06 (TP-SRS-072, TP-SRS-073)
@pytest.mark.parametrize("text", ["not json", '["a", "list"]', '{"flights": [', ""])
async def test_non_json_answer_raises(client, llm, text):
    llm.answer_text(text)
    with pytest.raises(LLMError):
        await client.chat(MESSAGES, SCHEMA)


# LLM-06 (TP-SRS-073)
@pytest.mark.parametrize("body", [{}, {"choices": []}, {"choices": [{}]}, {"choices": [{"message": "text"}]}])
async def test_malformed_envelope_raises(client, llm, body):
    llm.answer_raw(body)
    with pytest.raises(LLMError):
        await client.chat(MESSAGES, SCHEMA)


# LLM-07 (TP-SRS-120)
async def test_token_usage_reported(client, llm):
    llm.answer({"flights": []}, prompt_tokens=321, completion_tokens=54)
    result = await client.chat(MESSAGES, SCHEMA)
    assert (result.prompt_tokens, result.completion_tokens) == (321, 54)


# LLM-08 (TP-SRS-085, TP-SRS-086)
async def test_embeddings_have_configured_size(client, respx_mock):
    embedder = FakeEmbedder(respx_mock, "openai", dimensions=1536)
    vectors = await client.embed(["Get in", "Get around"])
    assert [len(v) for v in vectors] == [1536, 1536]
    assert embedder.requests == [{"model": "text-embedding-3-small", "input": ["Get in", "Get around"]}]


# LLM-08 (TP-SRS-086)
async def test_embedding_of_wrong_size_raises(client, respx_mock):
    FakeEmbedder(respx_mock, "openai", dimensions=768)
    with pytest.raises(LLMError, match="1536"):
        await client.embed(["Get in"])


# LLM-08 (TP-SRS-085)
async def test_embedding_failure_raises(client, respx_mock):
    FakeEmbedder(respx_mock, "openai", dimensions=1536).time_out()
    with pytest.raises(LLMTimeout):
        await client.embed(["Get in"])
