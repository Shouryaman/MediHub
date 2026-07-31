from __future__ import annotations

from functools import lru_cache
from typing import Any

from langchain.chains import RetrievalQA
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from app.config import (
    DB_FAISS_PATH,
    EMBEDDING_MODEL,
    LLM_TEMPERATURE,
    OPENAI_MODEL,
    RETRIEVER_K,
    require_openai_key,
)

CUSTOM_PROMPT_TEMPLATE = """You are Medically, a careful medical information assistant.
Use ONLY the context below to answer the user's question.
If the context is insufficient, say you do not know based on the available references.
Do not invent diagnoses, drugs, or dosages outside the context.
Keep the answer clear and concise. Start directly — no preamble.
Always remind the user this is educational information, not a substitute for a clinician,
but keep that reminder to one short closing sentence.

Context:
{context}

Question:
{question}
"""


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


@lru_cache(maxsize=1)
def build_qa_chain() -> RetrievalQA:
    prompt = PromptTemplate(
        template=CUSTOM_PROMPT_TEMPLATE,
        input_variables=["context", "question"],
    )
    return RetrievalQA.from_chain_type(
        llm=load_llm(),
        chain_type="stuff",
        retriever=get_vectorstore().as_retriever(search_kwargs={"k": RETRIEVER_K}),
        return_source_documents=True,
        chain_type_kwargs={"prompt": prompt},
    )


def format_references(source_documents: list[Any]) -> list[dict[str, Any]]:
    references: list[dict[str, Any]] = []
    for idx, doc in enumerate(source_documents, start=1):
        metadata = getattr(doc, "metadata", {}) or {}
        source = metadata.get("source") or metadata.get("file_path") or "Unknown source"
        page = metadata.get("page")
        if isinstance(page, int):
            page_display = page + 1  # PyPDFLoader is 0-indexed
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


def ask_medically(question: str) -> dict[str, Any]:
    question = (question or "").strip()
    if not question:
        raise ValueError("Question cannot be empty.")

    chain = build_qa_chain()
    response = chain.invoke({"query": question})
    references = format_references(response.get("source_documents") or [])

    return {
        "answer": response.get("result", "").strip(),
        "references": references,
        "suggested_actions": ["upload_image", "ask_voice", "listen"],
    }
