import json
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.config import TEMP_DIR
from app.rag import ask_medically
from app.vision import ask_with_image
from app.voice import synthesize_speech, transcribe_audio

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

app = FastAPI(
    title="Medically",
    description="Multimodal medical assistant: RAG + vision + voice (OpenAI + FAISS)",
    version="3.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class HistoryMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=4000)
    history: list[HistoryMessage] = Field(default_factory=list)


class SpeakRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=4000)


class Reference(BaseModel):
    id: int
    source: str
    page: int | str | None = None
    snippet: str
    metadata: dict = Field(default_factory=dict)


class ChatResponse(BaseModel):
    answer: str
    references: list[Reference]
    suggested_actions: list[str]
    transcript: str | None = None


class TranscribeResponse(BaseModel):
    transcript: str


def _save_upload(upload: UploadFile, suffix: str) -> Path:
    TEMP_DIR.mkdir(exist_ok=True)
    ext = Path(upload.filename or f"upload{suffix}").suffix or suffix
    dest = TEMP_DIR / f"{uuid4().hex}{ext}"
    content = upload.file.read()
    if not content:
        raise ValueError("Uploaded file is empty.")
    dest.write_bytes(content)
    return dest


def _parse_history_json(raw: str) -> list[dict]:
    if not raw or not raw.strip():
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("Invalid history JSON.") from exc
    if not isinstance(data, list):
        raise ValueError("history must be a JSON list.")
    return data


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "medically", "version": "3.1.0"}


@app.post("/api/chat", response_model=ChatResponse)
def chat(payload: ChatRequest):
    try:
        history = [m.model_dump() for m in payload.history]
        return ask_medically(payload.question, history=history)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Chat failed: {exc}") from exc


@app.post("/api/chat/vision", response_model=ChatResponse)
async def chat_vision(
    image: UploadFile = File(...),
    question: str = Form(""),
    history: str = Form("[]"),
):
    path = None
    try:
        path = _save_upload(image, ".jpg")
        prior = _parse_history_json(history)
        return ask_with_image(question, path, history=prior)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Vision chat failed: {exc}") from exc
    finally:
        if path and path.exists():
            path.unlink(missing_ok=True)


@app.post("/api/transcribe", response_model=TranscribeResponse)
async def transcribe(audio: UploadFile = File(...)):
    path = None
    try:
        path = _save_upload(audio, ".webm")
        text = transcribe_audio(path)
        return {"transcript": text}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Transcription failed: {exc}") from exc
    finally:
        if path and path.exists():
            path.unlink(missing_ok=True)


@app.post("/api/speak")
def speak(payload: SpeakRequest):
    try:
        out = synthesize_speech(payload.text, TEMP_DIR / "final.mp3")
        return FileResponse(
            out,
            media_type="audio/mpeg",
            filename="medically-reply.mp3",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Speech synthesis failed: {exc}") from exc


@app.get("/")
def index():
    index_path = STATIC_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="UI not found")
    return FileResponse(index_path)


if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
