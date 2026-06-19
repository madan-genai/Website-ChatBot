import uuid
import asyncio

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool

from models import IndexRequest, QueryRequest
from scraper import WebsiteCrawler
from vectorstore import build_vectorstore, load_vectorstore, retrieve_documents
from db import save_index, get_index
from config import LLM_MODEL, OLLAMA_BASE_URL

from langchain_ollama import ChatOllama


app = FastAPI(title="Production RAG Website Chatbot")


# =========================
# LLM (Qwen 2.5 1.5B)
# =========================
llm = ChatOllama(
    model=LLM_MODEL,  # qwen2.5:1.5b
    base_url=OLLAMA_BASE_URL,
    temperature=0,
    num_ctx=4096,
)

async def index_site(index_id: str, url: str):
    try:
        await run_in_threadpool(save_index, index_id, url, "", "processing")

        crawler = WebsiteCrawler(url)
        docs = await run_in_threadpool(crawler.crawl)

        if not docs:
            raise Exception("No content crawled from website")

        collection_name = f"site_{index_id}"

        await run_in_threadpool(
            build_vectorstore,
            docs,
            collection_name,
        )

        await run_in_threadpool(
            save_index,
            index_id,
            url,
            collection_name,
            "completed",
        )

    except Exception as e:
        await run_in_threadpool(
            save_index,
            index_id,
            url,
            "",
            f"failed: {str(e)}",
        )

@app.post("/index")
async def index(req: IndexRequest, background_tasks: BackgroundTasks):
    index_id = str(uuid.uuid4())

    background_tasks.add_task(index_site, index_id, req.url)

    return {
        "index_id": index_id,
        "status": "started",
    }

@app.get("/index/{index_id}")
async def status(index_id: str):
    data = await run_in_threadpool(get_index, index_id)

    if not data:
        raise HTTPException(status_code=404, detail="Index not found")

    return {
        "index_id": data[0],
        "url": data[1],
        "collection": data[2],
        "status": data[3],
    }

@app.post("/chat/stream")
async def chat(req: QueryRequest):

    meta = await run_in_threadpool(get_index, req.index_id)

    if not meta:
        raise HTTPException(status_code=404, detail="Index not found")

    if meta[3] != "completed":
        raise HTTPException(status_code=400, detail="Index not ready")

    collection_name = meta[2]

    # Load vector store
    store = await run_in_threadpool(load_vectorstore, collection_name)

    
    docs = await run_in_threadpool(
        retrieve_documents,
        store,
        req.question,
        4,
    )

    
    if not docs:

        async def no_context_stream():
            yield "I don't know based on the provided context."

        return StreamingResponse(no_context_stream(), media_type="text/plain")

    # Build context
    context = "\n\n".join(
        d.page_content[:400] for d in docs
    )

    prompt = f"""
You are a precise website assistant.

Rules:
- Use ONLY the provided context
- Do NOT hallucinate
- If answer is missing, say exactly:
  "I don't know based on the provided context."

Context:
{context}

Question:
{req.question}

Answer:
""".strip()

    # Streaming generator
    async def stream():

        def generate():
            for chunk in llm.stream(prompt):
                if chunk.content:
                    yield chunk.content

        for token in generate():
            yield token
            await asyncio.sleep(0)

    return StreamingResponse(stream(), media_type="text/plain")


@app.get("/")
async def root():
    return {
        "status": "running",
        "system": "production-rag-chatbot",
        "model": LLM_MODEL,
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy"
    }