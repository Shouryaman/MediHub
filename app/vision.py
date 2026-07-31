"""Vision consult grounded on FAISS retrieval (MediEase → OpenAI)."""

from __future__ import annotations

import base64
import gc
from io import BytesIO
from pathlib import Path
from typing import Any

from openai import OpenAI
from PIL import Image

from app.config import (
    LLM_TEMPERATURE,
    OPENAI_VISION_MODEL,
    VISION_MAX_SIDE,
    require_openai_key,
)
from app.rag import format_context, format_references, retrieve_documents

VISION_SYSTEM = """You are Medically, a careful multimodal medical information assistant.
Use the retrieved knowledge-base context together with the patient's image and question.
Do not invent findings that are not supported by the image or the context.
If unsure, say what is uncertain and recommend seeing a clinician.
Keep the answer concise (about 3-6 sentences). Start directly.
End with one short educational disclaimer sentence.
"""


def encode_image_file(image_path: str | Path) -> tuple[str, str]:
    """Resize large uploads before base64 to cut memory on small Render instances."""
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {path}")

    with Image.open(path) as img:
        img = img.convert("RGB")
        img.thumbnail((VISION_MAX_SIDE, VISION_MAX_SIDE), Image.Resampling.LANCZOS)
        buffer = BytesIO()
        img.save(buffer, format="JPEG", quality=85, optimize=True)
        encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")

    return encoded, "image/jpeg"


def ask_with_image(question: str, image_path: str | Path) -> dict[str, Any]:
    question = (question or "").strip() or (
        "Please review this medical image and describe possible concerns."
    )

    try:
        documents = retrieve_documents(question)
        context = format_context(documents)
        encoded, mime = encode_image_file(image_path)

        client = OpenAI(api_key=require_openai_key())
        completion = client.chat.completions.create(
            model=OPENAI_VISION_MODEL,
            temperature=LLM_TEMPERATURE,
            max_tokens=500,
            messages=[
                {"role": "system", "content": VISION_SYSTEM},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                f"Patient question:\n{question}\n\n"
                                f"Retrieved knowledge-base context:\n{context}\n\n"
                                "Using the image and context, respond carefully."
                            ),
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime};base64,{encoded}",
                                "detail": "low",
                            },
                        },
                    ],
                },
            ],
        )

        answer = (completion.choices[0].message.content or "").strip()
        return {
            "answer": answer,
            "references": format_references(documents),
            "suggested_actions": ["upload_image", "ask_voice", "listen"],
            "transcript": None,
        }
    finally:
        # Help Render's small RAM reclaim buffers after large image requests
        gc.collect()
