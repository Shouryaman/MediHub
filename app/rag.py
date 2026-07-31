from __future__ import annotations

from functools import lru_cache
from typing import Any

from langchain_community.vectorstores import FAISS
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from app.config import (
    DB_FAISS_PATH,
    EMBEDDING_MODEL,
    LLM_TEMPERATURE,
    OPENAI_MODEL,
    RETRIEVER_K,
    require_openai_key,
)

SYSTEM_PROMPT = """You are Medically, a careful medical information assistant.
Use the retrieved knowledge-base context to answer the user.
Use the conversation history to stay consistent with prior symptoms and questions.
If the context is insufficient, say you do not know based on the available references.
Do not invent diagnoses, drugs, or dosages outside the context.
Keep the answer clear and concise. Start directly — no preamble.
Always remind the user this is educational information, not a substitute for a clinician,
but keep that reminder to one short closing sentence.
"""

MAX_HISTORY_MESSAGES = 12


@lru_cache(maxsize=1)
def get_embedding_model() -> OpenAIEmbeddings:
    require_openai_key()
    return OpenAIEmbeddings(model=EMBEDDING_MODEL)


@lru_cache(maxsize=1)
def get_vectorstore() -> FAISS:
    if not DB_FAISS_PATH.exists():
        raise FileNotFoundError(
            f"FAISS index not found at {DB_FAISS_PATH}. "
            "Add PDFs to data/ and run: python create_memory_for_llm.py"
        )
    return FAISS.load_local(
        str(DB_FAISS_PATH),
        get_embedding_model(),
        allow_dangerous_deserialization=True,
    )


@lru_cache(maxsize=1)
def load_llm() -> ChatOpenAI:
    require_openai_key()
    return ChatOpenAI(
        model=OPENAI_MODEL,
        temperature=LLM_TEMPERATURE,
    )


def normalize_history(history: list[dict[str, Any]] | None) -> list[dict[str, str]]:
    if not history:
        return []
    cleaned: list[dict[str, str]] = []
    for item in history[-MAX_HISTORY_MESSAGES:]:
        role = (item.get("role") or "").strip().lower()
        content = (item.get("content") or "").strip()
        if role not in {"user", "assistant"} or not content:
            continue
        cleaned.append({"role": role, "content": content[:2000]})
    return cleaned


def format_chat_history(history: list[dict[str, str]]) -> str:
    if not history:
        return "None yet."
    lines: list[str] = []
    for msg in history:
        label = "User" if msg["role"] == "user" else "Assistant"
        lines.append(f"{label}: {msg['content']}")
    return "\n".join(lines)


def build_retrieval_query(question: str, history: list[dict[str, str]]) -> str:
    """Blend recent user turns into retrieval so follow-ups stay on-topic."""
    prior = [
        msg["content"]
        for msg in history
        if msg["role"] == "user"
    ][-3:]
    blended = " ".join([*prior, question]).strip()
    return blended[:1500] or question


def format_references(source_documents: list[Any]) -> list[dict[str, Any]]:
    references: list[dict[str, Any]] = []
    for idx, doc in enumerate(source_documents, start=1):
        metadata = getattr(doc, "metadata", {}) or {}
        source = metadata.get("source") or metadata.get("file_path") or "Unknown source"
        page = metadata.get("page")
        if isinstance(page, int):
            page_display = page + 1
        else:
            page_display = page
        snippet = " ".join((doc.page_content or "").split())
        if len(snippet) > 420:
            snippet = snippet[:417] + "..."
        references.append(
            {
                "id": idx,
                "source": str(source).split("\\")[-1].split("/")[-1],
                "page": page_display,
                "snippet": snippet,
                "metadata": {
                    k: v
                    for k, v in metadata.items()
                    if k in {"source", "page", "title", "total_pages"}
                },
            }
        )
    return references


def retrieve_documents(question: str) -> list[Any]:
    question = (question or "").strip()
    if not question:
        raise ValueError("Question cannot be empty.")
    retriever = get_vectorstore().as_retriever(search_kwargs={"k": RETRIEVER_K})
    return list(retriever.invoke(question))


def format_context(documents: list[Any]) -> str:
    if not documents:
        return "No relevant passages were retrieved."
    parts: list[str] = []
    for idx, doc in enumerate(documents, start=1):
        meta = getattr(doc, "metadata", {}) or {}
        source = str(meta.get("source", "unknown")).split("\\")[-1].split("/")[-1]
        page = meta.get("page")
        page_bit = f", page {page + 1}" if isinstance(page, int) else ""
        parts.append(f"[{idx}] ({source}{page_bit})\n{(doc.page_content or '').strip()}")
    return "\n\n".join(parts)


def ask_medically(
    question: str,
    history: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    question = (question or "").strip()
    if not question:
        raise ValueError("Question cannot be empty.")

    prior = normalize_history(history)
    search_query = build_retrieval_query(question, prior)
    documents = retrieve_documents(search_query)
    context = format_context(documents)
    history_text = format_chat_history(prior)

    user_prompt = (
        f"Conversation history:\n{history_text}\n\n"
        f"Retrieved knowledge-base context:\n{context}\n\n"
        f"Current user question:\n{question}"
    )

    response = load_llm().invoke(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
    )
    answer = (getattr(response, "content", None) or str(response)).strip()

    return {
        "answer": answer,
        "references": format_references(documents),
        "suggested_actions": ["upload_image", "ask_voice", "listen"],
    }
