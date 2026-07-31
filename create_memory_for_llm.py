"""Build / rebuild the FAISS knowledge base from PDFs in data/."""

from __future__ import annotations

from pathlib import Path

from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    DATA_PATH,
    DB_FAISS_PATH,
    EMBEDDING_MODEL,
    require_openai_key,
)


def load_pdf_files(data_path: Path):
    if not data_path.exists():
        raise FileNotFoundError(f"Data folder not found: {data_path}")

    loader = DirectoryLoader(
        str(data_path),
        glob="*.pdf",
        loader_cls=PyPDFLoader,
        show_progress=True,
    )
    documents = loader.load()
    if not documents:
        raise ValueError(f"No PDF files found in {data_path}. Add medical PDFs first.")

    for doc in documents:
        source = doc.metadata.get("source", "")
        doc.metadata["source"] = Path(source).name if source else "unknown.pdf"
        doc.metadata.setdefault("title", doc.metadata["source"])
    return documents


def create_chunks(documents):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )
    return splitter.split_documents(documents)


def build_vectorstore(text_chunks):
    require_openai_key()
    embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)
    # Batch to avoid huge peak memory / request bodies
    db = FAISS.from_documents(text_chunks, embeddings)
    DB_FAISS_PATH.parent.mkdir(parents=True, exist_ok=True)
    db.save_local(str(DB_FAISS_PATH))
    return db


def main():
    print(f"Loading PDFs from: {DATA_PATH}")
    print(f"Embedding model: {EMBEDDING_MODEL} (OpenAI API — no local torch)")
    documents = load_pdf_files(DATA_PATH)
    print(f"Loaded {len(documents)} pages")

    chunks = create_chunks(documents)
    print(f"Created {len(chunks)} chunks (size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP})")

    build_vectorstore(chunks)
    print(f"FAISS index saved to: {DB_FAISS_PATH}")
    print("Knowledge base ready.")


if __name__ == "__main__":
    main()
