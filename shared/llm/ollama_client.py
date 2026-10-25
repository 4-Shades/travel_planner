"""Ollama: local generation and embeddings over its HTTP API (TP-SRS-077)."""

from shared.llm.base import ChatResult, LLMError, check_vectors, parse_object, post_json

PROVIDER = "Ollama"


class OllamaClient:
    def __init__(self, base_url, chat_model, embedding_model, embedding_dimensions, timeout):
        self.base_url = base_url.rstrip("/")
        self.chat_model = chat_model
        self.embedding_model = embedding_model
        self.embedding_dimensions = embedding_dimensions
        self.timeout = timeout

    @classmethod
    def from_settings(cls, settings):
        return cls(
            settings.ollama_base_url,
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
            "format": schema,
            "stream": False,
            "options": {"temperature": 0},
        }
        answer = await post_json(PROVIDER, f"{self.base_url}/api/chat", body, self.timeout)
        try:
            text = answer["message"]["content"]
        except (KeyError, TypeError):
            raise LLMError(f"{PROVIDER} answered without a message") from None
        return ChatResult(
            content=parse_object(PROVIDER, text),
            prompt_tokens=answer.get("prompt_eval_count", 0),
            completion_tokens=answer.get("eval_count", 0),
        )

    async def embed(self, texts):
        body = {"model": self.embedding_model, "input": texts}
        answer = await post_json(PROVIDER, f"{self.base_url}/api/embed", body, self.timeout)
        vectors = answer.get("embeddings") if isinstance(answer, dict) else None
        return check_vectors(PROVIDER, vectors, len(texts), self.embedding_dimensions)
