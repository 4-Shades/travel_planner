"""The file-based index for the cloud deployment: committed to the repository and bundled (TP-SRS-152)."""

import dataclasses
import json
import os
from datetime import date

import numpy as np

from shared.rag.store import EmbeddingIdentity, IndexUnavailable, Passage

IDENTITY_FILE = "identity.json"
PASSAGES_FILE = "passages.jsonl"
VECTORS_FILE = "vectors.npy"


def _passage_from_json(line):
    values = json.loads(line)
    values["valid_from"] = date.fromisoformat(values["valid_from"])
    values["valid_until"] = date.fromisoformat(values["valid_until"])
    return Passage(**values)


def _passage_to_json(passage):
    values = dataclasses.asdict(passage)
    values["valid_from"] = passage.valid_from.isoformat()
    values["valid_until"] = passage.valid_until.isoformat()
    return json.dumps(values, ensure_ascii=False)


def _write_atomically(path, write):
    temporary = path.with_name(path.name + ".tmp")
    write(temporary)
    os.replace(temporary, path)


class FileStore:
    def __init__(self, path, identity, passages, vectors):
        self.path = path
        self.identity = identity
        self.passages = passages
        self.vectors = vectors

    @classmethod
    def open(cls, path):
        try:
            identity = EmbeddingIdentity(**json.loads((path / IDENTITY_FILE).read_text(encoding="utf-8")))
            lines = (path / PASSAGES_FILE).read_text(encoding="utf-8").splitlines()
            vectors = np.load(path / VECTORS_FILE)
        except FileNotFoundError:
            raise IndexUnavailable(f"no guidance index at {path}") from None
        return cls(path, identity, [_passage_from_json(line) for line in lines if line], vectors)

    @classmethod
    def create(cls, path, identity):
        if (path / IDENTITY_FILE).exists():
            store = cls.open(path)
            if store.identity != identity:
                raise ValueError(f"The index at {path} was built with {store.identity}, not {identity}")
            return store
        path.mkdir(parents=True, exist_ok=True)
        store = cls(path, identity, [], np.zeros((0, identity.dimensions), dtype=np.float32))
        store._save()
        return store

    def destinations(self):
        return {p.destination for p in self.passages}

    def count(self):
        return len(self.passages)

    def search(self, vector, destination, sections, language, today, k):
        rows = [
            i
            for i, p in enumerate(self.passages)
            if p.destination == destination and p.section in sections and p.language == language and p.is_valid_on(today)
        ]
        if not rows:
            return []
        candidates = self.vectors[rows]
        query = np.asarray(vector, dtype=np.float32)
        scores = candidates @ query / (np.linalg.norm(candidates, axis=1) * np.linalg.norm(query) + 1e-12)
        best = np.argsort(-scores, kind="stable")[:k]
        return [self.passages[rows[i]] for i in best]

    def replace(self, destination, passages, vectors):
        """Swap a destination's passages for new ones (TP-SRS-103)."""
        keep = [i for i, p in enumerate(self.passages) if p.destination != destination]
        new_vectors = np.asarray(vectors, dtype=np.float32).reshape(len(passages), self.identity.dimensions)
        self.passages = [self.passages[i] for i in keep] + list(passages)
        self.vectors = np.concatenate([self.vectors[keep], new_vectors])
        self._save()

    def _save(self):
        identity = json.dumps(dataclasses.asdict(self.identity))
        _write_atomically(self.path / IDENTITY_FILE, lambda p: p.write_text(identity + "\n", encoding="utf-8"))
        lines = "".join(_passage_to_json(p) + "\n" for p in self.passages)
        _write_atomically(self.path / PASSAGES_FILE, lambda p: p.write_text(lines, encoding="utf-8"))

        def write_vectors(p):
            with open(p, "wb") as file:
                np.save(file, self.vectors)

        _write_atomically(self.path / VECTORS_FILE, write_vectors)
