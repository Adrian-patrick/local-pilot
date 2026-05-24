from __future__ import annotations

import math
import re
from collections import Counter


def retrieve_chunks(question: str, chunks: list[dict], top_k: int) -> list[dict]:
    if not chunks:
        return []

    query_terms = set(terms(question))
    if not query_terms:
        return chunks[:top_k]

    document_terms = [terms(chunk["text"]) for chunk in chunks]
    document_frequency = Counter(term for doc in document_terms for term in set(doc))
    total_documents = len(chunks)

    scored: list[tuple[float, dict]] = []
    for chunk, chunk_terms in zip(chunks, document_terms):
        score = _bm25_score(query_terms, chunk_terms, document_frequency, total_documents)
        score += _exact_match_score(question, chunk["text"])
        score += _metadata_score(query_terms, chunk.get("metadata") or {})
        scored.append((score, chunk))

    ranked = [chunk for score, chunk in sorted(scored, key=lambda item: item[0], reverse=True) if score > 0]
    if not ranked:
        ranked = chunks[:top_k]
    return ranked[:top_k]


def _bm25_score(
    query_terms: set[str],
    chunk_terms: list[str],
    document_frequency: Counter,
    total_documents: int,
) -> float:
    counts = Counter(chunk_terms)
    length = max(1, len(chunk_terms))
    average_length = 180
    k1 = 1.5
    b = 0.75
    score = 0.0

    for term in query_terms:
        if term not in counts:
            continue
        df = document_frequency.get(term, 0)
        idf = math.log(1 + (total_documents - df + 0.5) / (df + 0.5))
        tf = counts[term]
        denominator = tf + k1 * (1 - b + b * length / average_length)
        score += idf * ((tf * (k1 + 1)) / denominator)

    return score


def _exact_match_score(question: str, text: str) -> float:
    lowered_text = text.lower()
    query = question.lower().strip()
    score = 0.0
    if len(query) >= 8 and query in lowered_text:
        score += 4.0
    for phrase in re.findall(r'"([^"]+)"', question):
        if phrase.lower() in lowered_text:
            score += 3.0
    return score


def _metadata_score(query_terms: set[str], metadata: dict) -> float:
    section = str(metadata.get("section") or "").lower()
    if not section:
        return 0.0
    section_terms = set(terms(section))
    return len(query_terms & section_terms) * 0.75


def terms(text: str) -> list[str]:
    stopwords = {
        "about",
        "after",
        "again",
        "also",
        "because",
        "before",
        "being",
        "could",
        "document",
        "from",
        "have",
        "into",
        "only",
        "selected",
        "that",
        "their",
        "there",
        "these",
        "this",
        "using",
        "what",
        "when",
        "where",
        "which",
        "with",
        "would",
        "does",
        "who",
    }
    return [
        token
        for token in re.findall(r"[a-zA-Z0-9_+#.-]{3,}", text.lower())
        if token not in stopwords
    ]
