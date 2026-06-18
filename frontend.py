import streamlit as st
import requests
import time

API_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="RAG Website Chatbot",
    page_icon="🤖",
    layout="wide"
)

st.title("⚡ WEBSITE CHATBOT")


if "index_id" not in st.session_state:
    st.session_state.index_id = None

if "messages" not in st.session_state:
    st.session_state.messages = []


with st.sidebar:
    st.header("📌 Index Website")

    url = st.text_input("Enter Website URL")

    if st.button("🚀 Start Indexing"):
        if url:
            res = requests.post(f"{API_URL}/index", json={"url": url})
            data = res.json()

            st.session_state.index_id = data["index_id"]
            st.success(f"Index started: {st.session_state.index_id}")
        else:
            st.warning("Enter a valid URL")

    if st.session_state.index_id:
        st.info(f"Current Index ID:\n{st.session_state.index_id}")

        if st.button("🔄 Check Status"):
            res = requests.get(f"{API_URL}/index/{st.session_state.index_id}")
            st.json(res.json())


st.divider()
st.subheader("💬 Chat with Website")

question = st.text_input("Ask a question from indexed website")


def stream_response(question, index_id):

    response = requests.post(
        f"{API_URL}/chat/stream",
        json={
            "question": question,
            "index_id": index_id
        },
        stream=True
    )

    placeholder = st.empty()
    full_response = ""

    for chunk in response.iter_content(chunk_size=1024):
        if chunk:
            text = chunk.decode("utf-8", errors="ignore")
            full_response += text
            placeholder.markdown(full_response + "▌")

    return full_response


if st.button("💬 Ask"):

    if not st.session_state.index_id:
        st.error("Please index a website first.")
    elif not question:
        st.warning("Enter a question.")
    else:

        st.session_state.messages.append(("user", question))

        with st.container():
            st.write("### Response")

            answer = stream_response(question, st.session_state.index_id)

            st.session_state.messages.append(("assistant", answer))


st.divider()
st.subheader("🧠 Chat History")

for role, msg in st.session_state.messages[::-1]:
    if role == "user":
        st.markdown(f"🧑 **You:** {msg}")
    else:
        st.markdown(f"🤖 **Bot:** {msg}")