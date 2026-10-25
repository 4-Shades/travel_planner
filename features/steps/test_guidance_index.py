"""Steps for features/ingest/guidance_index.feature (BDD scenarios §5.2)."""

import re
from datetime import date, timedelta

import pytest
from freezegun import freeze_time
from pytest_bdd import given, parsers, scenarios, then, when

from shared.rag import EmbeddingIdentity, open_store
from shared.rag.chunking import MAX_TOKENS, MIN_TOKENS, count_tokens
from shared.rag.ingest import main as ingest_main
from tests.fakes.llm import PROVIDER_ENV, FakeEmbedder
from tests.fakes.mediawiki import FakeMediaWiki, article

scenarios("ingest/guidance_index.feature")


class IngestRun:
    """The ingest command, run in a temporary directory against the fake MediaWiki API."""

    def __init__(self, tmp_path, monkeypatch, capsys):
        self.tmp_path = tmp_path
        self.capsys = capsys
        self.stderr = ""
        self.monkeypatch = monkeypatch
        self.wiki = None
        self.destinations_file = tmp_path / "destinations.txt"
        self.provider = "openai"
        self.store = "file"
        self.exit_code = None
        self.requests_before = 0
        self.counts = {}

    @property
    def index_path(self):
        return self.tmp_path / f"index-{self.store}"

    def run(self, *args):
        for name, value in {**PROVIDER_ENV[self.provider], "EMBEDDING_DIMENSIONS": "8"}.items():
            self.monkeypatch.setenv(name, value)
        self.requests_before = len(self.wiki.titles_requested)
        argv = [
            *args,
            "--store", self.store,
            "--index-path", str(self.index_path),
            "--destinations-file", str(self.destinations_file),
            "--cache-dir", str(self.tmp_path / "cache"),
        ]
        self.exit_code = ingest_main(argv)
        self.stderr = self.capsys.readouterr().err
        return self.exit_code

    @property
    def last_titles(self):
        return self.wiki.titles_requested[self.requests_before :]

    def passages(self):
        store = open_store(self.store, self.index_path)
        if hasattr(store, "passages"):
            return store.passages
        from shared.rag.chroma_store import _passage

        result = store.collection.get(include=["documents", "metadatas"])
        return [_passage(i, d, m) for i, d, m in zip(result["ids"], result["documents"], result["metadatas"])]


@pytest.fixture
def clock():
    with freeze_time("2026-10-24", tick=True) as frozen:
        yield frozen


@pytest.fixture
def ingest(tmp_path, monkeypatch, capsys, fake_router, clock):
    FakeEmbedder(fake_router, "openai", dimensions=8)
    FakeEmbedder(fake_router, "ollama", dimensions=8)
    return IngestRun(tmp_path, monkeypatch, capsys)


def names(text):
    """'"Tokyo" and "Kyoto"' or '"Understand", "Get in", and "See"' -> the quoted names."""
    return re.findall(r'"([^"]+)"', text)


# Givens


@given(parsers.re(r"the MediaWiki API is a fake with articles for (?P<titles>.+)"))
def fake_mediawiki(ingest, fake_router, titles):
    ingest.wiki = FakeMediaWiki(fake_router, [article(title) for title in names(titles)])


@given(parsers.re(r'"data/rag/destinations.txt" lists (?P<titles>.+)'))
def destinations_file(ingest, titles):
    ingest.destinations_file.write_text("\n".join(names(titles)) + "\n", encoding="utf-8")


@given(parsers.parse('today is "{day}"'))
def today_is(clock, day):
    clock.move_to(day)


@given(parsers.re(r"the Tokyo article has the sections (?P<sections>.+)"))
def article_sections(ingest, sections):
    ingest.wiki.articles["Tokyo"] = article("Tokyo", sections=tuple(names(sections)))


@given("I have run the ingest command")
def have_run(ingest):
    assert ingest.run() == 0
    ingest.counts["Tokyo"] = sum(p.destination == "Tokyo" for p in ingest.passages())


@given("the Tokyo article has a new revision")
def new_revision(ingest):
    ingest.wiki.set_revision("Tokyo", 2000)


@given(parsers.parse("I ran the ingest command {days:d} days ago"))
@given(parsers.parse("I ran the ingest command {days:d} day ago"))
def ran_days_ago(ingest, clock, days):
    today = date(2026, 10, 24)
    clock.move_to(today - timedelta(days=days))
    assert ingest.run() == 0
    clock.move_to(today)


