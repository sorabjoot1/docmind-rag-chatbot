"""
hybrid_search.py - Hybrid retrieval = semantic score + keyword score.

Same method as the original pipeline:
    final_score = alpha * semantic_score + (1 - alpha) * keyword_score
Keyword statistics are prepared once, so each question only does the cheap part.
"""
import re

import numpy as np

import config

WORD_RE = re.compile(r"\w+")


class HybridRetriever:
    def __init__(self, vector_store, texts, metadatas):
        self.vector_store = vector_store
        self.texts = texts
        self.metadatas = metadatas
        # Prepared once (not on every question):
        self._lower = [t.lower() for t in texts]
        self._word_counts = [len(WORD_RE.findall(t)) for t in texts]
        self._key_to_idx = {
            (m["technique"], m["chunk_index"]): i for i, m in enumerate(metadatas)
        }

    def search(self, query, k=3, alpha=0.5):
        n = len(self.texts)
        if n == 0:
            return []

        # 1) Semantic scores (vector search on the best candidates)
        candidates = min(n, config.SEMANTIC_CANDIDATES)
        semantic_results = self.vector_store.similarity_search_with_relevance_scores(
            query, k=candidates
        )

        # 2) Keyword scores (word counts, normalised by chunk length, then by the max)
        words = [w.lower() for w in WORD_RE.findall(query) if len(w) > 2]
        keyword_scores = []
        for text_lower, word_count in zip(self._lower, self._word_counts):
            score = sum(text_lower.count(w) for w in words)
            keyword_scores.append(score / word_count if word_count else 0.0)
        max_kw = max(keyword_scores)
        keyword_scores = [s / max_kw for s in keyword_scores] if max_kw > 0 else [0.0] * n

        # 3) Combine
        combined = [(1 - alpha) * s for s in keyword_scores]
        for doc, score in semantic_results:
            key = (doc.metadata.get("technique"), doc.metadata.get("chunk_index"))
            idx = self._key_to_idx.get(key)
            if idx is not None:
                combined[idx] += alpha * max(0.0, min(1.0, score))

        # 4) Top-k (the same text can exist in several techniques - keep it only once)
        results, seen = [], set()
        for idx in np.argsort(combined)[::-1]:
            text = self.texts[idx]
            if text in seen:
                continue
            seen.add(text)
            results.append(
                {"text": text, "metadata": self.metadatas[idx], "score": float(combined[idx])}
            )
            if len(results) == k:
                break
        return results
