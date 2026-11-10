"""
chunking.py - The 6 chunking techniques from the original pipeline.
"""
import numpy as np

import config
from langchain_experimental.text_splitter import SemanticChunker
from langchain_text_splitters import CharacterTextSplitter, RecursiveCharacterTextSplitter


# Technique 1: Fixed-size
def fixed_size_chunks(text):
    splitter = CharacterTextSplitter(separator="", chunk_size=150, chunk_overlap=20)
    return splitter.split_text(text)


# Technique 2: Sentence-based
def sentence_chunks(text):
    splitter = CharacterTextSplitter(separator=". ", chunk_size=10000, chunk_overlap=0)
    chunks = []
    for c in splitter.split_text(text):
        c = c.strip()
        if c:
            chunks.append(c if c.endswith(".") else c + ".")
    return chunks


# Technique 3: Recursive character splitting
def recursive_chunks(text):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=150, chunk_overlap=20, separators=["\n\n", "\n", " ", ""]
    )
    return splitter.split_text(text)


# Technique 4: Semantic chunking
def semantic_chunks(text, embeddings):
    splitter = SemanticChunker(embeddings, breakpoint_threshold_type="percentile")
    return [d.page_content for d in splitter.create_documents([text])]


# Technique 5: Document structure-based (one chunk per PDF page)
def structure_chunks(pages):
    return [p.page_content for p in pages if p.page_content.strip()]


# Technique 6: Agentic (groups neighbouring sentences by similarity)
def agentic_chunks(text, embeddings, threshold=0.5):
    sentences = [s.strip() for s in text.split(".") if s.strip()]
    if not sentences:
        return []
    sentence_embeddings = embeddings.embed_documents(sentences)

    chunks = []
    current_chunk = [sentences[0]]
    current_embedding = sentence_embeddings[0]
    for idx in range(1, len(sentences)):
        emb = sentence_embeddings[idx]
        similarity = np.dot(current_embedding, emb) / (
            np.linalg.norm(current_embedding) * np.linalg.norm(emb)
        )
        if similarity > threshold:
            current_chunk.append(sentences[idx])
            current_embedding = np.mean([current_embedding, emb], axis=0)
        else:
            chunks.append(". ".join(current_chunk) + ".")
            current_chunk = [sentences[idx]]
            current_embedding = emb
    if current_chunk:
        chunks.append(". ".join(current_chunk) + ".")
    return chunks


def _safe(name, func):
    """Run one technique; if it fails, skip it instead of stopping the whole app."""
    try:
        return func()
    except Exception as e:
        print(f"[chunking] '{name}' skipped ({type(e).__name__}: {e})")
        return []


def build_all_chunks(pages, full_text, embeddings):
    """Run every technique and return {technique_name: [chunk, ...]}."""
    return {
        "Fixed-Size": _safe("Fixed-Size", lambda: fixed_size_chunks(full_text)),
        "Sentence-Based": _safe("Sentence-Based", lambda: sentence_chunks(full_text)),
        "Recursive Character": _safe("Recursive", lambda: recursive_chunks(full_text)),
        "Semantic": _safe("Semantic", lambda: semantic_chunks(full_text, embeddings)),
        "Structure-Based": _safe("Structure", lambda: structure_chunks(pages)),
        "Agentic": _safe("Agentic", lambda: agentic_chunks(full_text, embeddings)),
    }


def flatten_chunks(all_techniques):
    """Turn the dictionary into two parallel lists: texts and metadatas.

    Very short chunks (a lone heading like 'Theft.') are skipped: they hold no answer, but
    would score high in keyword search because the score is divided by chunk length.
    """
    texts, metadatas = [], []
    for technique, chunks in all_techniques.items():
        for i, chunk in enumerate(chunks):
            if chunk and len(chunk.strip()) >= config.MIN_CHUNK_CHARS:
                texts.append(chunk)
                metadatas.append({"technique": technique, "chunk_index": i})
    return texts, metadatas
