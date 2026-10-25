"""FakeLLM and FakeEmbedder: respx routes standing in for the Ollama and OpenAI endpoints (TDD plan §2.3)."""

import hashlib
import json

import httpx

from tests import factories

OLLAMA_URL = "http://ollama.test"
OPENAI_URL = "https://openai.test/v1"
OPENAI_KEY = "sk-test-key-0000"

# Environment for settings that point the model clients at the fakes.
PROVIDER_ENV = {
    "ollama": {"LLM_PROVIDER": "ollama", "OLLAMA_BASE_URL": OLLAMA_URL},
    "openai": {"LLM_PROVIDER": "openai", "OPENAI_BASE_URL": OPENAI_URL, "OPENAI_API_KEY": OPENAI_KEY},
}


# The model-output schema each specialist asks for, by title, and a valid answer to it.
VALID_ANSWERS = {
    "FlightSuggestions": lambda: {"flights": [factories.flight_offer(), factories.flight_offer(airline="Other Air")]},
    "StaySuggestions": lambda: {"stay": [factories.stay_offer(), factories.stay_offer(name="Example Inn Asakusa")]},
    "ActivitySuggestions": lambda: {"activities": [factories.activity_offer(), factories.activity_offer(name="TeamLab")]},
}


def _route(respx_mock, provider, ollama_path, openai_path):
    if provider == "ollama":
        return respx_mock.post(f"{OLLAMA_URL}{ollama_path}")
    return respx_mock.post(f"{OPENAI_URL}{openai_path}")


def _envelope(provider, text, prompt_tokens=11, completion_tokens=22):
    if provider == "ollama":
        return {
            "message": {"role": "assistant", "content": text},
            "done": True,
            "prompt_eval_count": prompt_tokens,
            "eval_count": completion_tokens,
        }
    return {
        "choices": [{"message": {"role": "assistant", "content": text, "refusal": None}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens},
    }


def requested_schema(provider, body):
    if provider == "ollama":
        return body["format"]
    return body["response_format"]["json_schema"]["schema"]


class FakeLLM:
    """A provider's chat endpoint. Configure one answer, then read back the requests it received."""

    def __init__(self, respx_mock, provider):
        self.provider = provider
        self.route = _route(respx_mock, provider, "/api/chat", "/chat/completions")

    def answer_normally(self):
        """Answer every request with valid offers for whichever schema it asks for."""

        def answer(request):
            title = requested_schema(self.provider, json.loads(request.content))["title"]
            return httpx.Response(200, json=_envelope(self.provider, json.dumps(VALID_ANSWERS[title]())))

        self.route.mock(side_effect=answer)

    def answer(self, content, prompt_tokens=11, completion_tokens=22):
        self.answer_text(json.dumps(content), prompt_tokens, completion_tokens)

    def answer_text(self, text, prompt_tokens=11, completion_tokens=22):
        self.answer_raw(_envelope(self.provider, text, prompt_tokens, completion_tokens))

    def answer_raw(self, body):
        self.route.mock(return_value=httpx.Response(200, json=body))

    def refuse(self, message="I can't help with that."):
        body = {
            "choices": [{"message": {"role": "assistant", "content": None, "refusal": message}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 11, "completion_tokens": 3},
        }
        self.answer_raw(body)

    def fail(self, status=500):
        self.route.mock(return_value=httpx.Response(status, json={"error": "fake failure"}))

    def time_out(self):
        self.route.mock(side_effect=httpx.ReadTimeout("fake timeout"))

    def unreachable(self):
        self.route.mock(side_effect=httpx.ConnectError("fake connection refused"))

    @property
    def requests(self):
        return [json.loads(call.request.content) for call in self.route.calls]

    @property
    def last_request(self):
        return self.route.calls.last.request

    @property
    def prompts(self):
        """Each request's messages joined into one text, for checking what the model was told."""
        return ["\n\n".join(message["content"] for message in body["messages"]) for body in self.requests]


def fake_vector(text, dimensions):
    """A deterministic vector derived from a hash of the text."""
    seed = hashlib.sha256(text.encode()).digest()
    return [seed[i % len(seed)] / 255 for i in range(dimensions)]


class FakeEmbedder:
    """A provider's embedding endpoint, answering with deterministic vectors of a configurable size."""

    def __init__(self, respx_mock, provider, dimensions):
        self.provider = provider
        self.dimensions = dimensions
        self.route = _route(respx_mock, provider, "/api/embed", "/embeddings")
        self.route.mock(side_effect=self._answer)

    def _answer(self, request):
        texts = json.loads(request.content)["input"]
        vectors = [fake_vector(text, self.dimensions) for text in texts]
        if self.provider == "ollama":
            return httpx.Response(200, json={"embeddings": vectors})
        data = [{"object": "embedding", "index": i, "embedding": v} for i, v in enumerate(vectors)]
        return httpx.Response(200, json={"data": data})

    def fail(self, status=500):
        self.route.mock(return_value=httpx.Response(status, json={"error": "fake failure"}))

    def time_out(self):
        self.route.mock(side_effect=httpx.ReadTimeout("fake timeout"))

    @property
    def call_count(self):
        return self.route.call_count

    @property
    def requests(self):
        return [json.loads(call.request.content) for call in self.route.calls]
