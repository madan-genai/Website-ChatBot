import uuid
import asyncio
import logging
from urllib.parse import urlparse, urlunparse

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse

from langchain_ollama import ChatOllama
from langchain_core.prompts import PromptTemplate

from schemas2 import (
    IndexRequest,
    ReindexRequest,
    QueryRequest,
    ChatHistoryResponse,
    ChatMessage,
)
from scrape2 import WebsiteCrawler
from vector2 import build_vectorstore, load_vectorstore, delete_vectorstore
from models2 import Index

from db2 import (
    SessionLocal,
    save_index,
    get_index,
    get_index_by_url,
    delete_index,
    save_message,
    get_chat_history,
    delete_chat_history,
    delete_all_chat_history,
)
from redis_cache import get_cached, set_cached, invalidate_index
from config2 import LLM_MODEL, OLLAMA_BASE_URL

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("rag-app")

app = FastAPI(title="RAG Chatbot", version="2.1.0")


# ─────────────────────────────────────────────────────────────────────────────
# URL normalization
# ─────────────────────────────────────────────────────────────────────────────
def normalize_url(url: str) -> str:
    """
    Normalize URLs consistently across:
    - /index
    - /reindex
    - DB lookup
    - saved records

    Rules:
    - add http:// if missing
    - lowercase scheme + domain
    - remove www.
    - strip query + fragment
    - trim trailing slash except root
    """
    url = str(url).strip()
    if not url:
        return url

    if not url.startswith(("http://", "https://")):
        url = "http://" + url

    parsed = urlparse(url)
    netloc = parsed.netloc.lower().replace("www.", "")
    path = parsed.path.rstrip("/") or "/"

    cleaned = parsed._replace(
        scheme=parsed.scheme.lower(),
        netloc=netloc,
        path=path,
        query="",
        fragment="",
    )
    return urlunparse(cleaned)


# ─────────────────────────────────────────────────────────────────────────────
# LLM
# ─────────────────────────────────────────────────────────────────────────────
llm = ChatOllama(
    model=LLM_MODEL,
    base_url=OLLAMA_BASE_URL,
    temperature=0.3,
    num_ctx=2048,
)

PROMPT_TEMPLATE = PromptTemplate.from_template(
    """
You are a helpful assistant. Use ONLY the context below to answer.
If the answer is not in the context, say "I don't know based on the provided content."

Context:
{context}

Question:
{question}

Answer:
""".strip()
)


# ─────────────────────────────────────────────────────────────────────────────
# Background indexing job
# ─────────────────────────────────────────────────────────────────────────────
async def index_site(index_id: str, url: str):
    db = SessionLocal()
    normalized_url = normalize_url(url)

    try:
        logger.info(f"Indexing started: index_id={index_id} url={normalized_url}")

        # Save "processing" row immediately
        save_index(
            index_id=index_id,
            url=normalized_url,
            collection_name="",
            status="processing",
            db=db,
            pages_crawled=0,
            chunks_created=0,
            error_message=None,
        )

        crawler = WebsiteCrawler(normalized_url)
        docs = await asyncio.to_thread(crawler.crawl)

        if not docs:
            raise Exception("No content crawled from website")

        collection_name = f"site_{index_id}"

        await asyncio.to_thread(build_vectorstore, docs, collection_name)

        # pages = number of crawled docs
        pages_crawled = len(docs)

        # For now chunks_created is approximated by number of docs.
        # If you later want exact chunk count, return it from build_vectorstore().
        chunks_created = len(docs)

        save_index(
            index_id=index_id,
            url=normalized_url,
            collection_name=collection_name,
            status="completed",
            db=db,
            pages_crawled=pages_crawled,
            chunks_created=chunks_created,
            error_message=None,
        )

        logger.info(
            f"Indexing completed: index_id={index_id} pages={pages_crawled} chunks={chunks_created}"
        )

    except Exception as e:
        logger.exception(f"Indexing failed [{index_id}]: {e}")
        save_index(
            index_id=index_id,
            url=normalized_url,
            collection_name="",
            status="failed",
            db=db,
            pages_crawled=0,
            chunks_created=0,
            error_message=str(e),
        )

    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# Health
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    from redis_cache import REDIS_AVAILABLE

    checks = {
        "api": "ok",
        "redis": "ok" if REDIS_AVAILABLE else "unavailable",
    }

    # DB ping
    try:
        db = SessionLocal()
        db.execute(__import__("sqlalchemy").text("SELECT 1"))
        db.close()
        checks["mysql"] = "ok"
    except Exception as e:
        checks["mysql"] = f"error: {e}"

    # Qdrant ping
    try:
        import httpx
        from config2 import QDRANT_URL

        r = httpx.get(f"{QDRANT_URL}/healthz", timeout=3)
        checks["qdrant"] = "ok" if r.status_code == 200 else f"status={r.status_code}"
    except Exception as e:
        checks["qdrant"] = f"error: {e}"

    overall = "healthy" if all(v == "ok" for v in checks.values()) else "degraded"
    return {"status": overall, "checks": checks}


