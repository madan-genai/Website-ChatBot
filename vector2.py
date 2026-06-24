from langchain_qdrant import QdrantVectorStore
from langchain_ollama import OllamaEmbeddings
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient

from config2 import QDRANT_URL, EMBEDDING_MODEL, OLLAMA_BASE_URL

EMBEDDINGS = OllamaEmbeddings(
    model=EMBEDDING_MODEL,
    base_url=OLLAMA_BASE_URL,
)

TEXT_SPLITTER = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=100,
)


def build_vectorstore(docs: list[dict], collection_name: str):
    documents = []
    for doc in docs:
        content = doc.get("content", "").strip()
        if not content:
            continue
        documents.append(
            Document(
                page_content=content,
                metadata={
                    "url":  doc.get("url", ""),
                    "type": doc.get("type", "html"),
                },
            )
        )

    if not documents:
        raise ValueError("No valid documents found for indexing.")

    chunked_docs = TEXT_SPLITTER.split_documents(documents)
    if not chunked_docs:
        raise ValueError("No chunks generated after splitting.")

    vectorstore = QdrantVectorStore.from_documents(
        documents=chunked_docs,
        embedding=EMBEDDINGS,
        url=QDRANT_URL,
        collection_name=collection_name,
        batch_size=128,
    )

    return vectorstore


def load_vectorstore(collection_name: str) -> QdrantVectorStore:
    try:
        return QdrantVectorStore.from_existing_collection(
            embedding=EMBEDDINGS,
            url=QDRANT_URL,
            collection_name=collection_name,
        )
    except Exception as e:
        raise Exception(f"Failed to load collection '{collection_name}': {str(e)}")


def delete_vectorstore(collection_name: str):
    """Delete a Qdrant collection completely."""
    try:
        client = QdrantClient(url=QDRANT_URL)
        client.delete_collection(collection_name)
    except Exception as e:
        raise Exception(f"Failed to delete collection '{collection_name}': {str(e)}")


def retrieve_documents(vectorstore: QdrantVectorStore, query: str, k: int = 4):
    """MMR retrieval for better diversity."""
    retriever = vectorstore.as_retriever(
        search_type="mmr",
        search_kwargs={
            "k":       k,
            "fetch_k": max(10, k * 3),
        },
    )
    return retriever.invoke(query)
