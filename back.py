import uuid

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool

from models import IndexRequest, QueryRequest
from scraper import WebsiteCrawler
from vectorstore import build_vectorstore, load_vectorstore
from db import save_index, get_index
from config import LLM_MODEL, OLLAMA_BASE_URL

from langchain_ollama import ChatOllama

app = FastAPI(title="Optimized Async RAG Chatbot")

# ---------------------------
# LLM (optimized for speed)
# ---------------------------
llm = ChatOllama(
    model=LLM_MODEL,
    base_url=OLLAMA_BASE_URL,
    temperature=0,
    num_ctx=1024,
    num_predict=120  # 🔥 CRITICAL SPEED BOOST
)

# ---------------------------
# Warm-up model (fix cold start lag)
# ---------------------------
@app.on_event("startup")
async def warmup():
    try:
        llm.invoke("hi")
    except:
        pass


# ---------------------------
# Background indexing
# ---------------------------
async def index_site(index_id: str, url: str):
    try:
        await run_in_threadpool(save_index, index_id, url, "", "processing")

        crawler = WebsiteCrawler(url)
        docs = await run_in_threadpool(crawler.crawl)

        if not docs:
            await run_in_threadpool(save_index, index_id, url, "", "failed: no content")
            return

        collection = f"site_{index_id}"

        await run_in_threadpool(build_vectorstore, docs, collection)

        await run_in_threadpool(
            save_index,
            index_id,
            url,
            collection,
            "completed"
        )

    except Exception as e:
        await run_in_threadpool(
            save_index,
            index_id,
            url,
            "",
            f"failed: {str(e)}"
        )


# ---------------------------
# Index endpoint
# ---------------------------
@app.post("/index")
async def index(req: IndexRequest, background_tasks: BackgroundTasks):
    index_id = str(uuid.uuid4())

    background_tasks.add_task(index_site, index_id, req.url)

    return {
        "index_id": index_id,
        "status": "started"
    }


# ---------------------------
# Status endpoint
# ---------------------------
@app.get("/index/{index_id}")
async def status(index_id: str):
    data = await run_in_threadpool(get_index, index_id)

    if not data:
        raise HTTPException(404, "Not found")

    return {
        "index_id": data[0],
        "url": data[1],
        "collection": data[2],
        "status": data[3]
    }


# ---------------------------
# Chat endpoint (OPTIMIZED STREAMING RAG)
# ---------------------------
@app.post("/chat/stream")
async def chat(req: QueryRequest):

    meta = await run_in_threadpool(get_index, req.index_id)

    if not meta:
        raise HTTPException(404, "Index not found")

    if meta[3] != "completed":
        raise HTTPException(400, "Index not ready")

    collection = meta[2]

    store = await run_in_threadpool(load_vectorstore, collection)

    docs = await run_in_threadpool(
        store.similarity_search,
        req.question,
        2  # 🔥 small k for speed
    )

    # ---------------------------
    # FAST FAIL (NO LLM CALL)
    # ---------------------------
    if not docs:
        return StreamingResponse(
            iter(["I don't know based on the provided context."]),
            media_type="text/plain"
        )

    # ---------------------------
    # Context compression (speed optimized)
    # ---------------------------
    context = "\n\n".join(
        d.page_content[:250] for d in docs
    )

    # ---------------------------
    # Ultra-light prompt (fast inference)
    # ---------------------------
    prompt = f"""
Answer ONLY using the context.

If not found, say:
"I don't know based on context."

Context:
{context}

Q: {req.question}

A:
""".strip()

    # ---------------------------
    # TRUE STREAMING (NO LIST CONVERSION)
    # ---------------------------
    async def stream():
        for chunk in llm.stream(prompt):
            if chunk.content:
                yield chunk.content

    return StreamingResponse(stream(), media_type="text/plain")


# ---------------------------
# Health check
# ---------------------------
@app.get("/")
async def root():
    return {
        "status": "running",
        "system": "optimized-fast-rag",
        "model": LLM_MODEL
    }