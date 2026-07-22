"""CLI fallback for Medically RAG (OpenAI + FAISS). Prefer: uvicorn app.main:app"""

from app.rag import ask_medically


def main():
    question = input("Write Query Here: ").strip()
    result = ask_medically(question)

    print("\nRESULT:\n", result["answer"])
    print("\nREFERENCES:")
    if not result["references"]:
        print("No sources retrieved.")
        return

    for ref in result["references"]:
        page = ref.get("page")
        page_bit = f", p.{page}" if page is not None else ""
        print(f"\n[{ref['id']}] {ref['source']}{page_bit}")
        print(ref["snippet"])


if __name__ == "__main__":
    main()
