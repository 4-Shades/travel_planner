"""The guidance index: passages, the embedding identity that built them, and the two stores (TP-SRS-106)."""

import importlib
from dataclasses import dataclass
from datetime import date
from pathlib import Path


@dataclass(frozen=True)
class EmbeddingIdentity:
    """The provider, model, and vector size that built an index (TP-SRS-107)."""

    provider: str
    model: str
    dimensions: int

    def __str__(self):
        return f"{self.provider} {self.model} ({self.dimensions} dimensions)"


@dataclass(frozen=True)
class Passage:
    """One stored passage and what it came from (TP-SRS-101)."""

    id: str
    destination: str
    section: str
    title: str
    url: str
    revision_id: int
    license: str
    language: str
    valid_from: date
    valid_until: date
    text: str

    def is_valid_on(self, day):
        return self.valid_from <= day <= self.valid_until


class IndexUnavailable(Exception):
    """There is no usable index at the configured location."""


# Each store implements: identity, destinations(), search(...), replace(...), and count().
_STORES = {"chroma": ("shared.rag.chroma_store", "ChromaStore"), "file": ("shared.rag.file_store", "FileStore")}


def _store_class(kind):
    # Imported only when used, so a missing optional package (chromadb) fails here, not at startup.
    module, name = _STORES[kind]
    return getattr(importlib.import_module(module), name)


def open_store(kind, path):
    """Open an existing index for reading; raises IndexUnavailable or ImportError."""
    path = Path(path)
    if not path.exists():
        raise IndexUnavailable(f"no guidance index at {path}")
    return _store_class(kind).open(path)


def create_store(kind, path, identity):
    """Open an index for writing, creating it if needed; its identity must match."""
    return _store_class(kind).create(Path(path), identity)
