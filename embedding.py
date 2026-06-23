import streamlit as st
import requests
import time
import json
from datetime import datetime

# ── Config ──────────────────────────────────────────────────────────────────
API_BASE = "http://localhost:8000"
MAX_HISTORY = 10          # last N messages kept as context
POLL_INTERVAL = 2         # seconds between status polls

# ── Page setup ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="WebMind — Site Chat",
    page_icon="🔮",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');

/* ── Root tokens ── */
:root {
    --bg:        #0d0f14;
    --surface:   #13161e;
    --panel:     #1a1e2a;
    --border:    #252a38;
    --accent:    #6C8EF5;
    --accent2:   #a78bfa;
    --text:      #e2e8f0;
    --muted:     #6b7280;
    --success:   #34d399;
    --warning:   #fbbf24;
    --danger:    #f87171;
    --user-bg:   #1e2535;
    --bot-bg:    #151a26;
    --radius:    12px;
    --font:      'Inter', sans-serif;
    --mono:      'JetBrains Mono', monospace;
}

/* ── Global reset ── */
html, body, [class*="css"] {
    font-family: var(--font) !important;
    background-color: var(--bg) !important;
    color: var(--text) !important;
}

/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 1.5rem 2rem 2rem !important; max-width: 100% !important; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: var(--surface) !important;
    border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] .block-container { padding: 1.5rem 1.2rem !important; }

/* ── Sidebar header ── */
.sidebar-logo {
    font-size: 1.45rem;
    font-weight: 600;
    letter-spacing: -0.02em;
    color: var(--text);
    margin-bottom: 0.2rem;
}
.sidebar-tagline {
    font-size: 0.75rem;
    color: var(--muted);
    margin-bottom: 1.6rem;
    letter-spacing: 0.03em;
    text-transform: uppercase;
}

/* ── Section labels ── */
.section-label {
    font-size: 0.68rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--muted);
    margin: 1.2rem 0 0.5rem;
}

/* ── URL input ── */
.stTextInput > div > div > input {
    background: var(--panel) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
    color: var(--text) !important;
    font-family: var(--mono) !important;
    font-size: 0.8rem !important;
    padding: 0.55rem 0.8rem !important;
}
.stTextInput > div > div > input:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px rgba(108,142,245,0.15) !important;
}

/* ── Buttons ── */
.stButton > button {
    width: 100%;
    background: linear-gradient(135deg, var(--accent), var(--accent2)) !important;
    color: #fff !important;
    border: none !important;
    border-radius: var(--radius) !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
    padding: 0.6rem 1rem !important;
    transition: opacity 0.15s, transform 0.1s !important;
    letter-spacing: 0.01em;
}
.stButton > button:hover { opacity: 0.88 !important; transform: translateY(-1px) !important; }
.stButton > button:active { transform: translateY(0) !important; }

/* ── Status pills ── */
.pill {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.25rem 0.7rem;
    border-radius: 999px;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.04em;
}
.pill-success { background: rgba(52,211,153,0.15); color: var(--success); }
.pill-warning { background: rgba(251,191,36,0.15); color: var(--warning); }
.pill-danger  { background: rgba(248,113,113,0.15); color: var(--danger);  }
.pill-info    { background: rgba(108,142,245,0.15); color: var(--accent);  }

