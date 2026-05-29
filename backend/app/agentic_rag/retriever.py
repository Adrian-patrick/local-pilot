from __future__ import annotations

import math
import re
from collections import Counter

from ..rag.retriever import terms
from .models import RetrievalResult


TOP_K = 10


def retrieve(question: str, chunks: list[dict], top_k: int = TOP_K) -> list[dict]:
    results = hybrid_retrieve(question, chunks, top_k=top_k)
    return [result.chunk for result in results]


def hybrid_retrieve(question: str, chunks: list[dict], top_k: int = TOP_K) -> list[RetrievalResult]:
    if not chunks:
        return []

    query_terms = terms(question)
    if not query_terms:
        return [RetrievalResult(chunk=chunk, score=1.0, reason="default-order") for chunk in chunks[:top_k]]

    sparse_scores = _bm25_scores(query_terms, chunks)
    dense_scores = _term_vector_scores(query_terms, chunks)
    exact_scores = [_exact_match_score(question, chunk["text"]) for chunk in chunks]
    metadata_scores = [_metadata_score(query_terms, chunk.get("metadata") or {}) for chunk in chunks]

    scored: list[RetrievalResult] = []
    for index, chunk in enumerate(chunks):
        score = (
            0.58 * sparse_scores[index]
            + 0.28 * dense_scores[index]
            + exact_scores[index]
            + metadata_scores[index]
        )
        if score > 0:
            scored.append(
                RetrievalResult(
                    chunk=chunk,
                    score=score,
                    reason=_score_reason(sparse_scores[index], dense_scores[index], exact_scores[index], metadata_scores[index]),
                )
            )

    ranked = sorted(scored, key=lambda item: item.score, reverse=True)
    if not ranked:
        ranked = [RetrievalResult(chunk=chunk, score=0.1, reason="fallback") for chunk in chunks[:top_k]]

    expanded = _expand_neighbors(ranked[:top_k], chunks, question)
    return expanded[:top_k]


def _bm25_scores(query_terms: list[str], chunks: list[dict]) -> list[float]:
    docs = [terms(chunk["text"]) for chunk in chunks]
    document_frequency = Counter(term for doc in docs for term in set(doc))
    total_documents = len(chunks)
    average_length = max(1.0, sum(len(doc) for doc in docs) / max(1, total_documents))

    scores = []
    for doc in docs:
        counts = Counter(doc)
        length = max(1, len(doc))
        score = 0.0
        for term in set(query_terms):
            if term not in counts:
                continue
            df = document_frequency.get(term, 0)
            idf = math.log(1 + (total_documents - df + 0.5) / (df + 0.5))
            tf = counts[term]
            k1 = 1.5
            b = 0.75
            denominator = tf + k1 * (1 - b + b * length / average_length)
            score += idf * ((tf * (k1 + 1)) / denominator)
        scores.append(score)
    return _normalize(scores)


def _term_vector_scores(query_terms: list[str], chunks: list[dict]) -> list[float]:
    query_counter = Counter(query_terms)
    scores = []
    for chunk in chunks:
        doc_counter = Counter(terms(chunk["text"]))
        scores.append(_cosine(query_counter, doc_counter))
    return scores


def _cosine(left: Counter, right: Counter) -> float:
    common = set(left) & set(right)
    numerator = sum(left[key] * right[key] for key in common)
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    if not left_norm or not right_norm:
        return 0.0
    return numerator / (left_norm * right_norm)


def _exact_match_score(question: str, text: str) -> float:
    lowered_text = text.lower()
    score = 0.0
    for phrase in re.findall(r'"([^"]+)"', question):
        if phrase.lower() in lowered_text:
            score += 1.5
    query = question.lower().strip()
    if len(query) >= 8 and query in lowered_text:
        score += 2.0
    return score


def _metadata_score(query_terms: list[str], metadata: dict) -> float:
    section = str(metadata.get("section") or "").lower()
    if not section:
        return 0.0
    return len(set(query_terms) & set(terms(section))) * 0.35


def _expand_neighbors(results: list[RetrievalResult], chunks: list[dict], question: str) -> list[RetrievalResult]:
    if not _is_broad_question(question):
        return _unique_results(results)

    by_key = {(chunk["source"], int(chunk["chunk_index"])): chunk for chunk in chunks}
    expanded: list[RetrievalResult] = []
    for result in results:
        expanded.append(result)
        source = result.chunk["source"]
        index = int(result.chunk["chunk_index"])
        for neighbor_index in (index - 1, index + 1):
            neighbor = by_key.get((source, neighbor_index))
            if neighbor:
                expanded.append(RetrievalResult(chunk=neighbor, score=result.score * 0.72, reason="neighbor-context"))
    return _unique_results(expanded)


def _is_broad_question(question: str) -> bool:
    lowered = question.lower()
    return bool(
        "summar" in lowered
        or "key point" in lowered
        or "what is this" in lowered
        or "what are" in lowered
        or "who is" in lowered
        or "overview" in lowered
    )


def _unique_results(results: list[RetrievalResult]) -> list[RetrievalResult]:
    unique = []
    seen: set[tuple[str, int]] = set()
    for result in results:
        key = (result.chunk["source"], int(result.chunk["chunk_index"]))
        if key in seen:
            continue
        seen.add(key)
        unique.append(result)
    return unique


def _normalize(scores: list[float]) -> list[float]:
    if not scores:
        return []
    highest = max(scores)
    if highest <= 0:
        return scores
    return [score / highest for score in scores]


def _score_reason(sparse: float, dense: float, exact: float, metadata: float) -> str:
    parts = []
    if sparse:
        parts.append("bm25")
    if dense:
        parts.append("term-vector")
    if exact:
        parts.append("exact")
    if metadata:
        parts.append("section")
    return "+".join(parts) or "unknown"
