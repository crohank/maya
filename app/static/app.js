"use strict";

// Rolling clip buffer: two MediaRecorders staggered by half a segment. The one
// that started earlier always holds between SEGMENT_MS/2 and SEGMENT_MS of the
// most recent video, so a tap gets 5 to 10 s ending at the tap. A WebM chunk
// list cannot be trimmed from the front (only the first chunk has headers),
// hence two recorders instead of one with a timeslice.
const SEGMENT_MS = 10000;
const MAX_QUESTION_MS = 15000;
const MIN_CLIP_MS = 2000;

const $ = (id) => document.getElementById(id);
const answerEl = $("answer");
const statusEl = $("status");
const askBtn = $("ask-btn");
const readBtn = $("read-btn");
const cameraBtn = $("camera-btn");
const preview = $("preview");
const player = $("player");

let stream = null;
let recorders = [];
let questionRec = null;
let questionTimer = null;
let busy = false;

const SILENT_WAV = "data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAIA+AAACABAAZGF0YQAAAAA=";

function setStatus(text) { statusEl.textContent = text; }

function showAnswer(text) {
  // Clear first so screen readers announce a repeated identical answer.
  answerEl.textContent = "";
  setTimeout(() => { answerEl.textContent = text; }, 50);
}

function pickType(candidates) {
  if (!window.MediaRecorder) return "";
  return candidates.find((t) => MediaRecorder.isTypeSupported(t)) || "";
}
const VIDEO_TYPE = pickType(["video/webm;codecs=vp8,opus", "video/webm", "video/mp4"]);
const AUDIO_TYPE = pickType(["audio/webm;codecs=opus", "audio/webm", "audio/mp4"]);

function extFor(type) { return type.includes("mp4") ? ".mp4" : ".webm"; }

// iOS only plays audio started inside a tap; priming the element in the tap
// lets the answer play later when the network reply arrives.
function unlockAudio() {
  player.src = SILENT_WAV;
  player.play().catch(() => {});
}

async function startCamera() {
  if (stream) return true;
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    setStatus("This browser cannot use the camera here. Open the page over https.");
    return false;
  }
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: { ideal: "environment" }, width: { ideal: 1280 }, height: { ideal: 720 } },
      audio: true,
    });
  } catch (e) {
    setStatus("Camera or microphone permission was refused. " + e.message);
    return false;
  }
  preview.srcObject = stream;
  cameraBtn.textContent = "Camera is on";
  cameraBtn.disabled = true;
  startRolling();
  setStatus("Camera on. Ready.");
  return true;
}

function newRecorder() {
  const rec = { chunks: [], started: Date.now(), mr: null, timer: null };
  rec.mr = new MediaRecorder(stream, VIDEO_TYPE ? { mimeType: VIDEO_TYPE } : undefined);
  rec.mr.ondataavailable = (e) => { if (e.data && e.data.size) rec.chunks.push(e.data); };
  rec.mr.start(1000);
  rec.timer = setTimeout(() => restart(rec), SEGMENT_MS);
  return rec;
}

function restart(rec) {
  const i = recorders.indexOf(rec);
  if (i < 0) return;
  clearTimeout(rec.timer);
  try { rec.mr.stop(); } catch (e) { /* already stopped */ }
  recorders[i] = newRecorder();
}

function startRolling() {
  if (!window.MediaRecorder) {
    setStatus("This browser cannot record video. Use Read this, or upload a video.");
    return;
  }
  recorders = [newRecorder()];
  setTimeout(() => { if (stream) recorders.push(newRecorder()); }, SEGMENT_MS / 2);
}

function grabClip() {
  // Oldest running recorder holds the longest stretch ending now.
  const rec = recorders.slice().sort((a, b) => a.started - b.started)[0];
  // A recorder stopped right after it started (camera just switched on, or a
  // restart) returns a header-only blob; a phone sent a 5-byte clip that way.
  const wait = Math.max(0, MIN_CLIP_MS - (Date.now() - rec.started));
  return new Promise((resolve) => setTimeout(resolve, wait)).then(() => new Promise((resolve) => {
    clearTimeout(rec.timer);
    rec.mr.onstop = () => {
      const type = rec.mr.mimeType || VIDEO_TYPE || "video/webm";
      resolve(new Blob(rec.chunks, { type }));
      const i = recorders.indexOf(rec);
      if (i >= 0) recorders[i] = newRecorder();
    };
    rec.mr.stop();
  }));
}

