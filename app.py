import uuid
import asyncio

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool

from models import IndexRequest, QueryRequest
from scraper import WebsiteCrawler
from vectorstore import build_vectorstore, load_vectorstore
from db import save_index, get_index
from config import LLM_MODEL, OLLAMA_BASE_URL

from langchain_ollama import ChatOllama

app = FastAPI(title="Async Production RAG Website Chatbot")

llm = ChatOllama(
    model=LLM_MODEL,
    base_url=OLLAMA_BASE_URL,
    temperature=0,
    num_ctx=1024
)

async def index_site(index_id: str, url: str):

    try:
        await run_in_threadpool(save_index, index_id, url, "", "processing")

        crawler = WebsiteCrawler(url)
        docs = await run_in_threadpool(crawler.crawl)

        if not docs:
            raise Exception("No content crawled")

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


@app.post("/index")
async def index(req: IndexRequest, background_tasks: BackgroundTasks):

    index_id = str(uuid.uuid4())

    # async-safe background execution
    background_tasks.add_task(index_site, index_id, req.url)

    return {
        "index_id": index_id,
        "status": "started"
    }

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
        2
    )

    if not docs:

        async def empty():
            yield "I don't know based on the provided website."

        return StreamingResponse(empty(), media_type="text/plain")

    context = "\n\n".join([d.page_content[:400] for d in docs])

    prompt = f"""
Use ONLY context.

Context:
{context}

Q: {req.question}

A:
"""

    async def stream():

        for chunk in await run_in_threadpool(lambda: list(llm.stream(prompt))):
            if chunk.content:
                yield chunk.content

            await asyncio.sleep(0)  # yield control to event loop

    return StreamingResponse(stream(), media_type="text/plain")


@app.get("/")
async def root():
    return {
        "status": "running",
        "system": "async-fast-production-rag"
    }