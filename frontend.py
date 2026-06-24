import time
import uuid
import requests
import streamlit as st

API_BASE_DEFAULT = "http://localhost:8000"

st.set_page_config(
    page_title="WebMind RAG",
    page_icon="🧠",
    layout="wide",
)

st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    * { font-family: 'Inter', sans-serif; }
    [data-testid="stAppViewContainer"] { background-color: #0f1117; color: #e2e8f0; }
    [data-testid="stSidebar"] { background-color: #161b27; border-right: 1px solid #2d3748; }
    [data-testid="stSidebar"] > div:first-child { padding-top: 1.5rem; }
    .brand-wrap { display: flex; align-items: center; gap: 10px; margin-bottom: 4px; }
    .brand-icon { font-size: 2rem; line-height: 1; }
    .brand-name { font-size: 1.35rem; font-weight: 700; color: #7c86f7; letter-spacing: -0.5px; }
    .brand-tagline { font-size: 0.7rem; color: #94a3b8; margin-top: 2px; letter-spacing: 0.3px; }
    .session-pill { display: inline-block; background: #1a2035; border: 1px solid #2d3748; border-radius: 999px; padding: 2px 10px; font-size: 0.68rem; color: #94a3b8; margin-top: 6px; }
    .badge { display: inline-block; padding: 2px 10px; border-radius: 999px; font-size: 0.7rem; font-weight: 600; letter-spacing: 0.4px; text-transform: uppercase; }
    .badge-processing { background: #1e3a5f; color: #63b3ed; }
    .badge-completed  { background: #1a3a2a; color: #68d391; }
    .badge-failed     { background: #3d1a1a; color: #fc8181; }
    .badge-other      { background: #2d3748; color: #e2e8f0; }
    .confirm-box { border-radius: 10px; padding: 12px 14px; font-size: 0.8rem; margin: 8px 0; line-height: 1.6; }
    .confirm-box code { font-size: 0.72rem; background: rgba(255,255,255,0.06); padding: 1px 5px; border-radius: 4px; }
    .force-box  { background: #2d1f0a; border: 1px solid #744210; color: #f6ad55; }
    .delete-box { background: #2d0a0a; border: 1px solid #742020; color: #fc8181; }
    .health-row { display: flex; align-items: center; justify-content: space-between; background: #1a2035; border: 1px solid #2d3748; border-radius: 6px; padding: 6px 12px; font-size: 0.74rem; margin-bottom: 5px; }
    .health-label { color: #a0aec0; font-weight: 500; }
    .health-ok    { color: #68d391; font-weight: 600; }
    .health-error { color: #fc8181; font-weight: 600; }
    .health-warn  { color: #f6ad55; font-weight: 600; }
    .site-card { background: #1a2035; border: 1px solid #2d3748; border-radius: 8px; padding: 10px 12px; margin-bottom: 8px; }
    .site-card.active-card { border-color: #7c86f7; background: #1e2340; }
    .site-url { font-size: 0.78rem; font-weight: 600; color: #e2e8f0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .site-meta { font-size: 0.68rem; color: #94a3b8; margin-top: 4px; line-height: 1.5; }
    .chat-header { background: #161b27; border: 1px solid #2d3748; border-radius: 10px; padding: 12px 18px; margin-bottom: 14px; display: flex; align-items: center; gap: 10px; }
    .chat-header-url { font-size: 0.92rem; color: #7c86f7; font-weight: 600; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .cache-hit-badge { background: #2d2060; color: #b794f4; padding: 2px 8px; border-radius: 999px; font-size: 0.68rem; font-weight: 600; }
    .stTextInput > div > div > input { background-color: #1a2035 !important; border: 1px solid #2d3748 !important; color: #e2e8f0 !important; border-radius: 8px !important; font-size: 0.85rem !important; }
    .stTextInput > div > div > input:focus { border-color: #7c86f7 !important; box-shadow: 0 0 0 2px rgba(124,134,247,0.15) !important; }
    .stButton > button { border-radius: 8px !important; font-weight: 600 !important; font-size: 0.8rem !important; }
    [data-testid="stChatMessage"] { background: #161b27 !important; border: 1px solid #2d3748 !important; border-radius: 10px !important; margin-bottom: 8px !important; padding: 10px 16px !important; }
    .empty-state { display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; padding: 100px 40px; color: #94a3b8; }
    .empty-icon  { font-size: 4rem; margin-bottom: 16px; }
    .empty-title { font-size: 1.8rem; font-weight: 700; color: #7c86f7; margin-bottom: 8px; }
    .empty-sub   { font-size: 0.88rem; color: #94a3b8; line-height: 1.7; }
    .steps-row { display: flex; gap: 20px; margin-top: 32px; flex-wrap: wrap; justify-content: center; }
    .step-card { background: #161b27; border: 1px solid #2d3748; border-radius: 10px; padding: 16px 20px; width: 180px; text-align: center; }
    .step-num  { font-size: 1.4rem; margin-bottom: 6px; }
    .step-text { font-size: 0.75rem; color: #a0aec0; line-height: 1.5; }
    .info-card { background: #161b27; border: 1px solid #2d3748; border-radius: 10px; padding: 14px 16px; margin-bottom: 12px; }
    .info-title { font-size: 0.75rem; color: #94a3b8; margin-bottom: 4px; text-transform: uppercase; letter-spacing: 0.4px; }
    .info-value { font-size: 0.95rem; color: #e2e8f0; font-weight: 600; word-break: break-word; }
    hr { border-color: #2d3748 !important; }
</style>
""",
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────────────────────────────────────
# Session state
# KEY CHANGE: session_index_ids — sirf is session ki indexed sites track karo
# ─────────────────────────────────────────────────────────────────────────────
DEFAULTS = {
    "user_id": str(uuid.uuid4()),
    "session_id": "default",
    "api_base": API_BASE_DEFAULT,
    "active_index": None,
    "active_url": None,
    "chat_history": {},
    "session_index_ids": [],   # ← ONLY this session's index IDs
    "indexes_cache": [],       # full details fetched from backend
    "last_refresh_ts": 0.0,
    "show_force_confirm": False,
    "show_delete_confirm": False,
    "confirm_url": None,
    "confirm_index_id": None,
}

for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ─────────────────────────────────────────────────────────────────────────────
# API helpers
# ─────────────────────────────────────────────────────────────────────────────
def api_base():
    return st.session_state.api_base.rstrip("/")

def api_get_index(index_id: str):
    return requests.get(f"{api_base()}/index/{index_id}", timeout=15)

def api_index(url: str):
    return requests.post(f"{api_base()}/index", json={"url": url}, timeout=20)

def api_reindex(url: str):
    return requests.post(f"{api_base()}/reindex", json={"url": url}, timeout=20)

def api_delete(index_id: str):
    return requests.delete(f"{api_base()}/index/{index_id}", timeout=20)

def api_status(index_id: str):
    return requests.get(f"{api_base()}/index/{index_id}", timeout=15)

def api_chat_stream(index_id: str, question: str, session_id: str):
    return requests.post(
        f"{api_base()}/chat/stream",
        json={"index_id": index_id, "question": question, "session_id": session_id},
        stream=True,
        timeout=180,
    )

def api_chat_history(index_id: str, session_id: str):
    return requests.get(
        f"{api_base()}/chat/history/{index_id}",
        params={"session_id": session_id},
        timeout=15,
    )

def api_clear_history(index_id: str, session_id: str):
    return requests.delete(
        f"{api_base()}/chat/history/{index_id}",
        params={"session_id": session_id},
        timeout=15,
    )

def api_health():
    try:
        return requests.get(f"{api_base()}/health", timeout=5).json()
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def health_icon(val):
    if val == "ok": return "🟢"
    if "error" in str(val).lower(): return "🔴"
    return "🟡"

def health_cls(val):
    sval = str(val).lower()
    if val == "ok": return "health-ok"
    if "error" in sval: return "health-error"
    return "health-warn"

def shorten_url(url, n=40):
    if not url: return ""
    short = url.replace("https://", "").replace("http://", "")
    return short[:n] + ("..." if len(short) > n else "")

def badge_html(status: str) -> str:
    status = (status or "").lower()
    if status == "completed":  return '<span class="badge badge-completed">completed</span>'
    if status == "processing": return '<span class="badge badge-processing">processing</span>'
    if status == "failed":     return '<span class="badge badge-failed">failed</span>'
    return f'<span class="badge badge-other">{status or "unknown"}</span>'

def load_history_from_db(index_id: str):
    try:
        res = api_chat_history(index_id, st.session_state.session_id)
        if res.status_code == 200:
            msgs = res.json().get("messages", [])
            st.session_state.chat_history[index_id] = [
                {"role": m["role"], "content": m["content"], "created_at": m.get("created_at")}
                for m in msgs
            ]
        else:
            st.session_state.chat_history[index_id] = []
    except Exception:
        st.session_state.chat_history[index_id] = []


# ─────────────────────────────────────────────────────────────────────────────
# SESSION-ONLY index refresh
# Sirf session_index_ids ke indexes fetch karo — baaki sab ignore
# ─────────────────────────────────────────────────────────────────────────────
def refresh_session_indexes(force=False):
    now = time.time()
    if not force and now - st.session_state.last_refresh_ts < 2:
        return st.session_state.indexes_cache

    session_ids = st.session_state.session_index_ids
    if not session_ids:
        st.session_state.indexes_cache = []
        st.session_state.last_refresh_ts = now
        return []

    updated = []
    for iid in session_ids:
        try:
            res = api_get_index(iid)
            if res.status_code == 200:
                updated.append(res.json())
            # 404 = deleted — don't add, it will be removed from session_index_ids below
        except Exception:
            pass

    # Remove deleted indexes from session tracking
    valid_ids = [x["index_id"] for x in updated]
    st.session_state.session_index_ids = [i for i in session_ids if i in valid_ids]
    st.session_state.indexes_cache = updated
    st.session_state.last_refresh_ts = now

    # If active index was deleted, unset it
    if st.session_state.active_index and st.session_state.active_index not in valid_ids:
        st.session_state.active_index = None
        st.session_state.active_url = None

    return updated


def get_session_index_by_url(url: str):
    for item in st.session_state.indexes_cache:
        if item.get("url") == url:
            return item
    return None

def get_session_index_by_id(index_id: str):
    for item in st.session_state.indexes_cache:
        if item.get("index_id") == index_id:
            return item
    return None

def add_to_session(index_id: str):
    """Add index_id to this session's tracking list."""
    if index_id not in st.session_state.session_index_ids:
        st.session_state.session_index_ids.append(index_id)


# Initial load
refresh_session_indexes(force=True)


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        f"""
        <div class="brand-wrap">
            <span class="brand-icon">🧠</span>
            <div>
                <div class="brand-name">WebMind RAG</div>
                <div class="brand-tagline">Chat with any website</div>
            </div>
        </div>
        <div class="session-pill">Session: {st.session_state.session_id}</div>
        """,
        unsafe_allow_html=True,
    )

    st.divider()

    st.markdown("#### ⚙️ Backend")
    new_api_base = st.text_input(
        "FastAPI URL",
        value=st.session_state.api_base,
        key="api_base_input",
        help="Example: http://localhost:8000",
    )
    if new_api_base != st.session_state.api_base:
        st.session_state.api_base = new_api_base.strip()
        refresh_session_indexes(force=True)

    colb1, colb2 = st.columns(2)
    with colb1:
        if st.button("🔄 Refresh", use_container_width=True):
            refresh_session_indexes(force=True)
            st.rerun()
    with colb2:
        if st.button("🩺 Health", use_container_width=True):
            pass

    with st.expander("❤️ System Health", expanded=False):
        health = api_health()
        if health:
            checks = health.get("checks", {})
            overall = health.get("status", "unknown")
            overall_cls = "health-ok" if overall == "healthy" else "health-error"
            st.markdown(
                f'<div class="health-row"><span class="health-label">Overall</span>'
                f'<span class="{overall_cls}">{overall.upper()}</span></div>',
                unsafe_allow_html=True,
            )
            for svc, val in checks.items():
                st.markdown(
                    f'<div class="health-row"><span class="health-label">{health_icon(val)} {svc}</span>'
                    f'<span class="{health_cls(val)}">{val}</span></div>',
                    unsafe_allow_html=True,
                )
        else:
            st.error("API unreachable. Start FastAPI first.")

    st.divider()

    # ── Index form ──────────────────────────────────────────────────────────
    st.markdown("#### 🔗 Index a Website")
    url_input = st.text_input(
        "Website URL",
        placeholder="https://example.com",
        label_visibility="collapsed",
        key="url_field",
    )

    if url_input.strip():
        matched = get_session_index_by_url(url_input.strip())
        if matched:
            st.info(
                f"Already indexed in this session · status = **{matched.get('status', 'unknown')}**\n\n"
                "Click **Index** to open, or **Force Re-scrape** to rebuild."
            )

    c1, c2 = st.columns(2)
    with c1:
        start_btn = st.button("🚀 Index", use_container_width=True, type="primary")
    with c2:
        force_btn = st.button("🔄 Force Re-scrape", use_container_width=True)

    # ── Start / open ────────────────────────────────────────────────────────
    if start_btn and url_input.strip():
        try:
            res = api_index(url_input.strip())
            data = res.json()

            if res.status_code == 200 and "index_id" in data:
                idx = data["index_id"]
                add_to_session(idx)          # ← track in this session
                refresh_session_indexes(force=True)

                row = get_session_index_by_id(idx)
                if row and row.get("status") == "completed":
                    st.session_state.active_index = idx
                    st.session_state.active_url = row.get("url")
                    load_history_from_db(idx)
                    st.toast("Index ready. Opening chat.", icon="✅")
                else:
                    st.toast(f"Index job started.", icon="🚀")
                st.rerun()
            else:
                st.error(data.get("detail", str(data)))
        except Exception as e:
            st.error(f"Index request failed: {e}")

    # ── Force re-scrape ─────────────────────────────────────────────────────
    if force_btn and url_input.strip():
        st.session_state.show_force_confirm = True
        st.session_state.show_delete_confirm = False
        st.session_state.confirm_url = url_input.strip()
        st.rerun()

    if st.session_state.show_force_confirm and st.session_state.confirm_url:
        curl = st.session_state.confirm_url
        st.markdown(
            f'<div class="confirm-box force-box">⚠️ <b>Force Re-scrape?</b><br>'
            f'<code>{curl}</code><br>'
            f'Existing index, vector data, cache, and chat history will be replaced.</div>',
            unsafe_allow_html=True,
        )
        fc1, fc2 = st.columns(2)
        with fc1:
            if st.button("✅ Confirm", use_container_width=True, type="primary", key="force_ok"):
                try:
                    res = api_reindex(curl)
                    data = res.json()
                    if res.status_code == 200 and "index_id" in data:
                        idx = data["index_id"]
                        add_to_session(idx)       # ← track new index_id
                        st.session_state.show_force_confirm = False
                        st.session_state.confirm_url = None
                        refresh_session_indexes(force=True)
                        st.toast("Reindex started.", icon="🔄")
                        st.rerun()
                    else:
                        st.error(data.get("detail", str(data)))
                except Exception as e:
                    st.error(f"Reindex failed: {e}")
        with fc2:
            if st.button("❌ Cancel", use_container_width=True, key="force_no"):
                st.session_state.show_force_confirm = False
                st.session_state.confirm_url = None
                st.rerun()

    # ── Session indexes list ─────────────────────────────────────────────────
    st.divider()
    st.markdown("#### 📚 This Session's Sites")

    indexes = refresh_session_indexes(force=False)

    if not indexes:
        st.caption("No sites indexed yet in this session.")
    else:
        def sort_key(x):
            order = {"processing": 0, "completed": 1, "failed": 2}
            return (order.get(x.get("status", ""), 99), x.get("created_at") or "")

        for item in sorted(indexes, key=sort_key):
            iid = item["index_id"]
            url = item.get("url", "")
            status = item.get("status", "")
            pages = item.get("pages_crawled", 0) or 0
            chunks = item.get("chunks_created", 0) or 0
            err = item.get("error_message")
            created_at = item.get("created_at")
            is_active = st.session_state.active_index == iid
            card_class = "site-card active-card" if is_active else "site-card"

            st.markdown(
                f'<div class="{card_class}">'
                f'<div class="site-url">{url}</div>'
                f'<div class="site-meta">{status.upper()} · pages={pages} · chunks={chunks}<br>'
                f'created={created_at or "—"}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

            b1, b2 = st.columns(2)
            with b1:
                open_label = "💬 Open" if status == "completed" else "👁 View"
                if st.button(open_label, key=f"open_{iid}", use_container_width=True,
                             type="primary" if is_active else "secondary"):
                    st.session_state.active_index = iid
                    st.session_state.active_url = url
                    if status == "completed":
                        load_history_from_db(iid)
                    st.rerun()
            with b2:
                if st.button("🗑 Delete", key=f"delete_{iid}", use_container_width=True):
                    st.session_state.show_delete_confirm = True
                    st.session_state.show_force_confirm = False
                    st.session_state.confirm_index_id = iid
                    st.session_state.confirm_url = url
                    st.rerun()

            if status == "failed" and err:
                st.error(f"{shorten_url(url, 55)} → {err}")

    # ── Delete confirm ──────────────────────────────────────────────────────
    if st.session_state.show_delete_confirm and st.session_state.confirm_index_id:
        ciid = st.session_state.confirm_index_id
        curl = st.session_state.confirm_url or ""
        st.markdown(
            f'<div class="confirm-box delete-box">🗑️ <b>Delete Index?</b><br>'
            f'<code>{curl}</code><br>'
            f'Removes vector data, DB record, cache, and chat history.</div>',
            unsafe_allow_html=True,
        )
        dc1, dc2 = st.columns(2)
        with dc1:
            if st.button("✅ Delete", use_container_width=True, type="primary", key="del_ok"):
                try:
                    res = api_delete(ciid)
                    if res.status_code == 200:
                        # Remove from session tracking
                        st.session_state.session_index_ids = [
                            i for i in st.session_state.session_index_ids if i != ciid
                        ]
                        st.session_state.chat_history.pop(ciid, None)
                        if st.session_state.active_index == ciid:
                            st.session_state.active_index = None
                            st.session_state.active_url = None
                        st.session_state.show_delete_confirm = False
                        st.session_state.confirm_index_id = None
                        st.session_state.confirm_url = None
                        refresh_session_indexes(force=True)
                        st.toast("Index deleted.", icon="🗑️")
                        st.rerun()
                    else:
                        st.error(res.text)
                except Exception as e:
                    st.error(f"Delete failed: {e}")
        with dc2:
            if st.button("❌ Cancel", use_container_width=True, key="del_no"):
                st.session_state.show_delete_confirm = False
                st.session_state.confirm_index_id = None
                st.session_state.confirm_url = None
                st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# Main area — empty state
# ─────────────────────────────────────────────────────────────────────────────
if not st.session_state.active_index:
    st.markdown(
        """
        <div class="empty-state">
            <div class="empty-icon">🧠</div>
            <div class="empty-title">WebMind RAG</div>
            <div class="empty-sub">
                Paste a website URL in the sidebar and click <b>Index</b>.<br>
                Once the crawl finishes, open the site and start chatting with its content.
            </div>
            <div class="steps-row">
                <div class="step-card"><div class="step-num">🔗</div><div class="step-text">Paste a website URL</div></div>
                <div class="step-card"><div class="step-num">🚀</div><div class="step-text">Index or reindex the site</div></div>
                <div class="step-card"><div class="step-num">💬</div><div class="step-text">Ask questions about the content</div></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.stop()


# ─────────────────────────────────────────────────────────────────────────────
# Active index panel
# ─────────────────────────────────────────────────────────────────────────────
active_id = st.session_state.active_index
row = get_session_index_by_id(active_id)

if row is None:
    refresh_session_indexes(force=True)
    row = get_session_index_by_id(active_id)

if row is None:
    st.warning("Selected index no longer exists.")
    st.session_state.active_index = None
    st.session_state.active_url = None
    st.stop()

active_url    = row.get("url", "")
active_status = row.get("status", "")
pages         = row.get("pages_crawled", 0) or 0
chunks        = row.get("chunks_created", 0) or 0
err           = row.get("error_message")
created_at    = row.get("created_at")

# ── Processing state ────────────────────────────────────────────────────────
if active_status == "processing":
    st.markdown(
        f'<div class="chat-header"><span style="font-size:1.2rem">⏳</span>'
        f'<span class="chat-header-url">{active_url}</span>{badge_html(active_status)}</div>',
        unsafe_allow_html=True,
    )
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f'<div class="info-card"><div class="info-title">Pages Crawled</div><div class="info-value">{pages}</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="info-card"><div class="info-title">Chunks Created</div><div class="info-value">{chunks}</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="info-card"><div class="info-title">Created At</div><div class="info-value">{created_at or "—"}</div></div>', unsafe_allow_html=True)
    st.info("Indexing is running. Auto-refreshing...")
    time.sleep(2)
    refresh_session_indexes(force=True)
    st.rerun()

# ── Failed state ─────────────────────────────────────────────────────────────
if active_status == "failed":
    st.markdown(
        f'<div class="chat-header"><span style="font-size:1.2rem">❌</span>'
        f'<span class="chat-header-url">{active_url}</span>{badge_html(active_status)}</div>',
        unsafe_allow_html=True,
    )
    st.error(err or "Indexing failed.")
    f1, f2 = st.columns(2)
    with f1:
        if st.button("🔄 Re-scrape this site", use_container_width=True, type="primary"):
            st.session_state.show_force_confirm = True
            st.session_state.confirm_url = active_url
            st.rerun()
    with f2:
        if st.button("🗑 Delete failed index", use_container_width=True):
            st.session_state.show_delete_confirm = True
            st.session_state.confirm_index_id = active_id
            st.session_state.confirm_url = active_url
            st.rerun()
    st.stop()


# ─────────────────────────────────────────────────────────────────────────────
# Chat view (completed)
# ─────────────────────────────────────────────────────────────────────────────
if active_id not in st.session_state.chat_history:
    load_history_from_db(active_id)

history = st.session_state.chat_history.get(active_id, [])

h1, h2, h3, h4 = st.columns([5, 2, 2, 2])
with h1:
    st.markdown(
        f'<div class="chat-header"><span style="font-size:1.2rem">💬</span>'
        f'<span class="chat-header-url">{active_url}</span>{badge_html(active_status)}</div>',
        unsafe_allow_html=True,
    )
with h2:
    if st.button("🔄 Re-scrape", use_container_width=True):
        st.session_state.show_force_confirm = True
        st.session_state.confirm_url = active_url
        st.rerun()
with h3:
    if st.button("🗑 Del Index", use_container_width=True):
        st.session_state.show_delete_confirm = True
        st.session_state.confirm_index_id = active_id
        st.session_state.confirm_url = active_url
        st.rerun()
with h4:
    if st.button("💬 Clear Chat", use_container_width=True):
        try:
            api_clear_history(active_id, st.session_state.session_id)
        except Exception:
            pass
        st.session_state.chat_history[active_id] = []
        st.rerun()

# Metadata row
m1, m2, m3, m4 = st.columns(4)
with m1:
    st.markdown(f'<div class="info-card"><div class="info-title">Index ID</div><div class="info-value">{active_id}</div></div>', unsafe_allow_html=True)
with m2:
    st.markdown(f'<div class="info-card"><div class="info-title">Pages Crawled</div><div class="info-value">{pages}</div></div>', unsafe_allow_html=True)
with m3:
    st.markdown(f'<div class="info-card"><div class="info-title">Chunks Created</div><div class="info-value">{chunks}</div></div>', unsafe_allow_html=True)
with m4:
    st.markdown(f'<div class="info-card"><div class="info-title">Created At</div><div class="info-value">{created_at or "—"}</div></div>', unsafe_allow_html=True)

# Chat messages
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
        chunks_list = []

        try:
            response = api_chat_stream(active_id, question, st.session_state.session_id)

            if response.status_code == 200:
                for chunk in response.iter_content(chunk_size=None, decode_unicode=True):
                    if chunk:
                        chunks_list.append(chunk)
                        answer += chunk
                        box.markdown(answer + "▌")

                is_cached = len(chunks_list) <= 2 and answer.strip()
                if is_cached:
                    box.markdown(
                        answer + "\n\n" + '<span class="cache-hit-badge">⚡ Cached response</span>',
                        unsafe_allow_html=True,
                    )
                else:
                    box.markdown(answer)
            else:
                try:
                    detail = response.json()
                except Exception:
                    detail = response.text
                answer = f"⚠️ Error {response.status_code}: {detail}"
                box.error(answer)

        except Exception as e:
            answer = f"⚠️ Network error: {e}"
            box.error(answer)

    history.append({"role": "assistant", "content": answer})
    st.session_state.chat_history[active_id] = history