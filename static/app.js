const chat = document.getElementById("chat");
const form = document.getElementById("composer");
const input = document.getElementById("question");
const sendBtn = document.getElementById("send");
const imageInput = document.getElementById("image-input");
const imageBtn = document.getElementById("image-btn");
const micBtn = document.getElementById("mic-btn");
const micStatus = document.getElementById("mic-status");

let lastQuestion = "";
let mediaRecorder = null;
let audioChunks = [];
let isRecording = false;

function clearWelcome() {
  const welcome = chat.querySelector(".welcome");
  if (welcome) welcome.remove();
}

function appendMessage(role, html, className = "") {
  const wrap = document.createElement("article");
  wrap.className = `msg ${role} ${className}`.trim();
  wrap.innerHTML = html;
  chat.appendChild(wrap);
  chat.scrollTop = chat.scrollHeight;
  return wrap;
}

function userBubble() {
  return `<div class="meta">You</div><div class="bubble"></div>`;
}

function setBubbleText(node, text) {
  const bubble = node.querySelector(".bubble");
  if (bubble) bubble.textContent = text;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function renderBot(answer, references, suggestedActions) {
  const refsHtml =
    references && references.length
      ? `
      <details class="references" open>
        <summary>References (${references.length})</summary>
        <div class="ref-list">
          ${references
            .map(
              (ref) => `
            <div class="ref-item">
              <strong>[${ref.id}] ${escapeHtml(ref.source)}${
                ref.page != null ? ` · p.${escapeHtml(String(ref.page))}` : ""
              }</strong>
              <p>${escapeHtml(ref.snippet || "")}</p>
            </div>`
            )
            .join("")}
        </div>
      </details>`
      : `<details class="references" open>
          <summary>References</summary>
          <div class="ref-list"><div class="ref-item"><p>No sources were retrieved for this answer.</p></div></div>
        </details>`;

  const actions = `
    <div class="followups">
      <button type="button" class="action-btn" data-action="upload_image">Upload photo</button>
      <button type="button" class="action-btn" data-action="ask_voice">Ask by voice</button>
      <button type="button" class="action-btn" data-action="listen">Listen</button>
    </div>`;

  return `
    <div class="meta">Medically</div>
    <div class="bubble"></div>
    ${refsHtml}
    ${actions}
  `;
}

function typingIndicator() {
  return `
    <div class="meta">Medically</div>
    <div class="bubble">
      <div class="typing" aria-label="Thinking">
        <span></span><span></span><span></span>
      </div>
    </div>
  `;
}

function showError(message) {
  appendMessage(
    "bot",
    `<div class="meta">Medically</div><div class="bubble"></div>`,
    "error"
  );
  setBubbleText(chat.lastElementChild, message);
}

function wireFollowups(botNode) {
  botNode.querySelectorAll(".action-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const action = btn.getAttribute("data-action");
      if (action === "upload_image") {
        imageInput.click();
      } else if (action === "ask_voice") {
        toggleVoice();
      } else if (action === "listen") {
        const text = botNode.querySelector(".bubble")?.textContent || "";
        await listenToAnswer(text, btn);
      }
    });
  });
}

async function renderAnswer(data) {
  const botNode = appendMessage(
    "bot",
    renderBot(data.answer, data.references, data.suggested_actions)
  );
  setBubbleText(botNode, data.answer || "No answer returned.");
  wireFollowups(botNode);
}

async function ask(question) {
  const q = (question || "").trim();
  if (!q) return;

  clearWelcome();
  lastQuestion = q;

  const userNode = appendMessage("user", userBubble());
  setBubbleText(userNode, q);

  const pending = appendMessage("bot", typingIndicator());
  sendBtn.disabled = true;

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: q }),
    });
    const data = await res.json().catch(() => ({}));
    pending.remove();

    if (!res.ok) {
      showError(formatDetail(data.detail) || "Something went wrong. Try again.");
      return;
    }
    await renderAnswer(data);
  } catch (err) {
    pending.remove();
    showError(err.message || "Network error");
  } finally {
    sendBtn.disabled = false;
    input.focus();
  }
}

