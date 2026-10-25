"""Retrieving guidance for a specialist. Retrieval never turns a plan into an error (TP-SRS-181)."""

import asyncio
from collections import OrderedDict
from datetime import date

from shared.rag.destinations import alias_map, load_destinations
from shared.rag.store import EmbeddingIdentity, IndexUnavailable, open_store

# Each specialist reads only its own sections (TP-SRS-081).
AGENT_SECTIONS = {
    "flight": ("Get in", "Get around"),
    "stay": ("Sleep", "Stay safe", "Understand"),
    "activities": ("See", "Do", "Eat", "Drink"),
}
LANGUAGE = "en"
CACHE_SIZE = 256


class Retriever:
    def __init__(self, store, embedder, aliases, top_k, timeout, logger):
        self.store = store
        self.embedder = embedder
        self.aliases = aliases
        self.top_k = top_k
        self.timeout = timeout
        self.logger = logger
        self.destinations = store.destinations()
        # Keyed by agent, destination, and day; least recently used first (TP-SRS-143).
        self._cache = OrderedDict()

    @property
    def cache_size(self):
        return len(self._cache)

    async def guidance(self, service, destination):
        """Return up to top_k passages, or none when anything goes wrong."""
        name = self.aliases.get(destination, destination)
        if name not in self.destinations:
            # No embedding call for a destination the index does not cover (TP-SRS-084).
            self.logger.info("Planning without guidance: %s is not in the guidance index", destination)
            return []
        today = date.today()
        key = (service, name, today)
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        try:
            passages = await asyncio.wait_for(self._lookup(service, name, today), self.timeout)
        except TimeoutError:
            self.logger.warning("Planning without guidance: the lookup took longer than RAG_TIMEOUT_SECONDS (%s s)", self.timeout)
            return []
        except Exception as error:
            self.logger.warning("Planning without guidance: %s: %s", type(error).__name__, error)
            return []
        self._cache[key] = passages
        if len(self._cache) > CACHE_SIZE:
            self._cache.popitem(last=False)
        return passages

    async def _lookup(self, service, destination, today):
        sections = AGENT_SECTIONS[service]
        [vector] = await self.embedder.embed([f"{destination}: {', '.join(sections)}"])
        # The stores are synchronous; a thread keeps a slow lookup from blocking other requests.
        return await asyncio.to_thread(self.store.search, vector, destination, sections, LANGUAGE, today, self.top_k)


class DisabledRetriever:
    """Used when there is no usable index: every plan is made without guidance, and says why."""

    def __init__(self, reason, logger):
        self.reason = reason
        self.logger = logger

    async def guidance(self, service, destination):
        self.logger.info("Planning without guidance: %s", self.reason)
        return []


def create_retriever(settings, embedder, logger):
    if not settings.rag_enabled:
        return DisabledRetriever("retrieval is switched off by RAG_ENABLED", logger)
    try:
        store = open_store(settings.rag_store, settings.rag_index_path)
    except IndexUnavailable as error:
        logger.warning("Guidance retrieval disabled: %s", error)
        return DisabledRetriever(str(error), logger)
    except ImportError as error:
        reason = f"{error.name or 'a vector store package'} is not installed"
        logger.warning("Guidance retrieval disabled: %s", reason)
        return DisabledRetriever(reason, logger)

    configured = EmbeddingIdentity(settings.llm_provider, settings.embedding_model, settings.embedding_dimensions)
    if store.identity != configured:
        # Vectors from different models cannot be compared (TP-SRS-086).
        logger.warning(
            "Guidance retrieval disabled: the index was built with %s, but the agent is configured for %s",
            store.identity,
            configured,
        )
        return DisabledRetriever("the index's embedding identity differs from the configured one", logger)

    try:
        aliases = alias_map(load_destinations(settings.rag_destinations_file))
    except FileNotFoundError:
        logger.warning("No destination file at %s; destination aliases are unavailable", settings.rag_destinations_file)
        aliases = {}
    return Retriever(store, embedder, aliases, settings.rag_top_k, settings.rag_timeout_seconds, logger)
