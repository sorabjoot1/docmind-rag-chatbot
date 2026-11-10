"""
embeddings.py - Loads the embedding model once and reuses it everywhere.
"""
import threading

from langchain_community.embeddings import HuggingFaceEmbeddings

import config

_embeddings = None
_lock = threading.Lock()


def get_embeddings():
    """Create the embedding model the first time it is needed, then reuse it."""
    global _embeddings
    if _embeddings is None:
        with _lock:
            if _embeddings is None:
                _embeddings = HuggingFaceEmbeddings(model_name=config.EMBEDDING_MODEL)
    return _embeddings
