from langchain_qdrant import QdrantVectorStore
from langchain_ollama import OllamaEmbeddings
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from config import QDRANT_URL, EMBEDDING_MODEL, OLLAMA_BASE_URL

def build_vectorstore(docs, collection_name):

    embeddings = OllamaEmbeddings(
        model=EMBEDDING_MODEL,
        base_url=OLLAMA_BASE_URL
    )

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=600,
        chunk_overlap=50
    )

    documents = [
        Document(
            page_content=d["content"],
            metadata={"url": d["url"]}
        )
        for d in docs
    ]

    chunked_docs = splitter.split_documents(documents)

    return QdrantVectorStore.from_documents(
        documents=chunked_docs,
        embedding=embeddings,
        url=QDRANT_URL,
        collection_name=collection_name,
        batch_size=128,
        prefer_grpc=False
    )


def load_vectorstore(collection_name):

    embeddings = OllamaEmbeddings(
        model=EMBEDDING_MODEL,
        base_url=OLLAMA_BASE_URL
    )

    return QdrantVectorStore.from_existing_collection(
        embedding=embeddings,
        url=QDRANT_URL,
        collection_name=collection_name
    )