"""OpenAI: cloud generation with strict JSON schemas, and embeddings (TP-SRS-077)."""

import copy

from shared.config import ConfigError
from shared.llm.base import ChatResult, LLMError, check_vectors, parse_object, post_json

PROVIDER = "OpenAI"


def strict_schema(schema):
    """Return a copy that OpenAI's strict mode accepts: every object closed, every property required."""
    strict = copy.deepcopy(schema)

    def close(node):
        if isinstance(node, dict):
            if "properties" in node:
                node["additionalProperties"] = False
                node["required"] = list(node["properties"])
            for value in node.values():
                close(value)
        elif isinstance(node, list):
            for value in node:
                close(value)

    close(strict)
    return strict


class OpenAIClient:
    def __init__(self, base_url, api_key, chat_model, embedding_model, embedding_dimensions, timeout):
        self.base_url = base_url.rstrip("/")
        self._headers = {"Authorization": f"Bearer {api_key}"}
        self.chat_model = chat_model
        self.embedding_model = embedding_model
        self.embedding_dimensions = embedding_dimensions
        self.timeout = timeout

    @classmethod
    def from_settings(cls, settings):
        if not settings.openai_api_key:
            raise ConfigError("OPENAI_API_KEY must be set when LLM_PROVIDER is openai")
        return cls(
            settings.openai_base_url,
            settings.openai_api_key,
            settings.llm_model,
            settings.embedding_model,
            settings.embedding_dimensions,
            settings.llm_timeout_seconds,
        )

    async def chat(self, messages, schema):
        """Ask for one JSON object matching the schema, at temperature 0 (TP-SRS-071)."""
        body = {
            "model": self.chat_model,
            "messages": messages,
            "temperature": 0,
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": schema.get("title", "response"), "schema": strict_schema(schema), "strict": True},
            },
        }
        answer = await post_json(PROVIDER, f"{self.base_url}/chat/completions", body, self.timeout, self._headers)
        try:
            message = answer["choices"][0]["message"]
            refusal, text = message.get("refusal"), message.get("content")
        except (KeyError, IndexError, TypeError, AttributeError):
            raise LLMError(f"{PROVIDER} answered without a message") from None
        if refusal:
            raise LLMError(f"{PROVIDER} refused the request")
        usage = answer.get("usage") or {}
        return ChatResult(
            content=parse_object(PROVIDER, text),
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
        )

    async def embed(self, texts):
        body = {"model": self.embedding_model, "input": texts}
        answer = await post_json(PROVIDER, f"{self.base_url}/embeddings", body, self.timeout, self._headers)
        try:
            vectors = [item["embedding"] for item in sorted(answer["data"], key=lambda item: item["index"])]
        except (KeyError, TypeError):
            vectors = None
        return check_vectors(PROVIDER, vectors, len(texts), self.embedding_dimensions)
