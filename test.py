import streamlit as st
import requests
import uuid
from datetime import datetime

API_BASE = "http://localhost:8000"
POLL_INTERVAL = 2


def init():
    if "user_id" not in st.session_state:
        st.session_state.user_id = str(uuid.uuid4())

    if "active_index" not in st.session_state:
        st.session_state.active_index = None

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = {}

    if "index_jobs" not in st.session_state:
        st.session_state.index_jobs = {}


init()

def create_index(url: str):
    return requests.post(
        f"{API_BASE}/index",
        json={
            "url": url,
            "user_id": st.session_state.user_id,
        },
        timeout=20,
    )


def get_status(index_id: str):
    return requests.get(
        f"{API_BASE}/index/{index_id}",
        params={"user_id": st.session_state.user_id},
        timeout=10,
    )


def chat_stream(index_id: str, question: str):
    return requests.post(
        f"{API_BASE}/chat/stream",
        json={
            "index_id": index_id,
            "question": question,
            "user_id": st.session_state.user_id,
            "top_k": 5,
        },
        stream=True,
        timeout=120,
    )


st.set_page_config(
    page_title="WebMind RAG",
    page_icon="🧠",
    layout="wide",
)

st.title("🧠 WebMind — Multi-Tenant RAG System")


with st.sidebar:

    st.header(" Control Panel")
    st.caption(f"User: {st.session_state.user_id[:8]}")

  
    st.subheader("🔗 Index Website")

    url = st.text_input("Enter URL")

    if st.button("🚀 Index"):
        if url.strip():

            res = create_index(url)

            if res.status_code == 200:
                data = res.json()
                index_id = data["index_id"]

                st.session_state.index_jobs[index_id] = {
                    "url": url,
                    "status": "processing",
                }

                st.success("Indexing started")
                st.rerun()

    st.subheader("⏳ Active Jobs")

    for index_id, job in list(st.session_state.index_jobs.items()):

        try:
            res = get_status(index_id)
            data = res.json()
            status = data.get("status")

            if status == "completed":
                st.success(f"Ready: {job['url'][:40]}")
                del st.session_state.index_jobs[index_id]

            elif "failed" in status:
                st.error(f"Failed: {job['url'][:40]}")
                del st.session_state.index_jobs[index_id]

            else:
                st.info(f"Processing: {job['url'][:40]}")

        except Exception:
            st.warning("Status check failed")

    # ── INDEX LIST
    st.subheader("📚 Indexed Sites")

    for index_id, job in st.session_state.index_jobs.items():
        if st.button(job["url"][:35], key=index_id):
            st.session_state.active_index = index_id
            st.rerun()


active = st.session_state.active_index

if not active:
    st.info("Select an indexed website to start chatting.")
    st.stop()


if active not in st.session_state.chat_history:
    st.session_state.chat_history[active] = []

history = st.session_state.chat_history[active]


st.subheader("💬 Chat with Website")


# ── CHAT RENDER
for msg in history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])


# ── INPUT
question = st.chat_input("Ask something...")

if question:

    history.append({"role": "user", "content": question})

    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        box = st.empty()
        answer = ""

        response = chat_stream(active, question)

        if response.status_code == 200:

            for chunk in response.iter_content(decode_unicode=True):
                if chunk:
                    answer += chunk
                    box.markdown(answer + "▌")

            box.markdown(answer)

        else:
            answer = "Error generating response"
            box.error(answer)

    history.append({"role": "assistant", "content": answer})