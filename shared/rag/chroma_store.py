"""The Chroma index for the self-hosted deployment (TP-SRS-106). Needs the optional chromadb package."""

from datetime import date

import chromadb
from chromadb.config import Settings as ChromaSettings
from chromadb.errors import NotFoundError

from shared.rag.store import EmbeddingIdentity, IndexUnavailable, Passage

COLLECTION = "guidance"
_BATCH = 1000


def _client(path):
    # Chroma's anonymous usage reports would be network calls; the application makes none it doesn't need.
    return chromadb.PersistentClient(path=str(path), settings=ChromaSettings(anonymized_telemetry=False))


def _metadata(passage):
    return {
        "destination": passage.destination,
        "section": passage.section,
        "title": passage.title,
        "url": passage.url,
        "revision_id": passage.revision_id,
        "license": passage.license,
        "language": passage.language,
        # Dates are stored as day numbers so that Chroma can compare them.
        "valid_from": passage.valid_from.toordinal(),
        "valid_until": passage.valid_until.toordinal(),
    }


def _passage(passage_id, document, metadata):
    values = dict(metadata)
    values["valid_from"] = date.fromordinal(values["valid_from"])
    values["valid_until"] = date.fromordinal(values["valid_until"])
    return Passage(id=passage_id, text=document, **values)


class ChromaStore:
    def __init__(self, collection):
        self.collection = collection
        metadata = collection.metadata or {}
        self.identity = EmbeddingIdentity(metadata.get("provider"), metadata.get("model"), metadata.get("dimensions"))

    @classmethod
    def open(cls, path):
        try:
            return cls(_client(path).get_collection(COLLECTION, embedding_function=None))
        except NotFoundError:
            raise IndexUnavailable(f"no guidance index at {path}") from None

    @classmethod
    def create(cls, path, identity):
        collection = _client(path).get_or_create_collection(
            COLLECTION,
            metadata={"provider": identity.provider, "model": identity.model, "dimensions": identity.dimensions},
            configuration={"hnsw": {"space": "cosine"}},
            embedding_function=None,
        )
        store = cls(collection)
        if store.identity != identity:
            raise ValueError(f"The index at {path} was built with {store.identity}, not {identity}")
        return store

    def destinations(self):
        return {metadata["destination"] for metadata in self.collection.get(include=["metadatas"])["metadatas"]}

    def count(self):
        return self.collection.count()

    def search(self, vector, destination, sections, language, today, k):
        day = today.toordinal()
        result = self.collection.query(
            query_embeddings=[list(vector)],
            n_results=k,
            where={
                "$and": [
                    {"destination": destination},
                    {"section": {"$in": list(sections)}},
                    {"language": language},
                    {"valid_from": {"$lte": day}},
                    {"valid_until": {"$gte": day}},
                ]
            },
            include=["documents", "metadatas"],
        )
        return [
            _passage(passage_id, document, metadata)
            for passage_id, document, metadata in zip(result["ids"][0], result["documents"][0], result["metadatas"][0])
        ]

    def replace(self, destination, passages, vectors):
        """Swap a destination's passages for new ones (TP-SRS-103)."""
        self.collection.delete(where={"destination": destination})
        for start in range(0, len(passages), _BATCH):
            batch = passages[start : start + _BATCH]
            self.collection.add(
                ids=[p.id for p in batch],
                documents=[p.text for p in batch],
                metadatas=[_metadata(p) for p in batch],
                embeddings=[list(v) for v in vectors[start : start + _BATCH]],
            )
