"""Steps for features/rag/guidance_retrieval.feature (BDD scenarios §5.1)."""

import asyncio
import re
from datetime import date, timedelta
from itertools import product

import pytest
from freezegun import freeze_time
from pytest_bdd import given, parsers, scenarios, then, when

from shared.rag import DisabledRetriever, EmbeddingIdentity
from shared.rag.guidance import GUIDANCE_INSTRUCTION, MAX_GUIDANCE_CHARS, MAX_PASSAGE_CHARS
from shared.schemas import SPECIALISTS
from tests import factories
from tests.asgi import AppClient
from tests.fakes.index import GuidanceIndex, hide_chromadb, passage
from tests.fakes.llm import PROVIDER_ENV, FakeEmbedder

from features.conftest import SERVICES

scenarios("rag/guidance_retrieval.feature")

GUIDANCE_BLOCK = re.compile(r"<guidance>\n(.*?)\n</guidance>", re.S)
HEADING = re.compile(r"^\[(?P<title>[^\]:]+): (?P<section>[^\]]+)\]$", re.M)
MARKER = re.compile(r"<\s*/?\s*guidance\s*>", re.I)


class Retrieval:
    """The scenario's index, settings, and agents. Agents are built, and the index written, on first use."""

    def __init__(self, agent_app, index, monkeypatch):
        self._agent_app = agent_app
        self._monkeypatch = monkeypatch
        self.index = index
        self.env = {}
        self.build_index = True
        self.index_identity = None
        self.hide_chromadb = False
        self.apps = {}
        self.service = None

    def app(self, service):
        if service not in self.apps:
            if self.build_index and not self.apps:
                self.index.build(**({"identity": self.index_identity} if self.index_identity else {}))
            if self.hide_chromadb:
                hide_chromadb(self._monkeypatch)
            self.apps[service] = self._agent_app(service, **PROVIDER_ENV["ollama"], **{**self.index.env(), **self.env})
        return self.apps[service]

    def post(self, service, destination):
        self.service = service
        return AppClient(self.app(service)).post("/run", json=factories.valid_request(destination=destination))


@pytest.fixture
def clock():
    with freeze_time(factories.TODAY, tick=True) as frozen:
        yield frozen


@pytest.fixture(autouse=True)
def embedder(fake_router):
    return FakeEmbedder(fake_router, "ollama", dimensions=8)


@pytest.fixture
def retrieval(agent_app, tmp_path, monkeypatch, clock):
    index = GuidanceIndex(tmp_path, "file")
    # Only the regular Tokyo and New York City passages; scenarios add the rest.
    index.passages = [p for p in index.passages if "guidance number" in p.text]
    return Retrieval(agent_app, index, monkeypatch)


@pytest.fixture
def agent(retrieval):
    """For the shared steps that ask which agent answered."""
    return retrieval


def guidance_in(prompt):
    match = GUIDANCE_BLOCK.search(prompt)
    return match.group(1) if match else None


def passage_bodies(block):
    """Split the guidance block into its passages' texts."""
    return [body.strip("\n") for body in HEADING.split(block)[3::3]]


# Givens


@given(parsers.parse('the guidance index holds passages for "{first}" and "{second}" in every section'))
def index_holds_passages(retrieval, first, second):
    assert {p.destination for p in retrieval.index.passages} == {first, second}


@given("retrieval is enabled")
def retrieval_enabled(retrieval):
    retrieval.env["RAG_ENABLED"] = "true"


@given(parsers.re(r"RAG_TOP_K is (?P<value>\d+)$"))
def rag_top_k(retrieval, value):
    retrieval.env["RAG_TOP_K"] = value


@given("RAG_TOP_K is not set")
def rag_top_k_unset(retrieval):
    retrieval.env.pop("RAG_TOP_K", None)


@given("the guidance index also holds these passages for the Activities agent:")
def index_also_holds(retrieval, datatable):
    header, *rows = datatable
    assert header == ["destination", "language", "valid until", "text"]
    for number, (destination, language, valid_until, text) in enumerate(rows, start=100):
        retrieval.index.add(
            passage(destination, "See", number, language=language, valid_until=date.fromisoformat(valid_until), text=text)
        )