# ─────────────────────────────────────────────────────────────────────────────
# List all indexes (NEW)
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/indexes")
async def list_indexes():
    db = SessionLocal()
    try:
        rows = db.query(Index).order_by(Index.created_at.desc()).all()
        return [
            {
                "index_id": r.index_id,
                "url": r.url,
                "collection_name": r.collection_name,
                "status": r.status,
                "pages_crawled": r.pages_crawled,
                "chunks_created": r.chunks_created,
                "error_message": r.error_message,
                "created_at": str(r.created_at) if r.created_at else None,
            }
            for r in rows
        ]
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# Create index
# ─────────────────────────────────────────────────────────────────────────────
@app.post("/index")
async def index(req: IndexRequest):
    if not req.url or not str(req.url).strip():
        raise HTTPException(status_code=400, detail="URL is required")

    db = SessionLocal()
    try:
        url = normalize_url(req.url)
        existing = get_index_by_url(url, db)

        if existing:
            return {
                "index_id": existing.index_id,
                "status": existing.status,
                "message": "URL already indexed",
                "cached": True,
            }

        index_id = str(uuid.uuid4())
        asyncio.create_task(index_site(index_id, url))

        return {
            "index_id": index_id,
            "status": "processing",
            "cached": False,
        }
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# Reindex (force re-scrape)
# ─────────────────────────────────────────────────────────────────────────────
@app.post("/reindex")
async def reindex(req: ReindexRequest):
    """
    Delete existing index + re-crawl from scratch.
    """
    if not req.url or not str(req.url).strip():
        raise HTTPException(status_code=400, detail="URL is required")

    db = SessionLocal()
    try:
        url = normalize_url(req.url)
        existing = get_index_by_url(url, db)

        if existing:
            old_id = existing.index_id
            logger.info(f"Reindex requested for existing URL: {url} old_index_id={old_id}")

            # 1) delete Qdrant collection
            if existing.collection_name:
                try:
                    await asyncio.to_thread(delete_vectorstore, existing.collection_name)
                except Exception as e:
                    logger.warning(f"Qdrant delete failed during reindex: {e}")

            # 2) invalidate cache
            invalidate_index(old_id)

            # 3) delete chat history
            delete_all_chat_history(old_id, db)

            # 4) delete DB record
            delete_index(old_id, db)

        # Start fresh index
        new_index_id = str(uuid.uuid4())
        asyncio.create_task(index_site(new_index_id, url))

        return {
            "index_id": new_index_id,
            "status": "processing",
            "reindexed": True,
        }
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# Delete index
# ─────────────────────────────────────────────────────────────────────────────
@app.delete("/index/{index_id}")
async def remove_index(index_id: str):
    db = SessionLocal()
    try:
        record = get_index(index_id, db)
        if not record:
            raise HTTPException(status_code=404, detail="Index not found")

        # 1) delete Qdrant collection
        if record.collection_name:
            try:
                await asyncio.to_thread(delete_vectorstore, record.collection_name)
            except Exception as e:
                logger.warning(f"Qdrant delete failed: {e}")

        # 2) invalidate cache
        invalidate_index(index_id)

        # 3) delete chat history
        delete_all_chat_history(index_id, db)

        # 4) delete DB record
        delete_index(index_id, db)

        return {"message": "Index deleted successfully", "index_id": index_id}
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# Get single index status
# ─────────────────────────────────────────────────────────────────────────────
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
            "error_message": data.error_message,
            "created_at": str(data.created_at) if data.created_at else None,
        }
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# Chat stream
# ─────────────────────────────────────────────────────────────────────────────
@app.post("/chat/stream")
async def chat(req: QueryRequest):
    if not req.question or not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    db = SessionLocal()
    session_id = req.session_id or "default"

    try:
        meta = get_index(req.index_id, db)
        if not meta:
            raise HTTPException(status_code=404, detail="Index not found")

        if meta.status != "completed":
            raise HTTPException(
                status_code=400,
                detail=f"Index not ready: {meta.status}",
            )

        # 1) cache check
        cached_answer = get_cached(req.index_id, req.question)
        if cached_answer:
            save_message(req.index_id, session_id, "user", req.question, db)
            save_message(req.index_id, session_id, "assistant", cached_answer, db)

            async def cached_stream():
                yield cached_answer

            return StreamingResponse(cached_stream(), media_type="text/plain")

        # 2) load vector store
        store = await asyncio.to_thread(load_vectorstore, meta.collection_name)

        # 3) retrieve docs
        docs = await asyncio.to_thread(
            lambda: store.as_retriever(
                search_type="mmr",
                search_kwargs={"k": 4, "fetch_k": 12},
            ).invoke(req.question)
        )

        if not docs:
            async def fallback():
                yield "I don't know based on the provided website content."

            return StreamingResponse(fallback(), media_type="text/plain")

        context = "\n\n".join(d.page_content[:600] for d in docs)
        prompt = PROMPT_TEMPLATE.format(context=context, question=req.question)

        # save user message
        save_message(req.index_id, session_id, "user", req.question, db)

        async def stream_generator():
            full_answer = []

            try:
                async for chunk in llm.astream(prompt):
                    if chunk and getattr(chunk, "content", None):
                        full_answer.append(chunk.content)
                        yield chunk.content

                answer_text = "".join(full_answer).strip()

                # save assistant response
                db2 = SessionLocal()
                try:
                    save_message(req.index_id, session_id, "assistant", answer_text, db2)
                finally:
                    db2.close()

                if answer_text:
                    set_cached(req.index_id, req.question, answer_text)

            except asyncio.CancelledError:
                logger.info("Client disconnected mid-stream")

            except Exception as e:
                logger.exception(f"Streaming error: {e}")
                yield f"\n[Error: {str(e)}]"

        return StreamingResponse(stream_generator(), media_type="text/plain")

    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# Chat history
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/chat/history/{index_id}", response_model=ChatHistoryResponse)
async def chat_history(index_id: str, session_id: str = "default"):
    db = SessionLocal()
    try:
        meta = get_index(index_id, db)
        if not meta:
            raise HTTPException(status_code=404, detail="Index not found")

        msgs = get_chat_history(index_id, session_id, db)
        return ChatHistoryResponse(
            index_id=index_id,
            session_id=session_id,
            messages=[
                ChatMessage(role=m.role, content=m.content, created_at=m.created_at)
                for m in msgs
            ],
        )
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# Clear chat history
# ─────────────────────────────────────────────────────────────────────────────
@app.delete("/chat/history/{index_id}")
async def clear_chat_history(index_id: str, session_id: str = "default"):
    db = SessionLocal()
    try:
        meta = get_index(index_id, db)
        if not meta:
            raise HTTPException(status_code=404, detail="Index not found")

        delete_chat_history(index_id, session_id, db)
        return {
            "message": "Chat history cleared",
            "index_id": index_id,
            "session_id": session_id,
        }
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# Root
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/")
async def root():
    return {
        "status": "running",
        "version": "2.1.0",
        "db": "mysql",
        "vector_db": "qdrant",
        "cache": "redis",
        "system": "production-rag-chatbot",
    }