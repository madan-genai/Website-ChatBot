import os

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")

LLM_MODEL = os.getenv("LLM_MODEL", "qwen2.5:1.5b")

DB_PATH = "data/metadata.db"