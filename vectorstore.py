from langchain_qdrant import QdrantVectorStore
from langchain_ollama import OllamaEmbeddings
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from config import (
    QDRANT_URL,
    EMBEDDING_MODEL,
    OLLAMA_BASE_URL,
)

# =========================
# Reuse embeddings (IMPORTANT)
# =========================
EMBEDDINGS = OllamaEmbeddings(
    model=EMBEDDING_MODEL,
    base_url=OLLAMA_BASE_URL,
)

# =========================
# Text splitter tuned for web pages
# =========================
TEXT_SPLITTER = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=100,
)


# =========================
# Build / Index vectorstore
# =========================
def build_vectorstore(docs, collection_name):
    """
    Create embeddings + store in Qdrant
    """

    documents = []

    for doc in docs:
        content = doc.get("content", "").strip()

        if not content:
            continue

        documents.append(
            Document(
                page_content=content,
                metadata={
                    "url": doc.get("url", ""),
                },
            )
        )

    if not documents:
        raise ValueError("No valid documents found for indexing.")

    # Split into chunks
    chunked_docs = TEXT_SPLITTER.split_documents(documents)

    if not chunked_docs:
        raise ValueError("No chunks generated after splitting.")

    # Create + store in Qdrant
    vectorstore = QdrantVectorStore.from_documents(
        documents=chunked_docs,
        embedding=EMBEDDINGS,
        url=QDRANT_URL,          # IMPORTANT: no client= to avoid your error
        collection_name=collection_name,
        batch_size=128,
    )

    return vectorstore


# =========================
# Load existing vectorstore
# =========================
def load_vectorstore(collection_name):
    """
    Load existing Qdrant collection
    """

    try:
        return QdrantVectorStore.from_existing_collection(
            embedding=EMBEDDINGS,
            url=QDRANT_URL,
            collection_name=collection_name,
        )

    except Exception as e:
        raise Exception(
            f"Failed to load collection '{collection_name}': {str(e)}"
        )


# =========================
# Retrieval (MMR improved search)
# =========================
def retrieve_documents(vectorstore, query: str, k: int = 4):
    """
    Smart retrieval using MMR (better than similarity search)
    """

    retriever = vectorstore.as_retriever(
        search_type="mmr",
        search_kwargs={
            "k": k,
            "fetch_k": max(10, k * 2),
        },
    )

    return retriever.invoke(query)