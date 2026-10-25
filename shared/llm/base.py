"""What both model clients share: the result type, the errors, and the HTTP call."""

import json
from dataclasses import dataclass

import httpx


class LLMError(Exception):
    """Any failure of a model or embedding call: unreachable, error status, timeout, refusal, or bad output."""


class LLMTimeout(LLMError):
    """The call took longer than LLM_TIMEOUT_SECONDS."""


@dataclass(frozen=True)
class ChatResult:
    content: dict
    prompt_tokens: int
    completion_tokens: int


async def post_json(provider, url, body, timeout, headers=None):
    """POST a JSON body and return the decoded JSON answer, turning every failure into an LLMError."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=body, headers=headers, timeout=timeout)
    except httpx.TimeoutException:
        raise LLMTimeout(f"{provider} did not answer within {timeout} seconds") from None
    except httpx.HTTPError as error:
        raise LLMError(f"{provider} could not be reached: {type(error).__name__}") from None
    if response.status_code >= 400:
        raise LLMError(f"{provider} answered with HTTP {response.status_code}")
    try:
        return response.json()
    except ValueError:
        raise LLMError(f"{provider} answered with a body that is not JSON") from None


def parse_object(provider, text):
    """Decode the model's answer, which must be one JSON object."""
    try:
        content = json.loads(text)
    except (TypeError, ValueError):
        raise LLMError(f"{provider} answered with content that is not JSON") from None
    if not isinstance(content, dict):
        raise LLMError(f"{provider} answered with JSON that is not an object")
    return content


def check_vectors(provider, vectors, count, dimensions):
    """Embeddings must match the configured identity, or retrieval would compare unlike vectors."""
    if not isinstance(vectors, list) or len(vectors) != count:
        raise LLMError(f"{provider} did not return one embedding for each of the {count} texts")
    for vector in vectors:
        if not isinstance(vector, list) or len(vector) != dimensions:
            size = len(vector) if isinstance(vector, list) else "no"
            raise LLMError(f"{provider} returned a vector of size {size}; {dimensions} is configured")
    return vectors
