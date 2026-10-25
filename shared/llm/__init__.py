"""Language-model clients, chosen by LLM_PROVIDER without code changes (TP-SRS-077, TP-SRS-186)."""

from shared.llm.base import ChatResult, LLMError, LLMTimeout
from shared.llm.ollama_client import OllamaClient
from shared.llm.openai_client import OpenAIClient

_CLIENTS = {"ollama": OllamaClient, "openai": OpenAIClient}


def create_llm_client(settings):
    return _CLIENTS[settings.llm_provider].from_settings(settings)


__all__ = ["ChatResult", "LLMError", "LLMTimeout", "OllamaClient", "OpenAIClient", "create_llm_client"]
