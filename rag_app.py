import os
import json
import math
import hashlib
import sqlite3
import requests

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
DOCS_DIR = os.path.join(PROJECT_DIR, "docs")
DB_PATH = os.path.join(PROJECT_DIR, "rag_vectors.sqlite3")

OLLAMA_BASE = os.getenv("OLLAMA_BASE", "http://localhost:11434").rstrip("/")
CHAT_MODEL = "llama3.2:1b"
EMBED_MODEL = "nomic-embed-text"


def get_embedding(text):
    """Convert text into a numerical embedding using Ollama."""
    print("Creating embedding...", flush=True)

    response = requests.post(
        f"{OLLAMA_BASE}/api/embed",
        json={"model": EMBED_MODEL, "input": text},
        timeout=60,
    )
    response.raise_for_status()

    embeddings = response.json()["embeddings"]
    if not embeddings:
        raise ValueError("Ollama returned no embeddings.")

    return embeddings[0]


def split_into_chunks(text, chunk_size=700, overlap=120):
    """Split documentation into overlapping text chunks."""
    text = text.strip()
    if not text:
        return []

    chunks = []
    start = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])

        if end == len(text):
            break

        start = end - overlap

    return chunks


def connect_database():
    """Open the existing database and create missing tables."""
    connection = sqlite3.connect(DB_PATH)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS document_chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            chunk_number INTEGER NOT NULL,
            content TEXT NOT NULL,
            embedding TEXT NOT NULL
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS document_metadata (
            source TEXT PRIMARY KEY,
            file_hash TEXT NOT NULL
        )
    """)

    connection.commit()
    return connection


def sync_knowledge_base(connection):
    """Index new or changed text files and preserve unchanged embeddings."""
    os.makedirs(DOCS_DIR, exist_ok=True)

    files = sorted(
        name for name in os.listdir(DOCS_DIR)
        if name.endswith(".txt")
        and os.path.isfile(os.path.join(DOCS_DIR, name))
    )

    print(f"Found {len(files)} documentation files.", flush=True)

    current_sources = set(files)

    for source in files:
        path = os.path.join(DOCS_DIR, source)

        with open(path, "r", encoding="utf-8") as file:
            content = file.read()

        file_hash = hashlib.sha256(
            content.encode("utf-8")
        ).hexdigest()

        row = connection.execute(
            "SELECT file_hash FROM document_metadata WHERE source = ?",
            (source,),
        ).fetchone()

        if row and row[0] == file_hash:
            print(f"Unchanged: {source}", flush=True)
            continue

        print(f"Indexing: {source}", flush=True)

        chunks = split_into_chunks(content)

        connection.execute(
            "DELETE FROM document_chunks WHERE source = ?",
            (source,),
        )

        for number, chunk in enumerate(chunks, start=1):
            embedding = get_embedding(chunk)

            connection.execute(
                """INSERT INTO document_chunks
                   (source, chunk_number, content, embedding)
                   VALUES (?, ?, ?, ?)""",
                (
                    source,
                    number,
                    chunk,
                    json.dumps(embedding),
                ),
            )

        connection.execute(
            """INSERT OR REPLACE INTO document_metadata
               (source, file_hash) VALUES (?, ?)""",
            (source, file_hash),
        )
        connection.commit()

        print(f"Indexed {len(chunks)} chunks from {source}.", flush=True)

    existing_sources = connection.execute(
        "SELECT source FROM document_metadata"
    ).fetchall()

    for (source,) in existing_sources:
        if source not in current_sources:
            connection.execute(
                "DELETE FROM document_chunks WHERE source = ?",
                (source,),
            )
            connection.execute(
                "DELETE FROM document_metadata WHERE source = ?",
                (source,),
            )

    connection.commit()

    count = connection.execute(
        "SELECT COUNT(*) FROM document_chunks"
    ).fetchone()[0]

    print(f"Knowledge base ready: {count} saved chunks.", flush=True)


def cosine_similarity(vector_a, vector_b):
    """Measure similarity between two embedding vectors."""
    if len(vector_a) != len(vector_b):
        return 0.0

    dot = sum(a * b for a, b in zip(vector_a, vector_b))
    norm_a = math.sqrt(sum(a * a for a in vector_a))
    norm_b = math.sqrt(sum(b * b for b in vector_b))

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot / (norm_a * norm_b)


def retrieve_documents(connection, question, top_k=2):
    """Find the most relevant documentation chunks."""
    question_embedding = get_embedding(question)

    rows = connection.execute(
        """SELECT source, chunk_number, content, embedding
           FROM document_chunks"""
    ).fetchall()

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

    return [item for item in results if item["similarity"] >= 0.30][:top_k]


def generate_answer(question, results):
    """Generate an answer grounded in the retrieved documentation."""
    if not results:
        return (
            "I couldn't find sufficiently relevant documentation. "
            "Please add a suitable .txt file to /home/swe/docs."
        )

    context_parts = []

    for item in results:
        context_parts.append(
            f"Source: {item['source']}\n"
            f"Content: {item['content']}"
        )

    context = "\n\n".join(context_parts)

    prompt = f"""
You are a beginner-friendly Linux troubleshooting assistant.

User's question:
{question}

Retrieved documentation:
{context}

Instructions:
- Answer the user's exact question.
- Use only documentation relevant to the question.
- Ignore unrelated retrieved material.
- Give diagnostic commands first, before commands that change system state.
- Explain what each important command checks.
- Never claim that you ran a command on the user's machine.
- Do not invent command output.
- Do not repeat the same steps.
- If the documentation does not contain enough information, say so.
- Keep the answer focused and concise.
- Finish the answer completely.
"""

    print("Generating answer with Ollama...", flush=True)

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

    answer = response.json().get("response", "").strip()

    if not answer:
        return "The model returned an empty answer. Please try again."

    return answer


def main():
    print(
        "\n=== Linux Troubleshooting Assistant: Persistent RAG ===",
        flush=True,
    )

    connection = connect_database()

    try:
        sync_knowledge_base(connection)

        print(
            "Unchanged documents do not need re-embedding.",
            flush=True,
        )

        while True:
            question = input(
                "\nDescribe your Linux problem (or type 'exit' to quit): "
            ).strip()

            if question.lower() == "exit":
                print("Goodbye!")
                break

            if not question:
                continue

            try:
                print("\nSearching documentation...", flush=True)
                results = retrieve_documents(connection, question)

                if results:
                    print("\nRelevant documentation:", flush=True)

                    for item in results:
                        print(
                            f"- {item['source']} "
                            f"(chunk {item['chunk_number']}, "
                            f"similarity: {item['similarity']:.3f})",
                            flush=True,
                        )

                answer = generate_answer(question, results)
                print("\nAnswer:\n", answer, flush=True)

            except requests.RequestException as error:
                print(
                    f"\nOllama request failed: {error}",
                    flush=True,
                )
            except (ValueError, KeyError, sqlite3.Error) as error:
                print(f"\nProcessing error: {error}", flush=True)

    finally:
        connection.close()


if __name__ == "__main__":
    main()
