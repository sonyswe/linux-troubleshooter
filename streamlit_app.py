import os

import streamlit as st
import sqlite3
import requests
import json
import math

# -----------------------------
# App configuration
# -----------------------------
st.set_page_config(
    page_title="Linux Troubleshooting AI",
    page_icon="🐧",
    layout="wide",
)

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rag_vectors.sqlite3")
OLLAMA_BASE = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
CHAT_MODEL = "llama3.2:1b"
EMBED_MODEL = "nomic-embed-text"

st.title("🐧 Linux Troubleshooting AI Assistant")
st.caption("Ask questions about Linux, services, networking, and DevOps.")

# -----------------------------
# Embedding function
# -----------------------------
def get_embedding(text):
    response = requests.post(
        f"{OLLAMA_BASE}/api/embed",
        json={"model": EMBED_MODEL, "input": text},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["embeddings"][0]


# -----------------------------
# Similarity function
# -----------------------------
def cosine_similarity(a, b):
    if len(a) != len(b):
        return 0.0

    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot / (norm_a * norm_b)


# -----------------------------
# Retrieve documentation
# -----------------------------
def retrieve_documents(question, top_k=2):
    connection = sqlite3.connect(DB_PATH)

    try:
        rows = connection.execute(
            """SELECT source, chunk_number, content, embedding
               FROM document_chunks"""
        ).fetchall()
    finally:
        connection.close()

    if not rows:
        return []

    question_embedding = get_embedding(question)
    results = []

    for source, number, content, stored_embedding in rows:
        similarity = cosine_similarity(
            question_embedding,
            json.loads(stored_embedding),
        )

        results.append({
            "source": source,
            "chunk_number": number,
            "content": content,
            "similarity": similarity,
        })

    results.sort(
        key=lambda item: item["similarity"],
        reverse=True,
    )

    return [
        item for item in results
        if item["similarity"] >= 0.30
    ][:top_k]


# -----------------------------
# Generate an answer
# -----------------------------
def generate_answer(question, results):
    if not results:
        return (
            "I couldn't find relevant documentation. "
            "Try a question about Nginx or Linux services."
        )

    context = "\n\n".join(
        f"Source: {item['source']}\n{item['content']}"
        for item in results
    )

    prompt = f"""
You are a beginner-friendly Linux troubleshooting assistant.

User question:
{question}

Relevant documentation:
{context}

Instructions:
- Answer the exact question.
- Use relevant documentation and ignore unrelated content.
- Explain commands simply.
- Recommend diagnostic commands before changing system state.
- Never claim that you ran commands on the user's computer.
- Do not invent command output.
- Keep the answer concise and complete.
"""

    response = requests.post(
        f"{OLLAMA_BASE}/api/generate",
        json={
            "model": CHAT_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_predict": 350,
            },
        },
        timeout=240,
    )

    response.raise_for_status()

    return response.json().get(
        "response", "The model returned an empty answer."
    ).strip()


# -----------------------------
# Sidebar
# -----------------------------
with st.sidebar:
    st.header("About this project")
    st.write("**AI model:** llama3.2:1b")
    st.write("**Embeddings:** nomic-embed-text")
    st.write("**Knowledge base:** SQLite")
    st.write("**Architecture:** Retrieval-Augmented Generation (RAG)")

    st.divider()
    st.write("Try asking:")
    st.write("- How do I troubleshoot Nginx?")
    st.write("- How can I check disk space?")
    st.write("- How do I check a Linux service?")


# -----------------------------
# Chat interface
# -----------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

question = st.chat_input("Describe your Linux problem...")

if question:
    st.session_state.messages.append({
        "role": "user",
        "content": question,
    })

    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Searching documentation and generating an answer..."):
            try:
                documents = retrieve_documents(question)
                answer = generate_answer(question, documents)

                st.markdown(answer)

                if documents:
                    with st.expander("View retrieved documentation"):
                        for item in documents:
                            st.markdown(
                                f"**{item['source']}** — "
                                f"chunk {item['chunk_number']} "
                                f"(similarity: {item['similarity']:.3f})"
                            )
                            st.write(item["content"])

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer,
                })

            except requests.RequestException as error:
                st.error(
                    f"Could not contact Ollama. "
                    f"Check that Ollama is running. Details: {error}"
                )
            except (sqlite3.Error, ValueError, KeyError) as error:
                st.error(f"An application error occurred: {error}")
