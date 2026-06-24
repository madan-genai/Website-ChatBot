import uuid
import asyncio
import logging
import time

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse

from langchain_ollama import ChatOllama
from langchain_core.prompts import PromptTemplate

from schemas2 import IndexRequest, ReindexRequest, QueryRequest, ChatHistoryResponse, ChatMessage
from scrape2 import WebsiteCrawler
from vector2 import build_vectorstore, load_vectorstore, delete_vectorstore

from db2 import (
    SessionLocal,
    save_index, get_index, get_index_by_url, delete_index,
    save_message, get_chat_history, delete_chat_history, delete_all_chat_history
)
from redis_cache import get_cached, set_cached, invalidate_index
from config2 import LLM_MODEL, OLLAMA_BASE_URL

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("rag-app")

app = FastAPI(title="RAG Chatbot", version="2.0.0")

llm = ChatOllama(
    model=LLM_MODEL,
    base_url=OLLAMA_BASE_URL,
    temperature=0.3,
    num_ctx=2048,
)

PROMPT_TEMPLATE = PromptTemplate.from_template("""
You are a helpful assistant. Use ONLY the context below to answer.
If the answer is not in the context, say "I don't know based on the provided content."

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
        docs    = await asyncio.to_thread(crawler.crawl)

        if not docs:
            raise Exception("No content crawled from website")

        collection_name = f"site_{index_id}"

        vs = await asyncio.to_thread(build_vectorstore, docs, collection_name)

        chunks = sum(1 for d in docs)

        save_index(
            index_id, url, collection_name, "completed", db,
            pages_crawled=len(docs),
            chunks_created=chunks,
        )
        logger.info(f"Indexing completed: {index_id} | pages={len(docs)}")

    except Exception as e:
        logger.error(f"Indexing failed [{index_id}]: {e}")
        save_index(index_id, url, "", f"failed", db, error_message=str(e))

    finally:
        db.close()

@app.get("/health")
async def health():
    from redis_cache import REDIS_AVAILABLE
    checks = {
        "api":    "ok",
        "redis":  "ok" if REDIS_AVAILABLE else "unavailable",
    }

    # Quick DB ping
    try:
        db = SessionLocal()
        db.execute(__import__("sqlalchemy").text("SELECT 1"))
        db.close()
        checks["mysql"] = "ok"
    except Exception as e:
        checks["mysql"] = f"error: {e}"

    # Quick Qdrant ping
    try:
        import httpx
        from config2 import QDRANT_URL
        r = httpx.get(f"{QDRANT_URL}/healthz", timeout=3)
        checks["qdrant"] = "ok" if r.status_code == 200 else f"status={r.status_code}"
    except Exception as e:
        checks["qdrant"] = f"error: {e}"

    overall = "healthy" if all(v == "ok" for v in checks.values()) else "degraded"
    return {"status": overall, "checks": checks}

@app.post("/index")
async def index(req: IndexRequest):
    if not req.url:
        raise HTTPException(status_code=400, detail="URL is required")

    db = SessionLocal()
    try:
        url      = str(req.url).strip()
        existing = get_index_by_url(url, db)

        if existing:
            return {
                "index_id": existing.index_id,
                "status":   existing.status,
                "message":  "URL already indexed",
                "cached":   True,
            }

        index_id = str(uuid.uuid4())
        asyncio.create_task(index_site(index_id, url))

        return {
            "index_id": index_id,
            "status":   "processing",
            "cached":   False,
        }
    finally:
        db.close()

@app.post("/reindex")
async def reindex(req: ReindexRequest):
    """Delete existing index + re-crawl from scratch."""
    if not req.url:
        raise HTTPException(status_code=400, detail="URL is required")

    db = SessionLocal()
    try:
        url      = str(req.url).strip()
        existing = get_index_by_url(url, db)

        if existing:
            old_id = existing.index_id

            # 1. Delete Qdrant collection
            if existing.collection_name:
                try:
                    await asyncio.to_thread(delete_vectorstore, existing.collection_name)
                except Exception as e:
                    logger.warning(f"Qdrant delete failed: {e}")

            # 2. Invalidate Redis cache
            invalidate_index(old_id)

            # 3. Delete chat history
            delete_all_chat_history(old_id, db)

            # 4. Delete DB record
            delete_index(old_id, db)

        # 5. Start fresh index
        index_id = str(uuid.uuid4())
        asyncio.create_task(index_site(index_id, url))

        return {
            "index_id":  index_id,
            "status":    "processing",
            "reindexed": True,
        }
    finally:
        db.close()

@app.delete("/index/{index_id}")
async def remove_index(index_id: str):
    db = SessionLocal()
    try:
        record = get_index(index_id, db)
        if not record:
            raise HTTPException(status_code=404, detail="Index not found")

        # 1. Delete Qdrant collection
        if record.collection_name:
            try:
                await asyncio.to_thread(delete_vectorstore, record.collection_name)
            except Exception as e:
                logger.warning(f"Qdrant delete failed: {e}")

        # 2. Invalidate Redis cache
        invalidate_index(index_id)

        # 3. Delete chat history
        delete_all_chat_history(index_id, db)

        # 4. Delete DB record
        delete_index(index_id, db)

        return {"message": "Index deleted successfully", "index_id": index_id}
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
            "index_id":        data.index_id,
            "url":             data.url,
            "collection_name": data.collection_name,
            "status":          data.status,
            "pages_crawled":   data.pages_crawled,
            "chunks_created":  data.chunks_created,
            "error_message":   data.error_message,
        }
    finally:
        db.close()

@app.post("/chat/stream")
async def chat(req: QueryRequest):
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    db         = SessionLocal()
    session_id = req.session_id or "default"

    try:
        meta = get_index(req.index_id, db)
        if not meta:
            raise HTTPException(status_code=404, detail="Index not found")
        if meta.status != "completed":
            raise HTTPException(status_code=400, detail=f"Index not ready: {meta.status}")

        # ── Redis cache check ──────────────────────────────────────
        cached_answer = get_cached(req.index_id, req.question)
        if cached_answer:
            save_message(req.index_id, session_id, "user",      req.question,   db)
            save_message(req.index_id, session_id, "assistant", cached_answer,  db)

            async def cached_stream():
                yield cached_answer

            return StreamingResponse(cached_stream(), media_type="text/plain")

        # ── Load vector store ──────────────────────────────────────
        store = await asyncio.to_thread(load_vectorstore, meta.collection_name)

        # ── MMR retrieval (better diversity than similarity search) ─
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
        prompt  = PROMPT_TEMPLATE.format(context=context, question=req.question)

        # ── Save user message ──────────────────────────────────────
        save_message(req.index_id, session_id, "user", req.question, db)

        # ── Stream + accumulate for cache ──────────────────────────
        async def stream_generator():
            full_answer = []
            try:
                async for chunk in llm.astream(prompt):
                    if chunk and getattr(chunk, "content", None):
                        full_answer.append(chunk.content)
                        yield chunk.content

                answer_text = "".join(full_answer)

                # Save to DB + Redis (fire-and-forget via thread)
                db2 = SessionLocal()
                try:
                    save_message(req.index_id, session_id, "assistant", answer_text, db2)
                finally:
                    db2.close()

                set_cached(req.index_id, req.question, answer_text)

            except asyncio.CancelledError:
                logger.info("Client disconnected mid-stream")

            except Exception as e:
                logger.error(f"Streaming error: {e}")
                yield f"\n[Error: {str(e)}]"

        return StreamingResponse(stream_generator(), media_type="text/plain")

    finally:
        db.close()


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


@app.delete("/chat/history/{index_id}")
async def clear_chat_history(index_id: str, session_id: str = "default"):
    db = SessionLocal()
    try:
        delete_chat_history(index_id, session_id, db)
        return {"message": "Chat history cleared", "index_id": index_id, "session_id": session_id}
    finally:
        db.close()


@app.get("/")
async def root():
    return {
        "status":  "running",
        "version": "2.0.0",
        "db":      "mysql",
        "vector_db": "qdrant",
        "cache":   "redis",
        "system":  "production-rag-chatbot",
    }