@given(parsers.parse('the embedding provider is "{provider}"'))
def embedding_provider(ingest, provider):
    ingest.provider = provider


# Whens


@when("I run the ingest command")
def run_ingest(ingest):
    ingest.run()


@when(parsers.parse('I run the ingest command for "{destination}" with a fresh download'))
def run_fresh(ingest, destination):
    ingest.run(destination, "--refresh")


@when("I run the ingest command with the refresh option")
def run_refresh(ingest):
    ingest.run("--refresh")


@when(parsers.parse('I run the ingest command for "{destination}"'))
def run_for(ingest, destination):
    ingest.run(destination)


@when(parsers.parse("I run the ingest command with the {store} store"))
def run_with_store(ingest, store):
    ingest.store = store.lower()
    ingest.run()


# Thens


@then(parsers.re(r"the index holds passages for (?P<titles>.+)"))
def index_holds(ingest, titles):
    assert ingest.exit_code == 0
    assert {p.destination for p in ingest.passages()} == set(names(titles))


@then(parsers.re(r"the index holds Tokyo passages from (?P<sections>.+)"))
def tokyo_sections(ingest, sections):
    assert {p.section for p in ingest.passages() if p.destination == "Tokyo"} == set(names(sections))


@then(parsers.re(r"the index holds no passages from (?P<sections>.+)"))
def no_sections(ingest, sections):
    assert not {p.section for p in ingest.passages()} & set(names(sections))


@then("every passage is about 300 tokens long")
def about_300_tokens(ingest):
    by_section = {}
    for p in ingest.passages():
        by_section.setdefault((p.destination, p.section), []).append(p)
    for passages in by_section.values():
        sizes = [count_tokens(p.text) for p in sorted(passages, key=lambda p: int(p.id.rsplit("/", 1)[1]))]
        assert all(size <= MAX_TOKENS for size in sizes)
        assert all(size >= MIN_TOKENS for size in sizes[:-1])


@then(
    "every passage records its destination, section, title, source URL, revision ID, license, language, and validity dates"
)
def passages_described(ingest):
    passages = ingest.passages()
    assert passages
    for p in passages:
        assert all([p.destination, p.section, p.title, p.url, p.revision_id, p.license, p.language])
        assert p.valid_from and p.valid_until


@then(parsers.parse('every passage is valid from "{start}" until "{end}"'))
def validity(ingest, start, end):
    assert {(p.valid_from, p.valid_until) for p in ingest.passages()} == {
        (date.fromisoformat(start), date.fromisoformat(end))
    }


@then("the number of Tokyo passages is the same as before")
def same_count(ingest):
    assert sum(p.destination == "Tokyo" for p in ingest.passages()) == ingest.counts["Tokyo"]


@then("every Tokyo passage has the new revision ID")
def new_revision_id(ingest):
    assert {p.revision_id for p in ingest.passages() if p.destination == "Tokyo"} == {2000}


@then("the MediaWiki API is not called")
def api_not_called(ingest):
    assert ingest.last_titles == []


@then("the MediaWiki API is called")
def api_called(ingest):
    assert ingest.last_titles


@then(parsers.re(r"the MediaWiki API is called for (?P<titles>.+)"))
def api_called_for(ingest, titles):
    assert sorted(ingest.last_titles) == sorted(names(titles))


@then(parsers.parse('the MediaWiki API is called only for "{title}"'))
def api_called_only_for(ingest, title):
    assert ingest.last_titles == [title]


@then(parsers.parse("a {store} index is built"))
def index_built(ingest, store):
    assert ingest.exit_code == 0
    assert type(open_store(store.lower(), ingest.index_path)).__name__ == {"chroma": "ChromaStore", "file": "FileStore"}[store.lower()]


@then("the index records the embedding provider, model, and vector size")
def identity_recorded(ingest):
    assert open_store(ingest.store, ingest.index_path).identity == EmbeddingIdentity("openai", "text-embedding-3-small", 8)


@then("the command fails with a message that the cloud index needs OpenAI embeddings")
def refuses(ingest):
    assert ingest.exit_code == 2
    assert "needs OpenAI embeddings" in ingest.stderr


@then("no index files are written")
def nothing_written(ingest):
    assert not ingest.index_path.exists()


@then("every MediaWiki request has a User-Agent header that includes a contact URL")
def user_agent(ingest):
    assert ingest.wiki.user_agents
    assert all(re.search(r"\(https?://\S+\)", agent) for agent in ingest.wiki.user_agents)
