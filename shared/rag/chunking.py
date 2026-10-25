"""Splitting article sections into passages of about 300 tokens (TP-SRS-101).

A token is a word or a punctuation mark. Passages end at sentence boundaries and hold at most
MAX_TOKENS; every passage but a section's last holds at least MIN_TOKENS.
"""

import re

TARGET_TOKENS = 300
MAX_TOKENS = 350
MIN_TOKENS = 200
# Sentences longer than this are split between words. Keeping every piece at or below
# MAX_TOKENS - MIN_TOKENS guarantees that a passage closed early still holds MIN_TOKENS.
_MAX_PIECE = MAX_TOKENS - MIN_TOKENS

_TOKEN = re.compile(r"\w+|[^\w\s]")
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


def count_tokens(text):
    return len(_TOKEN.findall(text))


def _pieces(text):
    for sentence in _SENTENCE_END.split(text):
        if count_tokens(sentence) <= _MAX_PIECE:
            yield sentence
            continue
        words, size = [], 0
        for word in sentence.split():
            tokens = count_tokens(word)
            if words and size + tokens > _MAX_PIECE:
                yield " ".join(words)
                words, size = [], 0
            words.append(word)
            size += tokens
        if words:
            yield " ".join(words)


def chunk_text(text):
    text = " ".join(text.split())
    if not text:
        return []
    chunks, current, size = [], [], 0
    for piece in _pieces(text):
        tokens = count_tokens(piece)
        if current and size + tokens > MAX_TOKENS:
            chunks.append(" ".join(current))
            current, size = [], 0
        current.append(piece)
        size += tokens
        if size >= TARGET_TOKENS:
            chunks.append(" ".join(current))
            current, size = [], 0
    if current:
        chunks.append(" ".join(current))
    return chunks
