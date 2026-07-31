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
from app.rag import (
    build_retrieval_query,
    format_chat_history,
    format_context,
    format_references,
    normalize_history,
    retrieve_documents,
)

VISION_SYSTEM = """You are Medically, a multimodal medical information assistant with vision.
An image IS attached to this request. You can see it — never say you cannot analyze,
view, or access the image.

How to answer:
1) First describe what you actually see (location, color, texture, lesions, swelling, etc.).
2) Then give possible educational differentials that fit the visible findings AND the
   retrieved knowledge-base context / conversation history.
3) Do not invent details that are not visible. If the photo is unclear, say what is unclear.
4) Keep the answer concise (3-6 sentences). Start directly with visual findings.
5) End with one short educational disclaimer (not a diagnosis; see a clinician).
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


def ask_with_image(
    question: str,
    image_path: str | Path,
    history: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    question = (question or "").strip() or (
        "Please review this medical image and describe possible concerns."
    )

    try:
        prior = normalize_history(history)
        search_query = build_retrieval_query(question, prior)
        documents = retrieve_documents(search_query)
        context = format_context(documents)
        history_text = format_chat_history(prior)
        encoded, mime = encode_image_file(image_path)

        client = OpenAI(api_key=require_openai_key())
        # Put the image first so the model grounds on pixels, then supporting text.
        completion = client.chat.completions.create(
            model=OPENAI_VISION_MODEL,
            temperature=LLM_TEMPERATURE,
            max_tokens=600,
            messages=[
                {"role": "system", "content": VISION_SYSTEM},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime};base64,{encoded}",
                                "detail": "high",
                            },
                        },
                        {
                            "type": "text",
                            "text": (
                                "Look at the attached photo and answer the patient.\n\n"
                                f"Patient question:\n{question}\n\n"
                                f"Conversation history:\n{history_text}\n\n"
                                f"Retrieved knowledge-base context (supporting only):\n{context}\n\n"
                                "Remember: describe visible findings from the photo first. "
                                "Do not claim you cannot see the image."
                            ),
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
        gc.collect()
