"""Build or refresh the guidance index from Wikivoyage (TP-SRS-100 to TP-SRS-107).

    python -m shared.rag.ingest                      # every destination in the destination file
    python -m shared.rag.ingest Tokyo NYC --refresh  # just these, downloaded again

Embeddings use the same settings as the agents (LLM_PROVIDER, EMBEDDING_MODEL, ...), so an
index built here matches the agents that read it.
"""

import argparse
import asyncio
import logging
import re
import sys
from datetime import date, timedelta
from pathlib import Path

from shared.config import ConfigError, Settings
from shared.llm import create_llm_client
from shared.rag.chunking import chunk_text
from shared.rag.destinations import alias_map, load_destinations
from shared.rag.mediawiki import DEFAULT_CONTACT_URL, LANGUAGE, LICENSE, ArticleNotFound, MediaWiki
from shared.rag.retriever import AGENT_SECTIONS
from shared.rag.store import EmbeddingIdentity, Passage, create_store

logger = logging.getLogger("travel_planner.ingest")

# Only sections some agent reads are kept (TP-SRS-101).
USED_SECTIONS = {section for sections in AGENT_SECTIONS.values() for section in sections}
EMBEDDING_BATCH = 64

_SECTION_HEADING = re.compile(r"^==\s*([^=].*?)\s*==\s*$", re.MULTILINE)
_SUBSECTION_HEADING = re.compile(r"^={3,}\s*(.*?)\s*={3,}\s*$", re.MULTILINE)


def one_year_after(day):
    """Passages expire one year after they are downloaded (TP-SRS-102); 29 February becomes 28 February."""
    try:
        return day.replace(year=day.year + 1)
    except ValueError:
        return day.replace(year=day.year + 1, day=28)


def sections_of(extract):
    """Map each level-2 section of a plain-text extract to its text, subsections included."""
    parts = _SECTION_HEADING.split(extract)
    sections = {}
    for name, body in zip(parts[1::2], parts[2::2]):
        sections[name] = _SUBSECTION_HEADING.sub(lambda m: f"{m.group(1)}.", body)
    return sections


def passages_of(destination, article):
    passages = []
    for section, text in sections_of(article.extract).items():
        if section not in USED_SECTIONS:
            continue
        for number, chunk in enumerate(chunk_text(text), start=1):
            passages.append(
                Passage(
                    id=f"{destination}/{section}/{number}",
                    destination=destination,
                    section=section,
                    title=article.title,
                    url=article.url,
                    revision_id=article.revision_id,
                    license=LICENSE,
                    language=LANGUAGE,
                    valid_from=article.downloaded,
                    valid_until=one_year_after(article.downloaded),
                    text=chunk,
                )
            )
    return passages


async def ingest(destinations, store, mediawiki, embedder):
    """Ingest each destination in turn; return the names that failed."""
    failed = []
    for destination in destinations:
        try:
            article = await mediawiki.article(destination)
            passages = passages_of(destination, article)
            vectors = []
            for start in range(0, len(passages), EMBEDDING_BATCH):
                vectors += await embedder.embed([p.text for p in passages[start : start + EMBEDDING_BATCH]])
            store.replace(destination, passages, vectors)
            logger.info("Ingested %s: %d passages from revision %s", destination, len(passages), article.revision_id)
        except ArticleNotFound as error:
            logger.warning("Skipped %s: %s", destination, error)
            failed.append(destination)
        except Exception as error:
            logger.warning("Skipped %s: %s: %s", destination, type(error).__name__, error)
            failed.append(destination)
    return failed


def parse_args(argv, settings):
    parser = argparse.ArgumentParser(prog="python -m shared.rag.ingest", description=__doc__.split("\n\n")[0])
    parser.add_argument("destinations", nargs="*", help="destinations or aliases to ingest instead of the whole file")
    parser.add_argument("--refresh", action="store_true", help="download articles again, even if cached")
    parser.add_argument("--store", choices=["chroma", "file"], default=settings.rag_store, help="index type")
    parser.add_argument("--index-path", type=Path, help="index location (default: RAG_INDEX_PATH)")
    parser.add_argument("--destinations-file", type=Path, default=Path(settings.rag_destinations_file))
    parser.add_argument("--cache-dir", type=Path, default=Path("data/rag/cache"), help="downloaded articles")
    parser.add_argument("--contact-url", default=DEFAULT_CONTACT_URL, help="contact URL sent to Wikimedia")
    args = parser.parse_args(argv)
    if args.index_path is None:
        args.index_path = Path(settings.rag_index_path if args.store == settings.rag_store else f"data/rag/index/{args.store}")
    return args


def main(argv=None):
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    try:
        settings = Settings.from_env()
    except ConfigError as error:
        print(f"Configuration error: {error}", file=sys.stderr)
        return 2
    args = parse_args(argv, settings)

    if args.store == "file" and settings.llm_provider != "openai":
        # The cloud deployment embeds queries with OpenAI, so its index must too (TP-SRS-106).
        print("The file (cloud) index needs OpenAI embeddings: set LLM_PROVIDER=openai.", file=sys.stderr)
        return 2

    known = load_destinations(args.destinations_file) if args.destinations_file.exists() else []
    if args.destinations:
        names = alias_map(known)
        destinations = [names.get(name, name) for name in args.destinations]
    elif known:
        destinations = [d.name for d in known]
    else:
        print(f"No destinations given and no destination file at {args.destinations_file}.", file=sys.stderr)
        return 2

    identity = EmbeddingIdentity(settings.llm_provider, settings.embedding_model, settings.embedding_dimensions)
    try:
        store = create_store(args.store, args.index_path, identity)
        embedder = create_llm_client(settings)
    except (ValueError, ImportError) as error:
        print(f"Cannot build the index: {error}", file=sys.stderr)
        return 2

    mediawiki = MediaWiki(args.cache_dir, contact_url=args.contact_url, refresh=args.refresh)
    failed = asyncio.run(ingest(destinations, store, mediawiki, embedder))
    if failed:
        print(f"Not ingested: {', '.join(failed)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
