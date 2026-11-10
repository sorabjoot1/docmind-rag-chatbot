"""
rag_pipeline.py - Connects all modules into one RAG workflow.

    load PDF -> chunk -> embed -> store (once, in the background)
    question -> hybrid search -> prompt pattern -> OpenRouter -> answer
"""
import logging
import threading
import time

import config
import vector_store
from chunking import build_all_chunks, flatten_chunks
from document_loader import DocumentError, load_document, locate_document
from embeddings import get_embeddings
from hybrid_search import HybridRetriever
from llm_client import generate
from prompts import DEFAULT_PATTERN, NOT_FOUND_ANSWER, PATTERNS, build_messages

logger = logging.getLogger(__name__)


class PipelineNotReady(Exception):
    pass


class RAGPipeline:
    def __init__(self):
        self._lock = threading.Lock()
        self.state = "idle"  # idle -> loading -> ready | error
        self.error = None
        self.document_name = None
        self.chunk_count = 0
        self.retriever = None

    # ---------- Start-up (runs once, in a background thread) ----------
    def start(self):
        with self._lock:
            if self.state in ("loading", "ready"):
                return
            self.state = "loading"
            self.error = None
        threading.Thread(target=self._initialize, daemon=True).start()

    def _initialize(self):
        try:
            path, doc_hash = locate_document()
            embeddings = get_embeddings()

            cached = vector_store.load_existing(doc_hash, embeddings)
            if cached:
                store, texts, metadatas = cached
            else:
                pages, full_text = load_document(path)
                texts, metadatas = flatten_chunks(build_all_chunks(pages, full_text, embeddings))
                if not texts:
                    raise DocumentError("No text chunks could be created from this PDF.")
                store = vector_store.create_store(doc_hash, embeddings, texts, metadatas)

            self.retriever = HybridRetriever(store, texts, metadatas)
            self.document_name = path.name
            self.chunk_count = len(texts)
            self.state = "ready"
        except DocumentError as e:
            self.error, self.state = str(e), "error"
        except Exception as e:
            logger.exception("Pipeline start-up failed")
            self.error = f"Could not prepare the knowledge base ({type(e).__name__})."
            self.state = "error"

    def status(self):
        return {
            "state": self.state,
            "error": self.error,
            "document": self.document_name,
            "chunks": self.chunk_count,
        }

    # ---------- Answering ----------
    @staticmethod
    def _clean_history(history):
        cleaned = []
        for item in history or []:
            if not isinstance(item, dict):
                continue
            role, content = item.get("role"), item.get("content")
            if role in ("user", "assistant") and isinstance(content, str) and content.strip():
                cleaned.append({"role": role, "content": content.strip()[: config.HISTORY_MESSAGE_CHARS]})
        return cleaned[-config.HISTORY_MESSAGES:]

    @staticmethod
    def _retrieval_query(question, history):
        """Short follow-ups ('tell me more') are searched together with the previous question."""
        if history and len(question.split()) < 8:
            previous = [m["content"] for m in history if m["role"] == "user"]
            if previous:
                return f"{previous[-1]} {question}"
        return question

    def ask(self, question, pattern=DEFAULT_PATTERN, history=None):
        if self.state != "ready":
            if self.state == "idle":
                self.start()
            raise PipelineNotReady(self.error or "The knowledge base is still getting ready. Please wait a moment.")

        pattern = pattern if pattern in PATTERNS else DEFAULT_PATTERN
        history = self._clean_history(history)
        started = time.perf_counter()

        results = self.retriever.search(
            self._retrieval_query(question, history), k=config.TOP_K, alpha=config.ALPHA
        )
        if not results:
            answer = NOT_FOUND_ANSWER
        else:
            context = "\n\n---\n\n".join(r["text"][: config.MAX_CHUNK_CHARS] for r in results)
            answer = generate(build_messages(pattern, context, question, history)) or NOT_FOUND_ANSWER

        return {
            "answer": answer,
            "pattern": pattern,
            "elapsed_ms": int((time.perf_counter() - started) * 1000),
            "sources": [
                {
                    "text": r["text"][:400],
                    "technique": r["metadata"]["technique"],
                    "score": round(r["score"], 3),
                }
                for r in results
            ],
        }


# One shared pipeline for the whole app.
pipeline = RAGPipeline()
