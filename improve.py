import streamlit as st
import requests
import time

# ---------------------------
# CONFIG
# ---------------------------
API_BASE = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="Fast RAG Chatbot",
    layout="wide"
)

# ---------------------------
# SESSION STATE
# ---------------------------
if "index_id" not in st.session_state:
    st.session_state.index_id = None

if "messages" not in st.session_state:
    st.session_state.messages = []

# ---------------------------
# SIDEBAR - INDEX WEBSITE
# ---------------------------
st.sidebar.title("⚡ Website Indexing")

url = st.sidebar.text_input("Enter website URL")

if st.sidebar.button("Index Website"):
    if url:
        res = requests.post(
            f"{API_BASE}/index",
            json={"url": url}
        )

        data = res.json()
        st.session_state.index_id = data["index_id"]

        st.sidebar.success(f"Index started: {st.session_state.index_id}")
    else:
        st.sidebar.warning("Enter a URL")


# ---------------------------
# INDEX STATUS CHECK
# ---------------------------
if st.session_state.index_id:
    st.sidebar.markdown("### 📌 Index Status")

    status_res = requests.get(
        f"{API_BASE}/index/{st.session_state.index_id}"
    )

    if status_res.status_code == 200:
        status = status_res.json()["status"]
        st.sidebar.info(f"Status: {status}")


# ---------------------------
# MAIN CHAT UI
# ---------------------------
st.title("💬 Fast RAG Chatbot")

if not st.session_state.index_id:
    st.warning("Please index a website first from sidebar.")
    st.stop()

# ---------------------------
# DISPLAY CHAT HISTORY
# ---------------------------
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ---------------------------
# USER INPUT
# ---------------------------
user_input = st.chat_input("Ask something about the website...")

if user_input:

    # Add user message
    st.session_state.messages.append({
        "role": "user",
        "content": user_input
    })

    with st.chat_message("user"):
        st.markdown(user_input)

    # Placeholder for assistant response
    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_response = ""

        # ---------------------------
        # STREAM REQUEST
        # ---------------------------
        response = requests.post(
            f"{API_BASE}/chat/stream",
            json={
                "index_id": st.session_state.index_id,
                "question": user_input
            },
            stream=True
        )

        # ---------------------------
        # STREAMING OUTPUT
        # ---------------------------
        for chunk in response.iter_content(chunk_size=32):
            if chunk:
                text = chunk.decode("utf-8")
                full_response += text
                placeholder.markdown(full_response)

        # Save response
        st.session_state.messages.append({
            "role": "assistant",
            "content": full_response
        })