@given(parsers.parse('the destination file lists "{alias}" as an alias for "{name}"'))
def destination_alias(retrieval, alias, name):
    retrieval.index.aliases[name] = [alias]


@given("no guidance index exists")
def no_index(retrieval):
    retrieval.build_index = False


@given("the vector store package is not installed")
def package_missing(retrieval):
    retrieval.index = GuidanceIndex(retrieval.index.root, "chroma")
    retrieval.hide_chromadb = True


@given("the embedding call fails")
def embedding_fails(embedder):
    embedder.fail(500)


@given("the lookup takes longer than RAG_TIMEOUT_SECONDS")
def lookup_slow(retrieval, monkeypatch):
    async def slow_embed(self, texts):
        await asyncio.sleep(5)

    monkeypatch.setattr("shared.llm.OllamaClient.embed", slow_embed)
    retrieval.env["RAG_TIMEOUT_SECONDS"] = "0.2"


@given(parsers.parse('the guidance index was built with embedding model "{model}" of size {size:d}'))
def index_identity(retrieval, model, size):
    retrieval.index_identity = EmbeddingIdentity("ollama", model, size)


@given(parsers.parse('the agent is configured for embedding model "{model}" of size {size:d}'))
def agent_identity(retrieval, model, size):
    retrieval.env.update(EMBEDDING_MODEL=model, EMBEDDING_DIMENSIONS=str(size))


@given(parsers.parse('a Tokyo "{section}" passage contains the text "{text}"'))
def passage_with_text(retrieval, section, text):
    retrieval.index.update(lambda p: p.destination == "Tokyo" and p.section == section, text=text)


@given("every Tokyo passage is 1,000 characters long")
def long_passages(retrieval):
    retrieval.index.update(lambda p: p.destination == "Tokyo", text="z" * 1000)


@given(parsers.parse('the language model\'s answer also contains a source with URL "{url}"'))
def model_adds_source(language_model, url):
    made_up = {"title": "Made up", "url": url, "license": "none"}
    language_model.answer({"activities": [factories.activity_offer()], "sources": [made_up]})


# Whens


@when(parsers.re(r'I post a travel request to "(?P<destination>[^"]+)" to the (?P<name>\w+) agent$'), target_fixture="response")
def post_request(retrieval, destination, name):
    return retrieval.post(SERVICES[name], destination)


@when(parsers.re(r'I post a travel request to "(?P<destination>[^"]+)" to the (?P<name>\w+) agent twice$'), target_fixture="response")
def post_request_twice(retrieval, destination, name):
    retrieval.post(SERVICES[name], destination)
    return retrieval.post(SERVICES[name], destination)


@when(parsers.parse("the {name} agent starts"))
def agent_starts(retrieval, name):
    retrieval.app(SERVICES[name])


@when("the date changes to tomorrow")
def date_changes(clock):
    clock.move_to(date.fromisoformat(factories.TODAY) + timedelta(days=1))


@when("retrieval runs for 257 different agent, destination, and day combinations")
def many_lookups(retrieval, clock):
    retriever = retrieval.app("activities").state.retriever
    start = date.fromisoformat(factories.TODAY)
    combinations = list(product(range(43), SPECIALISTS, ("Tokyo", "New York City")))[:257]

    async def run():
        for day, service, destination in combinations:
            clock.move_to(start + timedelta(days=day))
            await retriever.guidance(service, destination)

    asyncio.run(run())


@when(parsers.parse('I post {count:d} travel requests to "{destination}" to each specialist'))
def post_many(retrieval, count, destination):
    retrieval.app("activities")
    retrieval.snapshot = retrieval.index.snapshot()
    for service in SPECIALISTS:
        for _ in range(count):
            retrieval.post(service, destination)


# Thens


@then(parsers.parse("the prompt contains at most {count:d} guidance passages"))
def at_most_passages(language_model, count):
    headings = HEADING.findall(guidance_in(language_model.prompts[-1]) or "")
    assert 1 <= len(headings) <= count


