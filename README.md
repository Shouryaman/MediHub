# Medically

**Multimodal AI medical assistant** — grounded RAG over a medical PDF knowledge base, with OpenAI vision and voice in one FastAPI app.

Ask about symptoms in text, upload a clinical photo, or speak. Every answer includes **source references** from your indexed documents.

> **Disclaimer:** Educational / demo use only. Not a diagnosis, treatment plan, or substitute for a licensed clinician. Always seek professional medical care for health concerns.

---

## Highlights

| Capability | Details |
|------------|---------|
| **RAG Q&A** | LangChain + FAISS + OpenAI embeddings (no local torch) |
| **Citations** | Always returns source filename, page, and snippet |
| **Vision** | GPT-4o reviews an image *with* retrieved KB context |
| **Voice in** | OpenAI Whisper speech-to-text |
| **Voice out** | OpenAI TTS (“Listen” on each reply) |
| **UI** | FastAPI + custom chat frontend (no Streamlit / Gradio) |

Built by combining a classic medical RAG chatbot with a MediEase-style vision + voice consult flow.

---

## Demo flow

1. Ask: *“I have red marks on my skin and it’s itching a lot…”*
2. Get a grounded answer + **References**
3. Click **Upload photo** to refine with vision
4. Or use **Voice** / **Listen** for speech I/O

---

## Tech stack

- **Python 3.11+**
- **FastAPI** + Uvicorn
- **OpenAI** — `gpt-4o-mini` (text + vision), Whisper (STT), TTS, `text-embedding-3-small`
- **LangChain** + **FAISS** (API embeddings — **no local torch**, Render-friendly)
- **Pillow** image resize for vision uploads
- **PyPDF** document loading
- Vanilla **HTML / CSS / JS** frontend

---

## Repository structure

```
├── app/
│   ├── main.py          # FastAPI routes
│   ├── config.py        # env + paths
│   ├── rag.py           # FAISS retrieval + text QA
│   ├── vision.py        # image + RAG (OpenAI vision)
│   └── voice.py         # Whisper STT + TTS
├── static/              # Chat UI
├── data/                # Medical PDFs (knowledge base)
├── vectorstore/db_faiss # FAISS index (generate locally if missing)
├── scripts/             # Helpers (e.g. build topic PDFs)
├── create_memory_for_llm.py
├── connect_memory_with_llm.py   # optional CLI
├── requirements.txt
├── .env.example
└── README.md
```

---

## Quick start

### 1. Clone & environment

```bash
git clone https://github.com/Shouryaman/MediHub.git
cd MediHub

python -m venv .venv

# Windows PowerShell
.venv\Scripts\Activate.ps1

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure secrets

```bash
cp .env.example .env
```

Edit `.env`:

```env
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4o-mini
OPENAI_VISION_MODEL=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-small
```

Never commit `.env`.

> **Render note:** This stack avoids local torch/sentence-transformers so photo uploads do not OOM small instances. Keep `vectorstore/db_faiss` in the deploy (rebuilt with OpenAI embeddings).
### 3. Build the vector index

Place medical PDFs in `data/`, then:

```bash
python create_memory_for_llm.py
```

This creates `vectorstore/db_faiss/`. Re-run whenever you add or change PDFs.

### 4. Run the app

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open **http://127.0.0.1:8000**

---

## Knowledge base

Default corpus under `data/` includes:

| Document | Role |
|----------|------|
| Gale Encyclopedia of Medicine (2nd ed.) | Broad medical reference |
| OpenStax integumentary (skin) extract | Anatomy — skin (CC BY) |
| WHO / EHF headache primary-care aids | Migraine / headache |
| Topic guides (eczema, diabetes, hypertension, allergy) | Focused educational briefs |

Add more **open / properly licensed** PDFs to `data/` and rebuild the index.

Chunking defaults: **500** characters, **50** overlap (`CHUNK_SIZE` / `CHUNK_OVERLAP` in `.env`).

---

## API reference

| Method | Endpoint | Body | Response |
|--------|----------|------|----------|
| `GET` | `/api/health` | — | Service status |
| `POST` | `/api/chat` | `{ "question": "..." }` | Answer + references |
| `POST` | `/api/chat/vision` | `multipart`: `image`, `question` | Vision+RAG answer + references |
| `POST` | `/api/transcribe` | `multipart`: `audio` | `{ "transcript": "..." }` |
| `POST` | `/api/speak` | `{ "text": "..." }` | MP3 audio |

### Example — text chat

```bash
curl -X POST http://127.0.0.1:8000/api/chat \
  -H "Content-Type: application/json" \
  -d "{\"question\": \"What are possible causes of itchy red skin marks?\"}"
```

### Example response shape

```json
{
  "answer": "...",
  "references": [
    {
      "id": 1,
      "source": "Medically_Eczema_and_Itchy_Rash_Guide.pdf",
      "page": 1,
      "snippet": "..."
    }
  ],
  "suggested_actions": ["upload_image", "ask_voice", "listen"]
}
```

Interactive docs: **http://127.0.0.1:8000/docs**

---

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | — | **Required** |
| `OPENAI_MODEL` | `gpt-4o-mini` | Text RAG model |
| `OPENAI_VISION_MODEL` | `gpt-4o` | Image model |
| `OPENAI_STT_MODEL` | `whisper-1` | Speech-to-text |
| `OPENAI_TTS_MODEL` | `gpt-4o-mini-tts` | Text-to-speech (falls back to `tts-1`) |
| `OPENAI_TTS_VOICE` | `coral` | TTS voice |
| `RETRIEVER_K` | `4` | Top chunks retrieved |
| `CHUNK_SIZE` | `500` | Ingest chunk size |
| `CHUNK_OVERLAP` | `50` | Ingest overlap |
| `LLM_TEMPERATURE` | `0.2` | Generation temperature |

---

## Optional CLI

```bash
python connect_memory_with_llm.py
```

Single-turn text Q&A in the terminal (same RAG backend).

---

## Notes for a new GitHub repo

- Copy `.env.example` → `.env` locally; keep `.env` out of git (see `.gitignore`).
- Large PDFs and `vectorstore/` can exceed GitHub limits — prefer:
  - documenting “run `create_memory_for_llm.py` after clone”, and/or
  - [Git LFS](https://git-lfs.com/) for big assets.
- Do **not** commit API keys, virtualenvs (`MedicalEnv/`, `.venv/`), or `tmp/` audio uploads.

Suggested `.gitignore` already covers secrets, venvs, `tmp/`, and the optional OpenStax archive.

---

## Roadmap

- [x] OpenAI RAG + FastAPI UI + always-on citations  
- [x] Vision + voice merge (MediEase-style)  
- [ ] Deploy FastAPI (Render / Railway / Hugging Face Space with Docker)  
- [ ] Stronger citation formatting (inline `[1]` markers in the answer text)  

---

## License & attribution

- Application code: add your preferred license (MIT recommended for portfolio repos).
- Knowledge PDFs retain their original licenses (e.g. OpenStax **CC BY**, WHO materials per WHO terms, Gale per your rights to that file).
- Redistribute only content you are allowed to share.

---

## Author

**Shouryaman Purohit**

Repository: [github.com/Shouryaman/MediHub](https://github.com/Shouryaman/MediHub)
