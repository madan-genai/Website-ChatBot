from langchain_qdrant import QdrantVectorStore
from langchain_ollama import OllamaEmbeddings
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from config import QDRANT_URL, EMBEDDING_MODEL, OLLAMA_BASE_URL

COLLECTION_NAME = "websites"


EMBEDDINGS = OllamaEmbeddings(
    model=EMBEDDING_MODEL,
    base_url=OLLAMA_BASE_URL,
)


TEXT_SPLITTER = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=100,
)

def build_vectorstore(docs, index_id: str, url: str, user_id: str):

    documents = []

    for doc in docs:

        if isinstance(doc, dict):
            content = doc.get("content") or doc.get("text") or ""

        elif hasattr(doc, "page_content"):
            content = doc.page_content

        else:
            content = str(doc)

        content = content.strip()

        if not content:
            continue

        documents.append(
            Document(
                page_content=content,
                metadata={
                    "index_id": index_id,
                    "url": url,
                    "user_id": user_id,
                },
            )
        )

    if not documents:
        raise ValueError("Crawler returned empty usable content")

    chunked_docs = TEXT_SPLITTER.split_documents(documents)

    if not chunked_docs:
        raise ValueError("No chunks generated from documents")

    return QdrantVectorStore.from_documents(
        documents=chunked_docs,
        embedding=EMBEDDINGS,
        url=QDRANT_URL,
        collection_name=COLLECTION_NAME,
    )

def load_vectorstore():
    return QdrantVectorStore.from_existing_collection(
        embedding=EMBEDDINGS,
        url=QDRANT_URL,
        collection_name=COLLECTION_NAME,
    )

def retrieve_documents(
    vectorstore,
    query: str,
    k: int = 4,
    index_id: str = None,
    user_id: str = None
):

    search_kwargs = {
        "k": k,
        "fetch_k": max(10, k * 2),
    }

    must_filter = []

    if index_id:
        must_filter.append({
            "key": "index_id",
            "match": {"value": index_id}
        })

    if user_id:
        must_filter.append({
            "key": "user_id",
            "match": {"value": user_id}
        })

    if must_filter:
        search_kwargs["filter"] = {
            "must": must_filter
        }

    retriever = vectorstore.as_retriever(
        search_type="mmr",
        search_kwargs=search_kwargs,
    )

    return retriever.get_relevant_documents(query)