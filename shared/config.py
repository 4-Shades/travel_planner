"""Settings, read only from environment variables (TP-SRS-163)."""

import os
from dataclasses import dataclass, field

# The web application waits this long for the Host (TP-SRS-022, TP-SRS-142).
WEB_TIMEOUT_SECONDS = 180

# Chat model, embedding model, and vector size used when none is configured.
PROVIDER_DEFAULTS = {
    "ollama": ("qwen2.5:3b", "nomic-embed-text", 768),
    "openai": ("gpt-4.1-mini", "text-embedding-3-small", 1536),
}

_NUMBERS = (
    ("LLM_TIMEOUT_SECONDS", "llm_timeout_seconds", float),
    ("DOWNSTREAM_TIMEOUT_SECONDS", "downstream_timeout_seconds", float),
    ("RAG_TOP_K", "rag_top_k", int),
    ("EMBEDDING_DIMENSIONS", "embedding_dimensions", int),
)
# Empty values count as not set.
_STRINGS = (
    ("LLM_PROVIDER", "llm_provider"),
    ("LLM_MODEL", "llm_model"),
    ("EMBEDDING_MODEL", "embedding_model"),
    ("OLLAMA_BASE_URL", "ollama_base_url"),
    ("OPENAI_BASE_URL", "openai_base_url"),
    ("OPENAI_API_KEY", "openai_api_key"),
    ("HOST_API_KEY", "host_api_key"),
)

ENV_VARS = tuple(name for name, *_ in _NUMBERS + _STRINGS)


class ConfigError(ValueError):
    """Raised at startup when an environment variable has an unusable value."""


@dataclass(frozen=True)
class Settings:
    llm_provider: str = "ollama"
    llm_model: str | None = None
    embedding_model: str | None = None
    embedding_dimensions: int | None = None
    ollama_base_url: str = "http://localhost:11434"
    openai_base_url: str = "https://api.openai.com/v1"
    llm_timeout_seconds: float = 120
    downstream_timeout_seconds: float = 150
    rag_top_k: int = 2
    # Secrets are kept out of repr() so they never reach a log line.
    openai_api_key: str | None = field(default=None, repr=False)
    host_api_key: str | None = field(default=None, repr=False)

    def __post_init__(self):
        if self.llm_provider not in PROVIDER_DEFAULTS:
            raise ConfigError(f"LLM_PROVIDER must be one of {', '.join(PROVIDER_DEFAULTS)}, not {self.llm_provider!r}")
        chat_model, embedding_model, dimensions = PROVIDER_DEFAULTS[self.llm_provider]
        object.__setattr__(self, "llm_model", self.llm_model or chat_model)
        object.__setattr__(self, "embedding_model", self.embedding_model or embedding_model)
        object.__setattr__(self, "embedding_dimensions", self.embedding_dimensions or dimensions)
        # Each caller waits longer than the call it makes (TP-SRS-142).
        if not self.llm_timeout_seconds < self.downstream_timeout_seconds < WEB_TIMEOUT_SECONDS:
            raise ConfigError(
                "DOWNSTREAM_TIMEOUT_SECONDS must be greater than LLM_TIMEOUT_SECONDS "
                f"and less than {WEB_TIMEOUT_SECONDS}"
            )
        if self.rag_top_k < 1:
            raise ConfigError("RAG_TOP_K must be at least 1")
        if self.embedding_dimensions < 1:
            raise ConfigError("EMBEDDING_DIMENSIONS must be at least 1")

    @classmethod
    def from_env(cls, environ=None):
        environ = os.environ if environ is None else environ
        values = {}
        for name, attribute, kind in _NUMBERS:
            if environ.get(name):
                try:
                    values[attribute] = kind(environ[name])
                except ValueError:
                    raise ConfigError(f"{name} must be a number, not {environ[name]!r}") from None
        for name, attribute in _STRINGS:
            if environ.get(name):
                values[attribute] = environ[name]
        return cls(**values)