/* ── Indexed site card ── */
.site-card {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 0.7rem 0.9rem;
    margin-bottom: 0.5rem;
    cursor: pointer;
    transition: border-color 0.15s, background 0.15s;
}
.site-card:hover { border-color: var(--accent); background: #1f2436; }
.site-card.active {
    border-color: var(--accent);
    background: rgba(108,142,245,0.08);
}
.site-card-url {
    font-family: var(--mono);
    font-size: 0.72rem;
    color: var(--accent);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.site-card-meta {
    font-size: 0.65rem;
    color: var(--muted);
    margin-top: 0.2rem;
}

/* ── Chat area ── */
.chat-header {
    display: flex;
    align-items: center;
    gap: 0.8rem;
    padding-bottom: 1rem;
    border-bottom: 1px solid var(--border);
    margin-bottom: 1.2rem;
}
.chat-site-badge {
    font-family: var(--mono);
    font-size: 0.78rem;
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 0.3rem 0.7rem;
    color: var(--accent);
}
.chat-title { font-size: 1.05rem; font-weight: 600; }

/* ── Messages ── */
.msg-row {
    display: flex;
    gap: 0.8rem;
    margin-bottom: 1rem;
    align-items: flex-start;
}
.msg-row.user { flex-direction: row-reverse; }

.msg-avatar {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.85rem;
    flex-shrink: 0;
    margin-top: 2px;
}
.msg-avatar.user-av { background: linear-gradient(135deg,var(--accent),var(--accent2)); }
.msg-avatar.bot-av  { background: var(--panel); border: 1px solid var(--border); }

.msg-bubble {
    max-width: 72%;
    padding: 0.75rem 1rem;
    border-radius: 14px;
    font-size: 0.9rem;
    line-height: 1.6;
}
.msg-bubble.user {
    background: var(--user-bg);
    border: 1px solid var(--border);
    border-top-right-radius: 4px;
}
.msg-bubble.bot {
    background: var(--bot-bg);
    border: 1px solid var(--border);
    border-top-left-radius: 4px;
}
.msg-time {
    font-size: 0.65rem;
    color: var(--muted);
    margin-top: 0.25rem;
    text-align: right;
}
.msg-row.user .msg-time { text-align: left; }

/* ── Empty state ── */
.empty-state {
    text-align: center;
    padding: 4rem 2rem;
    color: var(--muted);
}
.empty-icon { font-size: 3rem; margin-bottom: 1rem; }
.empty-title { font-size: 1.1rem; font-weight: 600; color: var(--text); margin-bottom: 0.4rem; }
.empty-desc  { font-size: 0.85rem; line-height: 1.6; }

/* ── Chat input override ── */
.stChatInput textarea {
    background: var(--panel) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
    color: var(--text) !important;
    font-size: 0.9rem !important;
}
.stChatInput textarea:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px rgba(108,142,245,0.15) !important;
}

/* ── Spinner ── */
.stSpinner > div { border-color: var(--accent) transparent transparent transparent !important; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 4px; }

/* ── Divider ── */
hr { border-color: var(--border) !important; margin: 1rem 0 !important; }

/* ── Info box ── */
.info-box {
    background: rgba(108,142,245,0.08);
    border: 1px solid rgba(108,142,245,0.25);
    border-radius: var(--radius);
    padding: 0.7rem 0.9rem;
    font-size: 0.8rem;
    color: var(--accent);
    line-height: 1.5;
}

/* ── Progress bar ── */
.stProgress > div > div > div { background: var(--accent) !important; }
</style>
""", unsafe_allow_html=True)


# ── Session state defaults ────────────────────────────────────────────────────
def _init_state():
    defaults = {
        "sessions": {},          # index_id -> {url, history: [{role,content,time}]}
        "active_id": None,       # currently selected index_id
        "indexed_sites": {},     # index_id -> {url, status, indexed_at}
        "indexing_jobs": {},     # index_id -> url  (in-progress)
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()


# ── API helpers ───────────────────────────────────────────────────────────────
def api_index(url: str) -> dict | None:
    try:
        r = requests.post(f"{API_BASE}/index", json={"url": url}, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Index request failed: {e}")
        return None


def api_status(index_id: str) -> dict | None:
    try:
        r = requests.get(f"{API_BASE}/index/{index_id}", timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def api_stream_chat(index_id: str, question: str) -> requests.Response | None:
    """Return a streaming response object."""
    try:
        return requests.post(
            f"{API_BASE}/chat/stream",
            json={"index_id": index_id, "question": question, "top_k": 5},
            stream=True,
            timeout=60,
        )
    except Exception as e:
        st.error(f"Chat request failed: {e}")
        return None


# ── Context builder ───────────────────────────────────────────────────────────
def build_context_question(history: list, new_question: str) -> str:
    """
    Prepend last MAX_HISTORY turns to the question so the backend LLM
    has conversational context without needing a server-side session.
    """
    if not history:
        return new_question

    recent = history[-(MAX_HISTORY * 2):]          # each turn = 2 items
    context_lines = []
    for msg in recent:
        role = "User" if msg["role"] == "user" else "Assistant"
        context_lines.append(f"{role}: {msg['content']}")

    return (
        "Conversation so far:\n"
        + "\n".join(context_lines)
        + f"\n\nUser: {new_question}\n\nAnswer:"
    )


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="sidebar-logo">🔮 WebMind</div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-tagline">Chat with any website</div>', unsafe_allow_html=True)

    # ── Index a new site ──────────────────────────────────────────────────────
    st.markdown('<div class="section-label">Index a website</div>', unsafe_allow_html=True)

    url_input = st.text_input(
        label="URL",
        placeholder="https://docs.example.com",
        label_visibility="collapsed",
        key="url_input",
    )

    if st.button("Crawl & Index", key="btn_index"):
        raw_url = url_input.strip()
        if not raw_url:
            st.warning("Paste a URL first.")
        else:
            # Check if already in local state
            already = next(
                (iid for iid, info in st.session_state.indexed_sites.items()
                 if info["url"] == raw_url and info["status"] == "completed"),
                None,
            )
            if already:
                st.session_state.active_id = already
                st.info("Already indexed — switching to that site.")
            else:
                with st.spinner("Submitting to crawler…"):
                    result = api_index(raw_url)
                if result:
                    iid = result["index_id"]
                    status = result.get("status", "started")

                    if status == "already_indexed":
                        # Backend confirmed it's done
                        st.session_state.indexed_sites[iid] = {
                            "url": raw_url,
                            "status": "completed",
                            "indexed_at": datetime.now().strftime("%H:%M"),
                        }
                        st.session_state.active_id = iid
                        st.success("Already indexed — ready to chat!")
                    else:
                        st.session_state.indexing_jobs[iid] = raw_url
                        st.session_state.indexed_sites[iid] = {
                            "url": raw_url,
                            "status": "processing",
                            "indexed_at": None,
                        }
                        st.info("Crawling started — status updates below.")

    # ── Poll in-progress jobs ─────────────────────────────────────────────────
    pending = {iid: url for iid, url in st.session_state.indexing_jobs.items()}
    if pending:
        st.markdown('<div class="section-label">Indexing in progress</div>', unsafe_allow_html=True)
        for iid, url in list(pending.items()):
            data = api_status(iid)
            if data:
                current_status = data.get("status", "")
                if current_status == "completed":
                    st.session_state.indexed_sites[iid]["status"] = "completed"
                    st.session_state.indexed_sites[iid]["indexed_at"] = (
                        datetime.now().strftime("%H:%M")
                    )
                    del st.session_state.indexing_jobs[iid]
                    st.success(f"✓ {url[:40]}… is ready!")
                elif current_status.startswith("failed"):
                    st.session_state.indexed_sites[iid]["status"] = "failed"
                    del st.session_state.indexing_jobs[iid]
                    st.error(f"Failed: {current_status}")
                else:
                    st.markdown(
                        f'<div class="pill pill-warning">⏳ crawling…</div> '
                        f'<span style="font-size:0.72rem;color:#6b7280">{url[:35]}…</span>',
                        unsafe_allow_html=True,
                    )
        if pending:
            time.sleep(POLL_INTERVAL)
            st.rerun()

    # ── Indexed sites list ────────────────────────────────────────────────────
    completed = {
        iid: info
        for iid, info in st.session_state.indexed_sites.items()
        if info["status"] == "completed"
    }

    if completed:
        st.markdown('<div class="section-label">Indexed sites</div>', unsafe_allow_html=True)
        for iid, info in completed.items():
            is_active = iid == st.session_state.active_id
            card_class = "site-card active" if is_active else "site-card"
            display_url = info["url"].replace("https://", "").replace("http://", "")
            tag = (
                f'<span style="color:var(--success);font-size:0.65rem">● ready</span>'
                if is_active else
                f'<span style="font-size:0.65rem;color:var(--muted)">click to chat</span>'
            )

            st.markdown(
                f"""
                <div class="{card_class}" id="card-{iid}">
                    <div class="site-card-url">{display_url}</div>
                    <div class="site-card-meta">{tag}
                    {"· indexed " + info['indexed_at'] if info.get('indexed_at') else ''}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            # Invisible button overlay for click handling
            if st.button(
                "select",
                key=f"select_{iid}",
                help=f"Chat with {info['url']}",
            ):
                st.session_state.active_id = iid
                st.rerun()

    st.markdown("---")
    st.markdown(
        '<div style="font-size:0.68rem;color:var(--muted);line-height:1.6">'
        '⚡ Streaming · 🔒 Session-isolated · 👥 Multi-user'
        '</div>',
        unsafe_allow_html=True,
    )


# ── Main chat panel ───────────────────────────────────────────────────────────
active_id = st.session_state.active_id
active_info = st.session_state.indexed_sites.get(active_id) if active_id else None

if not active_id or not active_info:
    # ── Empty state ───────────────────────────────────────────────────────────
    st.markdown(
        """
        <div class="empty-state">
            <div class="empty-icon">🔮</div>
            <div class="empty-title">No site selected</div>
            <div class="empty-desc">
                Paste a URL in the sidebar and click <strong>Crawl &amp; Index</strong>.<br>
                Once indexed, select it to start chatting.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    site_url = active_info["url"]
    display_url = site_url.replace("https://", "").replace("http://", "")

    # ── Chat header ───────────────────────────────────────────────────────────
    col_title, col_badge, col_clear = st.columns([5, 3, 1.2])
    with col_title:
        st.markdown(
            '<div class="chat-title">💬 Chat</div>',
            unsafe_allow_html=True,
        )
    with col_badge:
        st.markdown(
            f'<div class="chat-site-badge" title="{site_url}">🌐 {display_url[:38]}</div>',
            unsafe_allow_html=True,
        )
    with col_clear:
        if st.button("Clear", key="clear_chat", help="Clear chat history"):
            if active_id in st.session_state.sessions:
                st.session_state.sessions[active_id]["history"] = []
            st.rerun()

    st.markdown('<hr>', unsafe_allow_html=True)

    # ── Ensure session exists ─────────────────────────────────────────────────
    if active_id not in st.session_state.sessions:
        st.session_state.sessions[active_id] = {"url": site_url, "history": []}

    history = st.session_state.sessions[active_id]["history"]

    # ── Context info banner ───────────────────────────────────────────────────
    if history:
        turns = len(history) // 2
        kept  = min(turns, MAX_HISTORY)
        st.markdown(
            f'<div class="info-box">🧠 Remembering last <strong>{kept}</strong> '
            f'turn{"s" if kept != 1 else ""} of this conversation as context.</div>',
            unsafe_allow_html=True,
        )
        st.markdown("")

    # ── Render history ────────────────────────────────────────────────────────
    chat_container = st.container()
    with chat_container:
        if not history:
            st.markdown(
                f"""
                <div style="text-align:center;padding:2.5rem 1rem;color:var(--muted)">
                    <div style="font-size:2rem;margin-bottom:0.6rem">💡</div>
                    <div style="font-size:0.9rem;color:var(--text);font-weight:500;margin-bottom:0.3rem">
                        Ask anything about {display_url}
                    </div>
                    <div style="font-size:0.8rem">
                        Try: "Summarise this site" · "What are the main features?" · "How do I get started?"
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            for msg in history:
                role = msg["role"]
                content = msg["content"]
                ts = msg.get("time", "")
                if role == "user":
                    with st.chat_message("user", avatar="👤"):
                        st.markdown(content)
                        if ts:
                            st.caption(ts)
                else:
                    with st.chat_message("assistant", avatar="🔮"):
                        st.markdown(content)
                        if ts:
                            st.caption(ts)

    # ── Chat input ────────────────────────────────────────────────────────────
    user_input = st.chat_input(
        placeholder=f"Ask something about {display_url}…",
        key="chat_input",
    )

    if user_input:
        now = datetime.now().strftime("%H:%M")

        # Append user message
        history.append({"role": "user", "content": user_input, "time": now})

        # Show user message immediately
        with st.chat_message("user", avatar="👤"):
            st.markdown(user_input)
            st.caption(now)

        # Build context-aware question
        context_question = build_context_question(history[:-1], user_input)

        # Stream assistant response
        with st.chat_message("assistant", avatar="🔮"):
            response_placeholder = st.empty()
            full_response = ""

            with st.spinner("Thinking…"):
                resp = api_stream_chat(active_id, context_question)

            if resp and resp.status_code == 200:
                for chunk in resp.iter_content(chunk_size=None, decode_unicode=True):
                    if chunk:
                        full_response += chunk
                        response_placeholder.markdown(full_response + "▌")
                response_placeholder.markdown(full_response)
                st.caption(datetime.now().strftime("%H:%M"))
            elif resp:
                try:
                    err = resp.json().get("detail", "Unknown error")
                except Exception:
                    err = resp.text or "Unknown error"
                full_response = f"⚠️ {err}"
                response_placeholder.error(full_response)
            else:
                full_response = "⚠️ Could not reach the API."
                response_placeholder.error(full_response)

        # Append assistant message
        history.append({
            "role": "assistant",
            "content": full_response,
            "time": datetime.now().strftime("%H:%M"),
        })
        st.session_state.sessions[active_id]["history"] = history
        st.rerun()