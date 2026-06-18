import os
import uuid
import time
from typing import List, Dict

from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct

from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter


class VectorStore:

    def __init__(self):

        self.client = QdrantClient(
            url=os.getenv("QDRANT_URL", "http://localhost:6333")
        )

        self.embeddings = OllamaEmbeddings(
            model=os.getenv("EMBED_MODEL", "nomic-embed-text"),
            base_url=os.getenv("OLLAMA_URL", "http://localhost:11434")
        )

        # FIX: no API call at startup (prevents uvicorn hang)
        self.dim = int(os.getenv("EMBED_DIM", "768"))

        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )

    def create_collection(self, collection_name: str):

        if not self.client.collection_exists(collection_name):
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=self.dim,
                    distance=Distance.COSINE
                )
            )

    def upsert(self, collection_name: str, docs: List[Dict]):

        self.create_collection(collection_name)

        points = []

        for doc in docs:

            url = doc.get("url", "")
            content = doc.get("content", "")

            if not content:
                continue

            chunks = self.splitter.split_text(content)

            for idx, chunk in enumerate(chunks):

                try:
                    vector = self.embeddings.embed_query(chunk)

                    points.append(
                        PointStruct(
                            id=str(uuid.uuid4()),
                            vector=vector,
                            payload={
                                "text": chunk,
                                "url": url,
                                "chunk": idx,
                                "timestamp": time.time()
                            }
                        )
                    )

                except Exception as e:
                    print(f"Embedding failed: {e}")

        if points:
            self.client.upsert(
                collection_name=collection_name,
                points=points
            )

    def search(self, collection_name: str, query: str, limit: int = 5):

        if not self.client.collection_exists(collection_name):
            return []

        try:
            query_vector = self.embeddings.embed_query(query)

            results = self.client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=limit
            )

        except Exception:
            return []

        return [
            {
                "text": r.payload.get("text", ""),
                "url": r.payload.get("url", ""),
                "score": getattr(r, "score", 0)
            }
            for r in results
        ]