@then(parsers.parse("every guidance passage in the prompt comes from one of these sections: {sections}"))
def passages_from_sections(language_model, sections):
    used = {section for _, section in HEADING.findall(guidance_in(language_model.prompts[-1]) or "")}
    assert used and used <= {s.strip() for s in sections.split(",")}


@then(parsers.parse('the prompt contains guidance about "{name}"'))
def guidance_about(language_model, name):
    titles = {title for title, _ in HEADING.findall(guidance_in(language_model.prompts[-1]) or "")}
    assert titles == {name}


@then("no embedding call is made")
def no_embedding(embedder):
    assert embedder.call_count == 0


@then("one embedding call is made")
def one_embedding(embedder):
    assert embedder.call_count == 1


@then("a second embedding call is made")
def second_embedding(embedder):
    assert embedder.call_count == 2


@then("the prompt contains no guidance")
def no_guidance(language_model):
    assert guidance_in(language_model.prompts[-1]) is None


@then("the response has no error")
def no_error(response):
    assert response.json()["error"] is None


@then("the response has no sources")
def no_sources(response):
    assert response.json()["sources"] == []


@then("the agent logs why it planned without guidance")
def logs_why(caplog):
    assert any(r.getMessage().startswith("Planning without guidance: ") for r in caplog.records)


@then("retrieval is disabled")
def retrieval_is_disabled(retrieval):
    assert isinstance(retrieval.app("activities").state.retriever, DisabledRetriever)


@then("the agent logs both embedding identities")
def logs_identities(caplog):
    warnings = [r.getMessage() for r in caplog.records if r.levelname == "WARNING"]
    assert any("model-a" in m and "768" in m and "model-b" in m and "1536" in m for m in warnings), warnings


@then(parsers.parse('the guidance in the prompt is inside one pair of "{marker}" markers'))
def one_pair_of_markers(language_model, marker):
    prompt = language_model.prompts[-1]
    assert marker == "<guidance>"
    assert guidance_in(prompt) is not None
    assert len(MARKER.findall(prompt)) == 2


@then("the prompt tells the model to treat the guidance as reference only")
def reference_only(language_model):
    assert GUIDANCE_INSTRUCTION in language_model.prompts[-1]
    assert "reference only" in GUIDANCE_INSTRUCTION


@then("the guidance text contains no other copies of the markers")
def no_marker_copies(language_model):
    assert not MARKER.search(guidance_in(language_model.prompts[-1]))


@then("each guidance passage in the prompt is at most 700 characters")
def passage_limit(language_model):
    bodies = passage_bodies(guidance_in(language_model.prompts[-1]))
    assert bodies and all(len(body) <= MAX_PASSAGE_CHARS == 700 for body in bodies)


@then("all guidance in the prompt is at most 2,400 characters")
def total_limit(language_model):
    assert len(guidance_in(language_model.prompts[-1])) <= MAX_GUIDANCE_CHARS == 2400


@then("the response sources are the sources of the passages in the prompt")
def sources_match_prompt(retrieval, language_model, response):
    block = guidance_in(language_model.prompts[-1])
    used = [p for p in retrieval.index.passages if p.text in block]
    assert used
    assert {(s["title"], s["url"], s["license"]) for s in response.json()["sources"]} == {
        (p.title, p.url, p.license) for p in used
    }


@then("every source has a title, a URL, and a license")
def sources_complete(response):
    sources = response.json()["sources"]
    assert sources and all(s["title"] and s["url"] and s["license"] for s in sources)


@then(parsers.parse('the response sources do not include "{url}"'))
def sources_exclude(response, url):
    assert url not in {s["url"] for s in response.json()["sources"]}


@then("the schema sent to the model has no field for sources")
def schema_without_sources(language_model):
    assert "sources" not in language_model.requests[-1]["format"]["properties"]


@then(parsers.parse("the retrieval cache holds {count:d} entries"))
def cache_size(retrieval, count):
    assert retrieval.app("activities").state.retriever.cache_size == count


@then("the guidance index is unchanged")
def index_unchanged(retrieval):
    assert retrieval.index.snapshot() == retrieval.snapshot
