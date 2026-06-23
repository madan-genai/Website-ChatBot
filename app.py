import uuid
import asyncio
import logging

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse

from langchain_ollama import ChatOllama
from langchain_core.prompts import PromptTemplate

from schemas import IndexRequest, QueryRequest
from scraper import WebsiteCrawler
from vectorstore import build_vectorstore, load_vectorstore

from db import SessionLocal, save_index, get_index, get_index_by_url
from config import LLM_MODEL, OLLAMA_BASE_URL

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("rag-app")

app = FastAPI(title="RAG Chatbot ")

llm = ChatOllama(
    model=LLM_MODEL,
    base_url=OLLAMA_BASE_URL,
    temperature=0,
    num_ctx=2048
)

PROMPT_TEMPLATE = PromptTemplate.from_template("""
Use ONLY the context below. If the answer is not present, say "I don't know".

Context:
{context}

Question:
{question}

Answer:
""")

async def index_site(index_id: str, url: str):

    db = SessionLocal()

    try:
        logger.info(f"Indexing started: {index_id}")

        save_index(index_id, url, "", "processing", db)

        crawler = WebsiteCrawler(url)
        docs = await asyncio.to_thread(crawler.crawl)

        if not docs:
            raise Exception("No content crawled")

        collection_name = f"site_{index_id}"

        # 4. Build vector DB
        await asyncio.to_thread(
            build_vectorstore,
            docs,
            collection_name
        )

        save_index(
            index_id,
            url,
            collection_name,
            "completed",
            db
        )

        logger.info(f"Indexing completed: {index_id}")

    except Exception as e:
        logger.error(f"Indexing failed [{index_id}]: {e}")

        save_index(
            index_id,
            url,
            "",
            f"failed: {str(e)}",
            db
        )

    finally:
        db.close()

@app.post("/index")
async def index(req: IndexRequest):

    if not req.url:
        raise HTTPException(
            status_code=400,
            detail="URL is required"
        )

    db = SessionLocal()

    try:

        existing = get_index_by_url(req.url, db)

        if existing:

            return {
                "index_id": existing.index_id,
                "status": existing.status,
                "message": "URL already indexed",
                "cached": True
            }

        index_id = str(uuid.uuid4())

        asyncio.create_task(
            index_site(index_id, req.url)
        )

        return {
            "index_id": index_id,
            "status": "processing",
            "cached": False
        }

    finally:
        db.close()

@app.get("/index/{index_id}")
async def status(index_id: str):

    db = SessionLocal()

    try:
        data = get_index(index_id, db)

        if not data:
            raise HTTPException(status_code=404, detail="Index not found")

        return {
            "index_id": data.index_id,
            "url": data.url,
            "collection_name": data.collection_name,
            "status": data.status,
            "pages_crawled": data.pages_crawled,
            "chunks_created": data.chunks_created,
            "error_message": data.error_message
        }

    finally:
        db.close()

@app.post("/chat/stream")
async def chat(req: QueryRequest):

    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    db = SessionLocal()

    try:
        # 1. Fetch index metadata
        meta = get_index(req.index_id, db)

        if not meta:
            raise HTTPException(status_code=404, detail="Index not found")

        if meta.status != "completed":
            raise HTTPException(status_code=400, detail="Index not ready")

        collection_name = meta.collection_name

        # 2. Load vector store
        store = await asyncio.to_thread(
            load_vectorstore,
            collection_name
        )

        docs = await asyncio.to_thread(
            store.similarity_search,
            req.question,
            k=3
        )

        # 3. Fallback
        if not docs:

            async def fallback():
                yield "I don't know based on the provided website."

            return StreamingResponse(fallback(), media_type="text/plain")

        context = "\n\n".join(
            d.page_content[:500] for d in docs
        )

        prompt = PROMPT_TEMPLATE.format(
            context=context,
            question=req.question
        )
        async def stream_generator():

            try:
                async for chunk in llm.astream(prompt):
                    if chunk and getattr(chunk, "content", None):
                        yield chunk.content

            except asyncio.CancelledError:
                logger.info("Client disconnected")

            except Exception as e:
                logger.error(f"Streaming error: {e}")
                yield f"\n[Error: {str(e)}]"

        return StreamingResponse(stream_generator(), media_type="text/plain")

    finally:
        db.close()

@app.get("/")
async def root():
    return {
        "status": "running",
        "db": "mysql",
        "vector_db": "qdrant",
        "system": "production-rag-chatbot"
    }