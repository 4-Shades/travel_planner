"""Settings, read only from environment variables (TP-SRS-163)."""

import os
from dataclasses import dataclass

# The web application waits this long for the Host (TP-SRS-022, TP-SRS-142).
WEB_TIMEOUT_SECONDS = 180

ENV_VARS = ("LLM_TIMEOUT_SECONDS", "DOWNSTREAM_TIMEOUT_SECONDS", "RAG_TOP_K", "HOST_API_KEY")


class ConfigError(ValueError):
    """Raised at startup when an environment variable has an unusable value."""


@dataclass(frozen=True)
class Settings:
    llm_timeout_seconds: float = 120
    downstream_timeout_seconds: float = 150
    rag_top_k: int = 2

    def __post_init__(self):
        # Each caller waits longer than the call it makes (TP-SRS-142).
        if not self.llm_timeout_seconds < self.downstream_timeout_seconds < WEB_TIMEOUT_SECONDS:
            raise ConfigError(
                "DOWNSTREAM_TIMEOUT_SECONDS must be greater than LLM_TIMEOUT_SECONDS "
                f"and less than {WEB_TIMEOUT_SECONDS}"
            )
        if self.rag_top_k < 1:
            raise ConfigError("RAG_TOP_K must be at least 1")

    @classmethod
    def from_env(cls, environ=None):
        environ = os.environ if environ is None else environ
        values = {}
        for name, field, kind in (
            ("LLM_TIMEOUT_SECONDS", "llm_timeout_seconds", float),
            ("DOWNSTREAM_TIMEOUT_SECONDS", "downstream_timeout_seconds", float),
            ("RAG_TOP_K", "rag_top_k", int),
        ):
            if name in environ:
                try:
                    values[field] = kind(environ[name])
                except ValueError:
                    raise ConfigError(f"{name} must be a number, not {environ[name]!r}") from None
        return cls(**values)
