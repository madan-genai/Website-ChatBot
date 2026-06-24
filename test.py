import streamlit as st
import requests
import uuid

API_BASE = "http://localhost:8000"

# ── Page config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="WebMind RAG",
    page_icon="🧠",
    layout="wide",
)

# ── Session state init ─────────────────────────────────────────────────────
if "user_id" not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())
if "active_index" not in st.session_state:
    st.session_state.active_index = None
if "active_url" not in st.session_state:
    st.session_state.active_url = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = {}
if "index_jobs" not in st.session_state:
    st.session_state.index_jobs = {}
if "completed_sites" not in st.session_state:
    st.session_state.completed_sites = {}

# ── API helpers ────────────────────────────────────────────────────────────
def create_index(url):
    return requests.post(
        f"{API_BASE}/index",
        json={"url": url},
        timeout=20,
    )

def get_status(index_id):
    return requests.get(f"{API_BASE}/index/{index_id}", timeout=10)

def chat_stream(index_id, question):
    return requests.post(
        f"{API_BASE}/chat/stream",
        json={"index_id": index_id, "question": question},
        stream=True,
        timeout=120,
    )

# ── Sidebar ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🧠 WebMind RAG")
    st.caption(f"User: `{st.session_state.user_id[:8]}`")
    st.divider()

    # Index form
    st.markdown("#### 🔗 Index a Website")
    url_input = st.text_input("URL", placeholder="https://example.com", label_visibility="collapsed")

    if st.button("🚀 Start Indexing", use_container_width=True, type="primary"):
        if url_input.strip():
            try:
                res = create_index(url_input.strip())
                data = res.json()
                if res.status_code == 200 and "index_id" in data:
                    index_id = data["index_id"]
                    if data.get("cached"):
                        st.session_state.completed_sites[index_id] = url_input.strip()
                        st.success("Already indexed — ready to chat!")
                    else:
                        st.session_state.index_jobs[index_id] = {
                            "url": url_input.strip(),
                            "status": "processing",
                        }
                        st.success("Indexing started!")
                    st.rerun()
                else:
                    st.error("Failed to start indexing.")
            except Exception as e:
                st.error(f"Cannot reach API: {e}")
        else:
            st.warning("Please enter a URL.")

    # Active jobs
    if st.session_state.index_jobs:
        st.divider()
        st.markdown("#### ⏳ Active Jobs")
        for index_id, job in list(st.session_state.index_jobs.items()):
            try:
                res = get_status(index_id)
                data = res.json()
                status = data.get("status", "")

                if status == "completed":
                    st.session_state.completed_sites[index_id] = job["url"]
                    del st.session_state.index_jobs[index_id]
                    st.rerun()
                elif "failed" in status:
                    st.error(f"❌ {job['url'][:35]}")
                    del st.session_state.index_jobs[index_id]
                    st.rerun()
                else:
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.caption(job["url"][:35])
                    with col2:
                        st.caption("⏳")
                    pages = data.get("pages_crawled", 0)
                    chunks = data.get("chunks_created", 0)
                    st.progress(0, text=f"Pages: {pages} · Chunks: {chunks}")

            except Exception:
                st.warning("Status check failed")

    # Completed / indexed sites
    if st.session_state.completed_sites:
        st.divider()
        st.markdown("#### 📚 Indexed Sites")
        for index_id, site_url in st.session_state.completed_sites.items():
            is_active = st.session_state.active_index == index_id
            label = ("✅ " if is_active else "🌐 ") + site_url.replace("https://", "").replace("http://", "")[:32]
            if st.button(label, key=f"site_{index_id}", use_container_width=True):
                st.session_state.active_index = index_id
                st.session_state.active_url = site_url
                if index_id not in st.session_state.chat_history:
                    st.session_state.chat_history[index_id] = []
                st.rerun()

# ── Main area ──────────────────────────────────────────────────────────────
if not st.session_state.active_index:
    st.markdown("## 🧠 WebMind RAG")
    st.info("👈 Index a website from the sidebar, then select it to start chatting.")
    st.stop()

active_id = st.session_state.active_index
active_url = st.session_state.active_url or ""
history = st.session_state.chat_history.get(active_id, [])

# Header
col1, col2 = st.columns([8, 2])
with col1:
    st.markdown(f"### 💬 Chat — `{active_url}`")
with col2:
    if st.button("🗑️ Clear chat", use_container_width=True):
        st.session_state.chat_history[active_id] = []
        st.rerun()

st.divider()

# Render chat history
for msg in history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Chat input
question = st.chat_input("Ask something about this website…")

if question:
    history.append({"role": "user", "content": question})
    st.session_state.chat_history[active_id] = history

    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        box = st.empty()
        answer = ""

        try:
            response = chat_stream(active_id, question)
            if response.status_code == 200:
                for chunk in response.iter_content(decode_unicode=True):
                    if chunk:
                        answer += chunk
                        box.markdown(answer + "▌")
                box.markdown(answer)
            else:
                answer = f"Error {response.status_code}: {response.text}"
                box.error(answer)
        except Exception as e:
            answer = f"Network error: {e}"
            box.error(answer)

    history.append({"role": "assistant", "content": answer})
    st.session_state.chat_history[active_id] = history