async function askWithImage(file, question) {
  clearWelcome();
  const q =
    (question || "").trim() ||
    lastQuestion ||
    "Please review this image and relate it to possible medical concerns.";
  lastQuestion = q;

  const userNode = appendMessage("user", userBubble());
  setBubbleText(userNode, `${q}\n[Photo attached: ${file.name}]`);

  const pending = appendMessage("bot", typingIndicator());
  sendBtn.disabled = true;

  try {
    const body = new FormData();
    body.append("image", file);
    body.append("question", q);

    const res = await fetch("/api/chat/vision", { method: "POST", body });
    const data = await res.json().catch(() => ({}));
    pending.remove();

    if (!res.ok) {
      showError(formatDetail(data.detail) || "Vision analysis failed.");
      return;
    }
    await renderAnswer(data);
  } catch (err) {
    pending.remove();
    showError(err.message || "Network error");
  } finally {
    sendBtn.disabled = false;
    imageInput.value = "";
  }
}

function formatDetail(detail) {
  if (!detail) return "";
  if (typeof detail === "string") return detail;
  try {
    return JSON.stringify(detail);
  } catch {
    return "Request failed";
  }
}

async function listenToAnswer(text, btn) {
  if (!text.trim()) return;
  const original = btn.textContent;
  btn.disabled = true;
  btn.textContent = "Speaking…";
  try {
    const res = await fetch("/api/speak", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(formatDetail(data.detail) || "TTS failed");
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const audio = new Audio(url);
    audio.onended = () => URL.revokeObjectURL(url);
    await audio.play();
  } catch (err) {
    showError(err.message || "Could not play audio");
  } finally {
    btn.disabled = false;
    btn.textContent = original;
  }
}

async function toggleVoice() {
  if (isRecording) {
    stopRecording();
    return;
  }
  if (!navigator.mediaDevices?.getUserMedia) {
    showError("Microphone is not supported in this browser.");
    return;
  }

  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    audioChunks = [];
    mediaRecorder = new MediaRecorder(stream);
    mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) audioChunks.push(event.data);
    };
    mediaRecorder.onstop = async () => {
      stream.getTracks().forEach((t) => t.stop());
      const blob = new Blob(audioChunks, { type: mediaRecorder.mimeType || "audio/webm" });
      await transcribeAndAsk(blob);
    };
    mediaRecorder.start();
    isRecording = true;
    micBtn.classList.add("recording");
    micStatus.hidden = false;
  } catch (err) {
    showError("Microphone permission denied or unavailable.");
  }
}

function stopRecording() {
  if (mediaRecorder && isRecording) {
    mediaRecorder.stop();
  }
  isRecording = false;
  micBtn.classList.remove("recording");
  micStatus.hidden = true;
}

async function transcribeAndAsk(blob) {
  const pending = appendMessage("bot", typingIndicator());
  try {
    const body = new FormData();
    body.append("audio", blob, "voice.webm");
    const res = await fetch("/api/transcribe", { method: "POST", body });
    const data = await res.json().catch(() => ({}));
    pending.remove();
    if (!res.ok) {
      showError(formatDetail(data.detail) || "Transcription failed.");
      return;
    }
    input.value = data.transcript || "";
    await ask(data.transcript);
  } catch (err) {
    pending.remove();
    showError(err.message || "Transcription error");
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const question = input.value.trim();
  if (!question) return;
  input.value = "";
  ask(question);
});

input.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    form.requestSubmit();
  }
});

document.querySelectorAll(".chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    const q = chip.getAttribute("data-q");
    if (q) ask(q);
  });
});

imageBtn.addEventListener("click", () => imageInput.click());
imageInput.addEventListener("change", () => {
  const file = imageInput.files?.[0];
  if (!file) return;
  askWithImage(file, input.value.trim() || lastQuestion);
});

micBtn.addEventListener("click", () => toggleVoice());