function recordQuestion() {
  const audioOnly = new MediaStream(stream.getAudioTracks());
  const chunks = [];
  const mr = new MediaRecorder(audioOnly, AUDIO_TYPE ? { mimeType: AUDIO_TYPE } : undefined);
  mr.ondataavailable = (e) => { if (e.data && e.data.size) chunks.push(e.data); };
  const done = new Promise((resolve) => {
    mr.onstop = () => resolve(new Blob(chunks, { type: mr.mimeType || AUDIO_TYPE || "audio/webm" }));
  });
  mr.start();
  return { mr, done };
}

async function onAsk() {
  unlockAudio();
  if (busy) return;
  if (!(await startCamera())) return;

  if (!questionRec) {
    if (recorders.length === 0) { setStatus("Video recording is not available in this browser."); return; }
    const clipPromise = grabClip();
    questionRec = recordQuestion();
    questionRec.clip = clipPromise;
    askBtn.dataset.recording = "true";
    askBtn.textContent = "Listening. Tap to send your question";
    setStatus("Listening. Ask your question, then tap the same button.");
    questionTimer = setTimeout(onAsk, MAX_QUESTION_MS);
    return;
  }

  clearTimeout(questionTimer);
  const q = questionRec;
  questionRec = null;
  askBtn.dataset.recording = "false";
  askBtn.textContent = "Ask about what is in front of me";
  q.mr.stop();
  const [clip, audio] = await Promise.all([q.clip, q.done]);
  const form = new FormData();
  form.append("file", clip, "clip" + extFor(clip.type));
  form.append("question_audio", audio, "question" + extFor(audio.type));
  await send(form);
}

async function onRead() {
  unlockAudio();
  if (busy) return;
  if (!(await startCamera())) return;
  if (!preview.videoWidth) { setStatus("Camera is still starting. Try again."); return; }
  const canvas = document.createElement("canvas");
  canvas.width = preview.videoWidth;
  canvas.height = preview.videoHeight;
  canvas.getContext("2d").drawImage(preview, 0, 0);
  const blob = await new Promise((r) => canvas.toBlob(r, "image/jpeg", 0.92));
  const form = new FormData();
  form.append("file", blob, "frame.jpg");
  form.append("question", "Read the text");
  await send(form);
}

function onUpload(input, kind) {
  unlockAudio();
  const f = input.files && input.files[0];
  input.value = "";
  if (!f) return;
  const form = new FormData();
  form.append("file", f, f.name);
  const q = $("question").value.trim();
  if (q) form.append("question", q);
  setStatus("Sending the " + kind + ".");
  send(form);
}

async function send(form) {
  busy = true;
  askBtn.disabled = readBtn.disabled = true;
  setStatus("Thinking. Please wait.");
  const t0 = performance.now();
  try {
    const res = await fetch("/ask", { method: "POST", body: form });
    const data = await res.json();
    showAnswer(data.text || "No answer.");
    const secs = ((performance.now() - t0) / 1000).toFixed(1);
    setStatus((data.question ? "You asked: " + data.question + ". " : "") + "Answered in " + secs + " seconds.");
    if (data.audio_b64 && $("speak-toggle").checked) {
      player.src = "data:audio/wav;base64," + data.audio_b64;
      player.play().catch(() => setStatus("Answer ready. Audio could not play; the text is above."));
    }
  } catch (e) {
    showAnswer("Could not reach Maya. Check the connection and try again.");
    setStatus("Network error: " + e.message);
  } finally {
    busy = false;
    askBtn.disabled = readBtn.disabled = false;
  }
}

askBtn.addEventListener("click", onAsk);
readBtn.addEventListener("click", onRead);
cameraBtn.addEventListener("click", () => { unlockAudio(); startCamera(); });
$("photo-btn").addEventListener("click", () => $("photo-input").click());
$("video-btn").addEventListener("click", () => $("video-input").click());
$("audio-btn").addEventListener("click", () => $("audio-input").click());
$("photo-input").addEventListener("change", (e) => onUpload(e.target, "photo"));
$("video-input").addEventListener("change", (e) => onUpload(e.target, "video"));
$("audio-input").addEventListener("change", (e) => onUpload(e.target, "sound"));

// Permission state "granted" means no prompt, so the camera can start on load.
// Otherwise wait for a tap; iOS shows the prompt either way but a tap is clearer.
(async () => {
  if (!window.isSecureContext) {
    setStatus("Not a secure page. Open Maya with https so the camera and microphone work.");
    return;
  }
  try {
    const p = await navigator.permissions.query({ name: "camera" });
    if (p.state === "granted") { await startCamera(); return; }
  } catch (e) { /* permissions API missing on some browsers */ }
  setStatus("Ready. The camera starts on your first tap.");
})();
