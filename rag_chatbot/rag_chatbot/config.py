"""
config.py - All settings in one place.

Secrets (like the API key) are read from the .env file, never hard-coded.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# Silence anonymous telemetry noise (must be set before chromadb is imported).
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

# ---------- Paths ----------
DATA_DIR = BASE_DIR / "data"          # put your PDF here
STORAGE_DIR = BASE_DIR / "storage"    # saved vector DB + chunk cache (auto-created)
CHROMA_DIR = STORAGE_DIR / "chroma"
CACHE_FILE = STORAGE_DIR / "chunks_cache.json"
DOCUMENT_PATH = os.getenv("DOCUMENT_PATH", "").strip()  # optional: explicit PDF path

# ---------- Embeddings (unchanged from the original pipeline) ----------
EMBEDDING_MODEL = "sentence-transformers/all-mpnet-base-v2"

# ---------- Chunk filtering ----------
MIN_CHUNK_CHARS = 60      # chunks shorter than this (e.g. a lone heading) carry no answer

# ---------- Retrieval ----------
TOP_K = 3                 # chunks sent to the LLM
ALPHA = 0.5               # 0.5 = equal mix of semantic and keyword score
SEMANTIC_CANDIDATES = 100 # semantic candidates scored per question (keeps search fast)
MAX_CHUNK_CHARS = 2000    # each chunk is trimmed to this size inside the prompt

# ---------- LLM (OpenRouter) ----------
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
LLM_MODEL = os.getenv("LLM_MODEL", "google/gemini-2.5-flash-lite").strip()
LLM_TEMPERATURE = 0.0
LLM_MAX_TOKENS = 800
LLM_TIMEOUT_SECONDS = 60

# ---------- Chat ----------
HISTORY_MESSAGES = 6      # previous messages sent along for follow-up questions
HISTORY_MESSAGE_CHARS = 600
MAX_QUESTION_CHARS = 1000

# ---------- Web app ----------
APP_NAME = "DocMind"
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "5000"))
