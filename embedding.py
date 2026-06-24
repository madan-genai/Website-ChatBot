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

# ── Custom CSS ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    * { font-family: 'Inter', sans-serif; }

    [data-testid="stAppViewContainer"] {
        background-color: #0f1117;
        color: #e2e8f0;
    }
    [data-testid="stSidebar"] {
        background-color: #161b27;
        border-right: 1px solid #2d3748;
    }
    [data-testid="stSidebar"] > div:first-child {
        padding-top: 1.5rem;
    }

    /* ── Brand ── */
    .brand-wrap {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 4px;
    }
    .brand-icon {
        font-size: 2rem;
        line-height: 1;
    }
    .brand-name {
        font-size: 1.35rem;
        font-weight: 700;
        color: #7c86f7;
        letter-spacing: -0.5px;
    }
    .brand-tagline {
        font-size: 0.7rem;
        color: #4a5568;
        margin-top: 2px;
        letter-spacing: 0.3px;
    }
    .session-pill {
        display: inline-block;
        background: #1a2035;
        border: 1px solid #2d3748;
        border-radius: 99px;
        padding: 2px 10px;
        font-size: 0.68rem;
        color: #4a5568;
        margin-top: 6px;
    }

    /* ── Badges ── */
    .badge {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 99px;
        font-size: 0.7rem;
        font-weight: 600;
        letter-spacing: 0.5px;
        text-transform: uppercase;
    }
    .badge-processing { background: #1e3a5f; color: #63b3ed; }
    .badge-completed  { background: #1a3a2a; color: #68d391; }
    .badge-failed     { background: #3d1a1a; color: #fc8181; }
    .badge-cached     { background: #2d2060; color: #b794f4; }

    /* ── Health ── */
    .health-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        background: #1a2035;
        border: 1px solid #2d3748;
        border-radius: 6px;
        padding: 6px 12px;
        font-size: 0.74rem;
        margin-bottom: 5px;
    }
    .health-label { color: #a0aec0; font-weight: 500; }
    .health-ok    { color: #68d391; font-weight: 600; }
    .health-error { color: #fc8181; font-weight: 600; }
    .health-warn  { color: #f6ad55; font-weight: 600; }

    /* ── Confirm boxes ── */
    .confirm-box {
        border-radius: 10px;
        padding: 12px 14px;
        font-size: 0.8rem;
        margin: 8px 0;
        line-height: 1.6;
    }
    .confirm-box code {
        font-size: 0.72rem;
        background: rgba(255,255,255,0.06);
        padding: 1px 5px;
        border-radius: 4px;
    }
    .force-box  { background: #2d1f0a; border: 1px solid #744210; color: #f6ad55; }
    .delete-box { background: #2d0a0a; border: 1px solid #742020; color: #fc8181; }
    .cached-box { background: #1a1f35; border: 1px solid #4c51bf; color: #a3bffa; }

    /* ── Site list ── */
    .site-card {
        background: #1a2035;
        border: 1px solid #2d3748;
        border-radius: 8px;
        padding: 8px 12px;
        margin-bottom: 4px;
        cursor: pointer;
        transition: border-color 0.15s;
    }
    .site-card.active {
        border-color: #7c86f7;
        background: #1e2340;
    }
    .site-card-url {
        font-size: 0.78rem;
        font-weight: 500;
        color: #e2e8f0;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    .site-card-meta {
        font-size: 0.68rem;
        color: #4a5568;
        margin-top: 2px;
    }

    /* ── Job progress ── */
    .job-row {
        background: #1a2035;
        border: 1px solid #2d3748;
        border-radius: 8px;
        padding: 8px 12px;
        margin-bottom: 6px;
        font-size: 0.78rem;
    }
    .job-url  { color: #a0aec0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .job-meta { color: #4a5568; font-size: 0.7rem; margin-top: 3px; }

    /* ── Chat header ── */
    .chat-header {
        background: #161b27;
        border: 1px solid #2d3748;
        border-radius: 10px;
        padding: 12px 18px;
        margin-bottom: 14px;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .chat-header-url {
        font-size: 0.92rem;
        color: #7c86f7;
        font-weight: 600;
        flex: 1;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    /* ── Cache hit ── */
    .cache-hit-badge {
        background: #2d2060;
        color: #b794f4;
        padding: 2px 8px;
        border-radius: 99px;
        font-size: 0.68rem;
        font-weight: 600;
    }

    /* ── Inputs & buttons ── */
    .stTextInput > div > div > input {
        background-color: #1a2035 !important;
        border: 1px solid #2d3748 !important;
        color: #e2e8f0 !important;
        border-radius: 8px !important;
        font-size: 0.85rem !important;
    }
    .stTextInput > div > div > input:focus {
        border-color: #7c86f7 !important;
        box-shadow: 0 0 0 2px rgba(124,134,247,0.15) !important;
    }
    .stButton > button {
        border-radius: 8px !important;
        font-weight: 600 !important;
        font-size: 0.8rem !important;
        transition: opacity 0.15s !important;
    }
    .stButton > button:hover { opacity: 0.85; }

    /* ── Chat messages ── */
    [data-testid="stChatMessage"] {
        background: #161b27 !important;
        border: 1px solid #2d3748 !important;
        border-radius: 10px !important;
        margin-bottom: 8px !important;
        padding: 10px 16px !important;
    }

    /* ── Empty state ── */
    .empty-state {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
        padding: 100px 40px;
        color: #4a5568;
    }
    .empty-icon  { font-size: 4rem; margin-bottom: 16px; }
    .empty-title { font-size: 1.8rem; font-weight: 700; color: #7c86f7; margin-bottom: 8px; }
    .empty-sub   { font-size: 0.88rem; color: #4a5568; line-height: 1.7; }
    .empty-stack { font-size: 0.72rem; color: #2d3748; margin-top: 24px; letter-spacing: 0.5px; }

    .steps-row {
        display: flex;
        gap: 20px;
        margin-top: 32px;
        flex-wrap: wrap;
        justify-content: center;
    }
    .step-card {
        background: #161b27;
        border: 1px solid #2d3748;
        border-radius: 10px;
        padding: 16px 20px;
        width: 160px;
        text-align: center;
    }
    .step-num  { font-size: 1.4rem; margin-bottom: 6px; }
    .step-text { font-size: 0.75rem; color: #a0aec0; line-height: 1.5; }

    hr { border-color: #2d3748 !important; }
    .stDivider { margin: 10px 0 !important; }

    /* scrollbar */
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: #0f1117; }
    ::-webkit-scrollbar-thumb { background: #2d3748; border-radius: 3px; }
</style>
""", unsafe_allow_html=True)


# ── Session state ──────────────────────────────────────────────────────────
defaults = {
    "user_id":             str(uuid.uuid4()),
    "session_id":          str(uuid.uuid4()),
    "active_index":        None,
    "active_url":          None,
    "chat_history":        {},
    "index_jobs":          {},
    "completed_sites":     {},
    "show_force_confirm":  False,
    "show_delete_confirm": False,
    "confirm_url":         None,
    "confirm_index_id":    None,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ── API helpers ────────────────────────────────────────────────────────────
def api_index(url):
    return requests.post(f"{API_BASE}/index", json={"url": url}, timeout=20)

def api_reindex(url):
    return requests.post(f"{API_BASE}/reindex", json={"url": url}, timeout=20)

def api_delete(index_id):
    return requests.delete(f"{API_BASE}/index/{index_id}", timeout=10)

def api_status(index_id):
    return requests.get(f"{API_BASE}/index/{index_id}", timeout=10)

def api_chat_stream(index_id, question, session_id):
    return requests.post(
        f"{API_BASE}/chat/stream",
        json={"index_id": index_id, "question": question, "session_id": session_id},
        stream=True,
        timeout=120,
    )

def api_chat_history(index_id, session_id):
    return requests.get(
        f"{API_BASE}/chat/history/{index_id}",
        params={"session_id": session_id},
        timeout=10,
    )

def api_clear_history(index_id, session_id):
    return requests.delete(
        f"{API_BASE}/chat/history/{index_id}",
        params={"session_id": session_id},
        timeout=10,
    )

def api_health():
    try:
        return requests.get(f"{API_BASE}/health", timeout=5).json()
    except Exception:
        return None


# ── Helpers ────────────────────────────────────────────────────────────────
def url_already_indexed(url):
    url = url.strip()
    for iid, u in st.session_state.completed_sites.items():
        if u.strip() == url:
            return iid
    return None

def url_in_progress(url):
    url = url.strip()
    for iid, job in st.session_state.index_jobs.items():
        if job["url"].strip() == url:
            return iid
    return None

def load_history_from_db(index_id):
    try:
        res = api_chat_history(index_id, st.session_state.session_id)
        if res.status_code == 200:
            msgs = res.json().get("messages", [])
            st.session_state.chat_history[index_id] = [
                {"role": m["role"], "content": m["content"]} for m in msgs
            ]
    except Exception:
        st.session_state.chat_history[index_id] = []

def health_icon(val):
    if val == "ok":          return "🟢"
    if "error" in str(val): return "🔴"
    return "🟡"

def health_cls(val):
    if val == "ok":          return "health-ok"
    if "error" in str(val): return "health-error"
    return "health-warn"

def shorten_url(url, n=32):
    return url.replace("https://","").replace("http://","")[:n]


# ══════════════════════════════════════════════════════════════════
#  SIDEBAR
# ══════════════════════════════════════════════════════════════════
with st.sidebar:

    # Brand
    st.markdown(f"""
    <div class="brand-wrap">
        <span class="brand-icon">🧠</span>
        <div>
            <div class="brand-name">WebMind RAG</div>
            <div class="brand-tagline">Chat with any website</div>
        </div>
    </div>
    <div class="session-pill">⚡ Session: {st.session_state.user_id[:8]}…</div>
    """, unsafe_allow_html=True)

    st.divider()

    # ── Health ─────────────────────────────────────────────────────
    with st.expander("❤️ System Health", expanded=False):
        health = api_health()
        if health:
            checks  = health.get("checks", {})
            overall = health.get("status", "unknown")
            ok_cls  = "health-ok" if overall == "healthy" else "health-error"
            st.markdown(
                f'<div class="health-row">'
                f'<span class="health-label">Overall</span>'
                f'<span class="{ok_cls}">{overall.upper()}</span>'
                f'</div>',
                unsafe_allow_html=True
            )
            for svc, val in checks.items():
                icon = health_icon(val)
                cls  = health_cls(val)
                st.markdown(
                    f'<div class="health-row">'
                    f'<span class="health-label">{icon} {svc}</span>'
                    f'<span class="{cls}">{val}</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )
        else:
            st.error("❌ API unreachable — is the backend running?")

    st.divider()

    # ── URL Input ──────────────────────────────────────────────────
    st.markdown("#### 🔗 Index a Website")
    url_input = st.text_input(
        "Website URL",
        placeholder="https://example.com",
        label_visibility="collapsed",
        key="url_field"
    )

    # Smart hint below URL
    if url_input.strip():
        if url_already_indexed(url_input.strip()):
            st.markdown(
                '<div class="cached-box">✅ <b>Already indexed.</b> Click <b>Index</b> to open '
                'chat, or <b>Force Re-scrape</b> to refresh.</div>',
                unsafe_allow_html=True
            )
        elif url_in_progress(url_input.strip()):
            st.markdown(
                '<div class="cached-box">⏳ <b>Indexing in progress…</b><br>'
                'Check the Processing section below.</div>',
                unsafe_allow_html=True
            )

    col_a, col_b = st.columns(2)
    with col_a:
        start_btn = st.button("🚀 Index", use_container_width=True, type="primary")
    with col_b:
        force_btn = st.button("🔄 Force Re-scrape", use_container_width=True,
                              help="Delete existing data and re-crawl from scratch")

    # ── Handle Index ───────────────────────────────────────────────
    if start_btn and url_input.strip():
        url = url_input.strip()
        existing_id = url_already_indexed(url)
        if existing_id:
            st.session_state.active_index = existing_id
            st.session_state.active_url   = url
            load_history_from_db(existing_id)
            st.toast("✅ Already indexed — chat ready!", icon="✅")
            st.rerun()
        else:
            try:
                res  = api_index(url)
                data = res.json()
                if res.status_code == 200 and "index_id" in data:
                    iid = data["index_id"]
                    if data.get("cached"):
                        st.session_state.completed_sites[iid] = url
                        st.session_state.active_index = iid
                        st.session_state.active_url   = url
                        load_history_from_db(iid)
                        st.toast("✅ Already indexed — chat ready!", icon="✅")
                    else:
                        st.session_state.index_jobs[iid] = {"url": url}
                        st.toast("🚀 Indexing started!", icon="🚀")
                    st.rerun()
                else:
                    st.error(f"Failed: {data}")
            except Exception as e:
                st.error(f"API error: {e}")

    # ── Handle Force ───────────────────────────────────────────────
    if force_btn and url_input.strip():
        st.session_state.show_force_confirm  = True
        st.session_state.show_delete_confirm = False
        st.session_state.confirm_url         = url_input.strip()
        st.rerun()

    # ── Force confirm ──────────────────────────────────────────────
    if st.session_state.show_force_confirm and st.session_state.confirm_url:
        curl = st.session_state.confirm_url
        st.markdown(
            f'<div class="confirm-box force-box">'
            f'⚠️ <b>Force Re-scrape?</b><br>'
            f'<code>{curl[:48]}</code><br>'
            f'Existing index + chat history will be deleted.</div>',
            unsafe_allow_html=True
        )
        fc1, fc2 = st.columns(2)
        with fc1:
            if st.button("✅ Confirm", use_container_width=True, type="primary", key="force_ok"):
                try:
                    res  = api_reindex(curl)
                    data = res.json()
                    if res.status_code == 200 and "index_id" in data:
                        iid = data["index_id"]
                        for old_id, u in list(st.session_state.completed_sites.items()):
                            if u.strip() == curl.strip():
                                del st.session_state.completed_sites[old_id]
                                if st.session_state.active_index == old_id:
                                    st.session_state.active_index = None
                                    st.session_state.active_url   = None
                                break
                        st.session_state.index_jobs[iid]    = {"url": curl}
                        st.session_state.show_force_confirm = False
                        st.session_state.confirm_url        = None
                        st.toast("🔄 Re-scrape started!", icon="🔄")
                        st.rerun()
                    else:
                        st.error(f"Reindex failed: {data}")
                except Exception as e:
                    st.error(f"API error: {e}")
        with fc2:
            if st.button("❌ Cancel", use_container_width=True, key="force_no"):
                st.session_state.show_force_confirm = False
                st.session_state.confirm_url        = None
                st.rerun()

    # ── Active jobs ────────────────────────────────────────────────
    if st.session_state.index_jobs:
        st.divider()
        st.markdown("#### ⏳ Processing")
        for iid, job in list(st.session_state.index_jobs.items()):
            try:
                data   = api_status(iid).json()
                status = data.get("status", "")
                pages  = data.get("pages_crawled",  0) or 0
                chunks = data.get("chunks_created", 0) or 0

                if status == "completed":
                    st.session_state.completed_sites[iid] = job["url"]
                    del st.session_state.index_jobs[iid]
                    if not st.session_state.active_index:
                        st.session_state.active_index = iid
                        st.session_state.active_url   = job["url"]
                        load_history_from_db(iid)
                    st.toast("✅ Indexing complete!", icon="✅")
                    st.rerun()

                elif "failed" in str(status):
                    err = data.get("error_message", "Unknown error")
                    st.markdown(
                        f'<div class="job-row">'
                        f'<span class="badge badge-failed">FAILED</span> '
                        f'<span class="job-url">{shorten_url(job["url"])}</span>'
                        f'<div class="job-meta">↳ {err[:70]}</div>'
                        f'</div>',
                        unsafe_allow_html=True
                    )
                    del st.session_state.index_jobs[iid]
                    st.rerun()

                else:
                    st.markdown(
                        f'<div class="job-row">'
                        f'<span class="badge badge-processing">CRAWLING</span> '
                        f'<span class="job-url">{shorten_url(job["url"])}</span>'
                        f'<div class="job-meta">📄 {pages} pages &nbsp;·&nbsp; 🧩 {chunks} chunks</div>'
                        f'</div>',
                        unsafe_allow_html=True
                    )
                    st.progress(0.0)

            except Exception:
                st.warning("⚠️ Status check failed")

    # ── Completed sites ────────────────────────────────────────────
    if st.session_state.completed_sites:
        st.divider()
        st.markdown("#### 📚 Indexed Sites")
        for iid, site_url in list(st.session_state.completed_sites.items()):
            is_active = st.session_state.active_index == iid
            short     = shorten_url(site_url, 30)
            label     = ("✅  " if is_active else "🌐  ") + short

            if st.button(label, key=f"site_{iid}", use_container_width=True,
                         type="primary" if is_active else "secondary"):
                st.session_state.active_index = iid
                st.session_state.active_url   = site_url
                load_history_from_db(iid)
                st.rerun()

            if st.button("🗑️ Delete", key=f"del_{iid}", use_container_width=True):
                st.session_state.show_delete_confirm = True
                st.session_state.show_force_confirm  = False
                st.session_state.confirm_index_id    = iid
                st.session_state.confirm_url         = site_url
                st.rerun()

    # ── Delete confirm ─────────────────────────────────────────────
    if st.session_state.show_delete_confirm and st.session_state.confirm_index_id:
        ciid = st.session_state.confirm_index_id
        curl = st.session_state.confirm_url or ""
        st.markdown(
            f'<div class="confirm-box delete-box">'
            f'🗑️ <b>Delete Index?</b><br>'
            f'<code>{curl[:48]}</code><br>'
            f'All data + chat history permanently removed.</div>',
            unsafe_allow_html=True
        )
        dc1, dc2 = st.columns(2)
        with dc1:
            if st.button("✅ Delete", use_container_width=True, type="primary", key="del_ok"):
                try:
                    res = api_delete(ciid)
                    if res.status_code == 200:
                        st.session_state.completed_sites.pop(ciid, None)
                        st.session_state.chat_history.pop(ciid, None)
                        if st.session_state.active_index == ciid:
                            st.session_state.active_index = None
                            st.session_state.active_url   = None
                        st.session_state.show_delete_confirm = False
                        st.session_state.confirm_index_id    = None
                        st.session_state.confirm_url         = None
                        st.toast("🗑️ Index deleted!", icon="🗑️")
                        st.rerun()
                    else:
                        st.error(f"Delete failed: {res.text}")
                except Exception as e:
                    st.error(f"API error: {e}")
        with dc2:
            if st.button("❌ Cancel", use_container_width=True, key="del_no"):
                st.session_state.show_delete_confirm = False
                st.session_state.confirm_index_id    = None
                st.rerun()


# ══════════════════════════════════════════════════════════════════
#  MAIN AREA — Empty state
# ══════════════════════════════════════════════════════════════════
if not st.session_state.active_index:
    st.markdown("""
    <div class="empty-state">
        <div class="empty-icon">🧠</div>
        <div class="empty-title">WebMind RAG</div>
        <div class="empty-sub">
            Paste any website URL in the sidebar and click <b>Index</b>.<br>
            Once indexed, select it to start chatting with its content.
        </div>

        <div class="steps-row">
            <div class="step-card">
                <div class="step-num">🔗</div>
                <div class="step-text">Paste a website URL in the sidebar</div>
            </div>
            <div class="step-card">
                <div class="step-num">🚀</div>
                <div class="step-text">Click Index and wait for crawling</div>
            </div>
            <div class="step-card">
                <div class="step-num">💬</div>
                <div class="step-text">Ask anything about the website</div>
            </div>
        </div>

        <div class="empty-stack">Ollama · Qdrant · MySQL · Redis · FastAPI</div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()


# ══════════════════════════════════════════════════════════════════
#  MAIN AREA — Chat
# ══════════════════════════════════════════════════════════════════
active_id  = st.session_state.active_index
active_url = st.session_state.active_url or ""
history    = st.session_state.chat_history.get(active_id, [])

# ── Header row ─────────────────────────────────────────────────────────────
h1, h2, h3, h4 = st.columns([5, 2, 2, 2])
with h1:
    st.markdown(
        f'<div class="chat-header">'
        f'<span style="font-size:1.2rem">💬</span>'
        f'<span class="chat-header-url">{active_url}</span>'
        f'<span class="badge badge-completed">READY</span>'
        f'</div>',
        unsafe_allow_html=True
    )
with h2:
    if st.button("🔄 Re-scrape", use_container_width=True):
        st.session_state.show_force_confirm  = True
        st.session_state.show_delete_confirm = False
        st.session_state.confirm_url         = active_url
        st.rerun()
with h3:
    if st.button("🗑️ Del Index", use_container_width=True):
        st.session_state.show_delete_confirm = True
        st.session_state.show_force_confirm  = False
        st.session_state.confirm_index_id    = active_id
        st.session_state.confirm_url         = active_url
        st.rerun()
with h4:
    if st.button("💬 Clear Chat", use_container_width=True):
        try:
            api_clear_history(active_id, st.session_state.session_id)
        except Exception:
            pass
        st.session_state.chat_history[active_id] = []
        st.rerun()

# ── Chat messages ──────────────────────────────────────────────────────────
for msg in history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ── Chat input ─────────────────────────────────────────────────────────────
question = st.chat_input("Ask something about this website…")

if question:
    history.append({"role": "user", "content": question})
    st.session_state.chat_history[active_id] = history

    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        box         = st.empty()
        answer      = ""
        chunks_list = []

        try:
            response = api_chat_stream(active_id, question, st.session_state.session_id)

            if response.status_code == 200:
                for chunk in response.iter_content(decode_unicode=True):
                    if chunk:
                        chunks_list.append(chunk)
                        answer += chunk
                        box.markdown(answer + "▌")

                # Cache hit = answer came in very few chunks almost instantly
                is_cached = len(chunks_list) <= 2 and answer.strip()

                if is_cached:
                    box.markdown(
                        answer + "\n\n"
                        '<span class="cache-hit-badge">⚡ Cached response</span>',
                        unsafe_allow_html=True
                    )
                else:
                    box.markdown(answer)

            else:
                answer = f"⚠️ Error {response.status_code}: {response.text}"
                box.error(answer)

        except Exception as e:
            answer = f"⚠️ Network error: {e}"
            box.error(answer)

    history.append({"role": "assistant", "content": answer})
    st.session_state.chat_history[active_id] = history