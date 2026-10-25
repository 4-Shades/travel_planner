"""A small guidance index for tests, built with fake embeddings (TDD plan §2.3)."""

import hashlib
import sys
from dataclasses import replace
from datetime import date

from shared.rag import EmbeddingIdentity, Passage, create_store
from tests.fakes.llm import fake_vector

DIMENSIONS = 8
IDENTITY = EmbeddingIdentity(provider="ollama", model="nomic-embed-text", dimensions=DIMENSIONS)
SECTIONS = ("Get in", "Get around", "Sleep", "Stay safe", "Understand", "See", "Do", "Eat", "Drink")


def passage(destination, section, number=1, **overrides):
    article = destination.replace(" ", "_")
    values = {
        "id": f"{article}/{section}/{number}",
        "destination": destination,
        "section": section,
        "title": destination,
        "url": f"https://en.wikivoyage.org/wiki/{article}",
        "revision_id": 1000 + number,
        "license": "CC BY-SA 4.0",
        "language": "en",
        "valid_from": date(2026, 1, 1),
        "valid_until": date(2027, 1, 1),
        "text": f"{destination} {section} guidance number {number}.",
    }
    values.update(overrides)
    return Passage(**values)


def default_passages():
    """Tokyo and New York City in every section, plus passages the filters must exclude or keep."""
    passages = [
        passage(destination, section, number)
        for destination in ("Tokyo", "New York City")
        for section in SECTIONS
        for number in (1, 2)
    ]
    passages += [
        passage("Tokyo", "See", 3, language="fr", text="Visitez le temple Senso-ji."),
        passage("Tokyo", "See", 4, valid_until=date(2026, 10, 23), text="An expired Tokyo passage."),
        passage("Tokyo", "See", 5, valid_until=date(2026, 10, 24), text="A Tokyo passage valid through today."),
        passage("Kyoto", "See", 1, text="A Kyoto passage."),
    ]
    return passages


class GuidanceIndex:
    """Passages to index; build() writes them to a store of the given kind under root."""

    def __init__(self, root, kind="file"):
        self.root = root
        self.kind = kind
        self.path = root / f"index-{kind}"
        self.destinations_file = root / "destinations.txt"
        self.passages = default_passages()
        self.aliases = {"New York City": ["NYC"]}

    def add(self, *passages):
        self.passages.extend(passages)

    def update(self, predicate, **changes):
        self.passages = [replace(p, **changes) if predicate(p) else p for p in self.passages]

    def build(self, identity=IDENTITY):
        store = create_store(self.kind, self.path, identity)
        by_destination = {}
        for p in self.passages:
            by_destination.setdefault(p.destination, []).append(p)
        for destination, passages in by_destination.items():
            store.replace(destination, passages, [fake_vector(p.text, identity.dimensions) for p in passages])
        lines = [" | ".join([name, *self.aliases.get(name, [])]) for name in by_destination]
        self.destinations_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return self

    def snapshot(self):
        """A fingerprint of the index files, to show that serving requests leaves them unchanged."""
        return {
            str(p.relative_to(self.path)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(self.path.rglob("*"))
            if p.is_file()
        }

    def env(self):
        """Settings that point an agent at this index with matching fake embeddings."""
        return {
            "RAG_ENABLED": "true",
            "RAG_STORE": self.kind,
            "RAG_INDEX_PATH": str(self.path),
            "RAG_DESTINATIONS_FILE": str(self.destinations_file),
            "EMBEDDING_DIMENSIONS": str(DIMENSIONS),
        }


def hide_chromadb(monkeypatch):
    """Make "import chromadb" raise ImportError, as if the package were not installed."""
    monkeypatch.setitem(sys.modules, "chromadb", None)
    # Forget the store module too, so that opening a Chroma index imports it, and chromadb, again.
    monkeypatch.delitem(sys.modules, "shared.rag.chroma_store", raising=False)
