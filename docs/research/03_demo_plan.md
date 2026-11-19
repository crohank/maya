# Research 03: Demo, evaluation, and judging plan

Written 2026-11-18 for code freeze Thu Nov 19 end of day and the live demo Fri Nov 20, 1 PM.
Inputs: `docs/research_prompts.md` (Prompt 3), `docs/decisions.md` (D1 to D4),
`docs/hardware.md`, and the OCR numbers quoted in Prompt 2. Web sources are linked
inline. Anything I could not confirm from a primary source is marked UNVERIFIED.

## 0. Where the project stands (from our own measurements)

| Capability | Status | Number we can quote |
|---|---|---|
| Short video Q&A / walk describe | Works | Model median 0.48 to 0.64 s per look, speech start minus newest frame median 0.57 to 1.18 s, 2.37 GiB peak (D3) |
| Image Q&A (signs, labels) | Works, weak on small print | Cosmos3-Edge NF4: 5/10 test images, median 1.2 s, 2.4 GiB (Prompt 2) |
| Image Q&A with Qwen3-VL-4B NF4 | Too slow for live use | 6/10, 20 to 60 s per image; vision tower 14.7 s (Prompt 2) |
| Steering ("move left/right") | Dropped | "move right" 65/85 looks; 4 of 6 hand-checked instructions wrong or dangerous (D3) |
| Text memory of earlier answers | Dropped | Model copied itself, e.g. same sentence 32/36 looks on London clip (D4) |
| Speech in, sound ID, doc Q&A, code gen + run, web UI | Not built yet (as far as the docs show) | none |

VRAM budget: 8151 MiB total, about 2.9 GB held by the desktop (hardware.md), so about
5 GB for models. Cosmos3-Edge already takes 2.4 GiB. That leaves room for small
helpers (faster-whisper small or base, AST, Piper on CPU) but not for a 7B coder at
the same time. See section 1.3.

## 1. Minimum build that scores well

### 1.1 Judging weights translated into what earns points

| Criterion | Weight | What actually moves the score |
|---|---|---|
| Multimodal checklist + our test results | 30% | Every required capability present and demonstrable (image, audio speech, audio sounds, doc Q&A with refusal, code gen + run, video), each with a small test table |
| Live demo start to finish in an easy app | 25% | One URL on a phone, one big button, voice out, no crashes, no typing at the laptop during the demo |
| Architecture | 20% | A clean diagram, why each model, VRAM and latency table, named limits, all local |
| Impact | 15% | One slide with sourced numbers and a clear "who and why offline" |
| Q&A | 10% | Short, honest answers; the decisions log is the ammunition |
| Bonus | n/a | Web + mobile: the phone browser UI already gives this for free |

The checklist plus test results (30%) rewards breadth plus evidence. The demo (25%)
rewards reliability. So the plan is: get every checkbox to "works on one easy case,
with 5 to 10 measured test cases", then harden the demo path, then polish. Depth
on any one capability (for example the perception layer from Prompt 1) is worth
less per hour than closing an empty checkbox.

### 1.2 Features ranked by points per hour

Hours are estimates for one developer plus a coding agent. "Points" is my rough
share of the 100 available, assuming the feature is shown and tested.

| Rank | Feature | Est. hours | Est. points | Points/hour | Notes |
|---|---|---|---|---|---|
| 1 | Phone web UI over HTTPS: one big "Ask" button, camera photo, mic record, audio playback | 2.5 | 15 (demo + bonus + enables everything) | 6.0 | Nothing else can be demoed without it. Do first. |
| 2 | Image Q&A on tap via Cosmos3-Edge (already measured) | 1.0 | 6 | 6.0 | Wire existing code to the UI. Use Cosmos, not Qwen3-VL, for the live path. |
| 3 | Speech in with faster-whisper (base.en or small.en, int8) | 1.0 | 5 | 5.0 | Transcribe the question, then route by keywords. |
| 4 | Voice out with Piper (already used in harness) | 0.5 | 3 | 6.0 | Return WAV to the phone, play it in the same tap gesture chain. |
| 5 | Test results tables for every capability (scripted runner + CSV + markdown) | 2.0 | 10 | 5.0 | Feeds the 30% bucket directly. Reuse `scripts/` harness style. |
| 6 | Document Q&A with "not in the document" | 2.0 | 6 | 3.0 | See 1.4 for a design that refuses reliably. |
| 7 | Sound ID with AST AudioSet (siren, horn, crosswalk beeps) | 1.5 | 5 | 3.3 | `MIT/ast-finetuned-audioset-10-10-0.4593`; AudioSet labels include siren and vehicle horn. Crosswalk chirps have no clean AudioSet label (UNVERIFIED which label fires); report it as a named limit if it misses. |
| 8 | Code generation + sandboxed execution | 2.0 | 5 | 2.5 | Small coder model, run in a subprocess or no-network container with a timeout. |
| 9 | Short video Q&A from an uploaded clip (already works in harness) | 1.0 | 4 | 4.0 | Upload a 2 to 10 s clip from the phone, ask one question. |
| 10 | Architecture slide + latency/VRAM table | 1.0 | 6 | 6.0 | Mostly writing; data already exists in decisions.md. |
| 11 | Impact slide (section 7) | 0.5 | 5 | 10.0 | Numbers are in this file. |
| 12 | Pre-recorded fallback video of the full demo | 1.0 | 5 (insurance on the 25%) | 5.0 | Record after the build freezes. |
| 13 | Accessibility pass on the UI (section 5) | 1.0 | 3 + credibility in Q&A | 3.0 | Cheap if built in from the start. |
| 14 | Live walk mode on the phone camera stream | 3.0 | 3 | 1.0 | Risky over venue Wi-Fi. Show it from a recorded clip on the laptop instead. |
| 15 | Detector + tracker perception layer (Prompt 1) | 6+ | 3 to 5 | under 1.0 | Only if everything above is done. Otherwise present as "next step" with the D2 to D4 evidence. |
| 16 | Qwen3-VL speed fix | unknown | 1 | low | Park it. Say "Qwen3-VL was 6/10 but 20 to 60 s; we chose Cosmos at 1.2 s" as an architecture decision. |

### 1.3 Model plan that fits 5 GB

| Role | Model | Approx. VRAM | Status |
|---|---|---|---|
| Video + image Q&A | `ubr-physical-ai/Cosmos3-Edge-NF4-bnb` | 2.4 GiB measured (D1, D3) | Measured |
| Speech to text | faster-whisper `base.en` or `small.en`, int8 | under 1 GB (UNVERIFIED on this GPU; CPU int8 also fine for short questions) | To measure |
| Sound ID | AST AudioSet (`MIT/ast-finetuned-audioset-10-10-0.4593`) | about 0.35 GB fp16 (UNVERIFIED), can run on CPU | To measure |
| Speech out | Piper `en_US-lessac-medium` on CPU | 0 GPU | Measured in harness (0.08 to 0.32 s, D2) |
| Code generation | Qwen2.5-Coder 7B does not fit next to Cosmos in about 5 GB. Options: Qwen2.5-Coder-1.5B or 3B Instruct in 4-bit on GPU, or 7B on CPU via llama.cpp GGUF if it is already installed (slow, UNVERIFIED speed), or load the 7B only when code mode is called and unload Cosmos | 7B NF4 about 5 GB (UNVERIFIED) | Decide by measurement |
| Document Q&A answerer | Reuse Cosmos3-Edge as the text LLM, or the coder model | none extra | To test |

Rule for the demo laptop: everything that is on the demo path stays loaded; nothing
loads from disk during the 5 minutes. If code mode needs a model swap, do that
capability last in the script and say so out loud ("swapping models, 8 seconds").

### 1.4 Document Q&A that says "not in the document" reliably

1. Extract text (PDF text layer; for a photo of a page, OCR via Cosmos).
2. Split into chunks of about 300 words; score chunks against the question with BM25
   or a small embedding model.
3. If the best score is under a threshold tuned on 10 test questions, answer
   "That is not in the document" without calling the LLM.
4. Otherwise prompt: answer only from the excerpt, quote the supporting sentence,
   or reply exactly NOT_IN_DOCUMENT.
5. Check that the quoted sentence actually appears in the document (string match
   after normalizing whitespace). If not, return "not in the document".

Test set: 10 answerable and 10 unanswerable questions on one 3 to 5 page document
(for example a course syllabus or a datasheet). Report accuracy on each half and
the false-answer rate on the unanswerable half. Judges respect a refusal rate more
than a high answer rate.

### 1.5 The next 24 hours

Assume now is Wed evening (H0). Code due Thu end of day (about H24). Sleep is in
the plan: a tired demo loses more than a missing feature.

| Block | Hours | Task | Done when |
|---|---|---|---|
| H0 to H1 | 1 | HTTPS on the LAN with mkcert (section 6). Load the page on the actual demo phone, get camera and mic permission. | Phone shows a camera preview over https and plays a test WAV |
| H1 to H3.5 | 2.5 | Server (FastAPI or similar) with `/ask` taking photo + audio, keyword router, returns text + WAV. One big button UI. | Tap, speak "what does this sign say", hear an answer |
| H3.5 to H4.5 | 1 | Wire Cosmos image Q&A and faster-whisper. Log every request with timings to JSONL. | Timings visible per stage |
| H4.5 to H5.5 | 1 | Sound ID with AST: record 3 s, return top labels above a threshold. | Siren and horn test clips labeled |
| H5.5 to H6 | 0.5 | Freeze a working tag (zip the folder). | Copy exists |
| H6 to H12 | 6 | Sleep. | |
| H12 to H14 | 2 | Document Q&A with refusal (1.4). | 20-question test runs |
| H14 to H16 | 2 | Code gen + sandboxed run. Prompt like "write Python that converts 72 F to C and run it". Timeout 10 s, no network, temp dir. | 10 prompts run, pass rate recorded |
| H16 to H17 | 1 | Video Q&A from uploaded clip on the phone. | One clip answered |
| H17 to H19 | 2 | Test runner over all capabilities, writes `results/eval/*.csv` and a summary markdown table. | Every capability has a row with n, correct, median latency |
| H19 to H20 | 1 | Accessibility pass (section 5 checklist) with VoiceOver or TalkBack on the demo phone. | Full flow done eyes closed |
| H20 to H21.5 | 1.5 | Slides: problem, impact, architecture, results, named limits, safety. | 6 to 8 slides |
| H21.5 to H22.5 | 1 | Record the fallback video of the full demo script (section 2). Screen-record the phone too. | MP4 on laptop desktop and on a USB stick |
| H22.5 to H24 | 1.5 | Submit code. Freeze. Two full dry runs with a timer. | Submitted |
| Fri morning | 2 | Dry run at the venue if possible, check Wi-Fi isolation, warm models, charge everything. | Demo checklist ticked |

Cut order if behind: drop live video from the phone (show clip on laptop), then drop
code execution to "generate only" plus one pre-run example, then shrink doc Q&A
test set. Never cut the test tables or the fallback recording.

## 2. Five-minute live demo script

Setup before the slot: laptop on power, models warm (send one dummy request per
model), phone on full brightness with auto-lock off, Do Not Disturb on, phone and
laptop on our own hotspot or travel router (not venue Wi-Fi), fallback video open
and paused in a second window, printed props on the table: one street-style sign,
one slide with a plot, one short document page, phone speaker loud or a small
Bluetooth speaker paired.

| Time | Show | Say (short) | Fallback if it fails |
|---|---|---|---|
| 0:00 to 0:30 | Title + one impact number | "2.2 billion people have a vision impairment. Maya runs fully offline on this laptop. The phone is just a camera, mic, and speaker." Turn off the laptop Wi-Fi internet uplink visibly, or show airplane mode with the hotspot still up. | none needed |
| 0:30 to 1:15 | Image Q&A: point phone at printed sign, tap, ask "What does this sign say?" | Let it speak. "About one second on the GPU." | Retry once. If it fails again, play the 15 s segment of the fallback video. |
| 1:15 to 1:50 | Slide or plot: "What is the trend in this plot?" | "Same model, same button." | Skip to next item, mention it is in the results table. |
| 1:50 to 2:30 | Sound: play a siren or horn clip from a second device, tap "What do I hear?" | "Audio classifier, no internet." | Use a pre-recorded WAV upload in the UI. |
| 2:30 to 3:15 | Document Q&A: photo or preloaded PDF. Ask one answerable question, then one that is not in it. | "It tells you when the answer is not there instead of guessing." This is the strongest trust moment. | Preloaded PDF button in the UI. |
| 3:15 to 3:50 | Code: "Write and run Python that converts 72 Fahrenheit to Celsius." Hear the result. | "Generated and run in a sandbox, no network, 10 s timeout." | Show the logged result of the same prompt from the test run. |
| 3:50 to 4:30 | Video: recorded sidewalk clip on the laptop through the same pipeline, Maya speaks a description. | "We tested steering instructions and removed them: they said move right 65 of 85 times. Maya describes, it never decides." | Fallback video segment. |
| 4:30 to 5:00 | Results slide + named limits | "Every number here is from our own tests on this laptop." | none |

Rules for the live part:
- Script exact spoken questions and keep them short; whisper handles them better and
  the router keywords match.
- One retry maximum per segment, then move on. Judges score "works start to
  finish", so a smooth skip beats a long debug.
- Never type on the laptop during the demo. Every action happens on the phone, which
  is what the user would do.
- If the network fails entirely: run the same UI on the laptop at
  `https://localhost` (localhost is a secure context, so camera and mic still work,
  per [MDN getUserMedia](https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia))
  using the laptop webcam. Prepare and test this path on Thursday.

Pre-record (Thursday H21.5): a 4 to 5 minute screen recording that follows the same
script, with the phone screen and the audio. Cut it into the per-segment clips listed
above, so any one segment can be replaced without playing the whole thing.

## 3. Presenting test results honestly

Judges respect small, real, reproducible numbers over big claims. Use one table per
capability, same columns everywhere.

| Capability | Test set | n | Correct | Median latency | p90 or max | Peak VRAM | Notes |
|---|---|---|---|---|---|---|---|
| Image Q&A (Cosmos3-Edge NF4) | 3 real street frames + 7 synthetic | 10 | 5 | 1.2 s | fill in | 2.4 GiB | Misses tiny text, loops on busy signs |
| Image Q&A (Qwen3-VL-4B NF4) | same | 10 | 6 | 20 to 60 s | | fill in | Rejected for latency |
| Walk describe (video) | 4 sidewalk clips, 54.5 s total longest | 85 looks on clip 1 | hand-checked events, fill in | 0.64 s model, 1.18 s to speech | 2.10 s | 2.37 GiB | Misses curb, poles; wrong direction for crossing people |
| Steering instruct | same 4 clips | 85 + 17 + 10 + 8 | 0 of 6 hand-checked clearly right | 0.60 s | 1.05 s | 2.37 GiB | Removed from product |
| Speech to text | 20 spoken questions, 2 speakers | 20 | word error rate | | | | |
| Sound ID | 10 clips (siren, horn, beeps, speech, silence) | 10 | top-1 | | | | |
| Doc Q&A answerable | 10 questions | 10 | | | | | |
| Doc Q&A not in document | 10 questions | 10 | correct refusals | | | | Most important number |
| Code gen + run | 10 small tasks | 10 | ran and output correct | | | | |
| End to end tap to first audio | 10 phone requests over LAN | 10 | | | | | Includes upload |

How to frame it:
- Lead with the method: "hand-checked against frames", "same clips for every
  variant". Show `results/live/instruct_check.jpg` or the contact sheet once; a
  picture of the error convinces more than the number.
- Report latency as median plus max, and say what the clock measures (newest frame
  to speech start). This is already how D3 reports it.
- Show a rejected option next to the chosen one (Qwen3-VL vs Cosmos, instruct vs
  describe, memory vs no memory). It proves the choice was measured.
- Small n is fine if stated. Say "10 images, so one image is 10 points" before
  anyone asks.

### Named limits slide (say these before judges find them)

1. Distance is unreliable: called a far, crossing pickup "two steps ahead" (D3).
2. Motion direction is unreliable: "walking away" for people crossing sideways,
   "coming towards you" for a bus driving away (D3).
3. Misses low or thin obstacles: curb at a crosswalk, pole and trash can ahead,
   A-frame signs (D2, D3).
4. Small print and busy signs: 5/10 on our image set; looping on a busy sign.
5. No steering and no "safe to cross": removed after testing; a regex safety filter
   blocks phrases like "path is clear" (D3). The filter is a pattern list, so it can
   miss new phrasings.
6. One GPU, one user: the laptop serves one phone at a time.
7. Needs the laptop nearby on the same network; not a pocket device yet.
8. Crosswalk chirps may not map to an AudioSet class (fill in after testing).

Next steps slide: detector + tracker in front of the VLM for distance and direction
(Prompt 1), tracks as structured state instead of text memory (D4), a phone-only
build when small VLMs get faster.

## 4. Judge Q&A cheat sheet

| Question | Short answer |
|---|---|
| Is it safe? Could it get someone hurt? | Maya describes, it never decides. We tested steering instructions and they were wrong 4 of 6 times on hand checks, so we removed them. It never says "safe to cross"; a filter blocks that kind of phrase. It is a complement to a cane, guide dog, and orientation and mobility training, not a replacement. |
| What is the latency? | Video looks take about 0.5 to 0.6 s of model time; speech starts about 1 s after the newest frame (median, D3). Image questions about 1.2 s. End to end over Wi-Fi: quote the measured number from the test table. |
| Why these models? | Cosmos3-Edge handles video natively and fits in 2.4 GiB at 4-bit. Qwen3-VL read one more test image of 10 but took 20 to 60 s, which is unusable. Whisper and AST are small, well known, and run on CPU or GPU. Piper speaks in under 0.35 s on CPU. All open weights. |
| Why not just use Seeing AI or Be My Eyes? | They are excellent and our users should keep them. But scene description in Seeing AI needs internet ([Wikipedia summary](https://en.wikipedia.org/wiki/Seeing_AI); Microsoft's own page does not say which features work offline, UNVERIFIED). Envision lists Describe Scene and Ask Envision as internet only ([Envision support](https://support.letsenvision.com/hc/en-us/articles/7947948935441), page blocked automated fetch, title confirmed via search). Be My Eyes volunteers need a live call. Maya runs where there is no signal or where photos must not leave the room: labs, exams, company sites. And it adds code and document Q&A for students and engineers. |
| Privacy? | No cloud calls at runtime. Camera frames, audio, and documents stay on the laptop; we keep only timing logs for testing, and can turn those off. |
| Why a laptop and a phone, not just a phone? | Current open VLMs need a GPU to answer in about a second. The phone is the sensor and speaker; the laptop is the brain. A student already carries both. |
| How did you test? | Same clips and images for every variant, hand-checked against frames, latency logged per stage. Tables on the results slide; raw outputs in `results/`. |
| What fails? | The named limits slide: distance, motion direction, thin obstacles, small print. Each with the clip where it failed. |
| How does it know a document does not contain the answer? | Retrieval score threshold plus a required quote that must match the text. If either fails, it says "not in the document". Measured on 10 unanswerable questions. |
| Is running generated code dangerous? | Runs in a subprocess (or container) with no network, a temp folder, and a 10 s timeout. It is for small calculations and plots, not system access. |
| What about hallucination in descriptions? | Short answers (24 token cap) reduce it; no text memory because the model copied itself (D4). Next step is detector and depth facts in the prompt. |
| Does it work with VoiceOver / TalkBack? | Yes, tested on the demo phone (only claim it once section 5 is done). One large button, live region announces answers. |
| What would you build next? | Detector + tracker for distance and direction (permissive license models), then evaluate warning lead time on labeled clips. |
| Cost? | Runs on a consumer laptop GPU (RTX 5060 Laptop, 8 GB). No subscription. |
| Why not a smaller model on the phone? | In the hackathon window the laptop GPU gave about 1 s answers. Phone-only is the roadmap. Do not claim phone numbers we did not measure. |

## 5. Accessibility must-haves for the web UI

The target user may be using a screen reader, a magnifier, or no screen at all.

Layout and controls
- One primary control: a single "Ask Maya" button filling most of the screen. WCAG
  2.2 SC 2.5.8 requires targets of at least 24 by 24 CSS px (AA) and SC 2.5.5 asks
  for 44 by 44 (AAA) ([WCAG 2.2](https://www.w3.org/TR/WCAG22/)). Go well past both:
  primary button at least 50% of the viewport, secondary buttons at least 64 px tall.
- Use a real `<button>` element with a text label ("Ask Maya, hold to speak" or
  "Tap to ask"). Satisfies SC 4.1.2 Name, Role, Value.
- Mode buttons (Read, Sounds, Document, Code, Video) as large, labeled buttons, not
  icons alone. Keep them in a fixed order so a screen reader user learns positions.
- No time limits on any interaction (SC 2.2.1).
- Works in portrait and landscape; text resizes to 200% without loss (SC 1.4.4).

Feedback
- Speak every answer (Piper WAV) and also put the text in an `aria-live="polite"`
  region (`role="status"`), so VoiceOver and TalkBack read it without moving focus
  (SC 4.1.3 Status Messages). Use `assertive` only for errors.
- Announce state changes: "Listening", "Thinking", "Answer ready". Pair with a short
  earcon and a vibration (`navigator.vibrate`, Android only; iOS Safari does not
  support it, UNVERIFIED for the current iOS version).
- If a screen reader is on, avoid double speech: offer a setting "Speak answers
  with Maya voice / let my screen reader read them". Default to Maya voice, since
  the live region text will also be read; test both on the demo phone.
- Errors in plain words with the fix: "I can't reach the laptop. Check that both
  are on the same Wi-Fi."

Visual
- Contrast at least 4.5:1 for text and 3:1 for button boundaries and focus rings
  (SC 1.4.3, 1.4.11). Use white on near-black or black on yellow; large type (at
  least 24 px base).
- Visible focus indicator, never hidden behind a sticky bar (SC 2.4.11).
- Support `prefers-color-scheme` and `prefers-reduced-motion`.

Voice-only use
- After the first tap, allow "hold to talk, release to send" so one gesture does the
  whole cycle.
- Do not rely on the browser Web Speech recognition API: it is not offline on every
  browser (UNVERIFIED per browser) and breaks the "no cloud" rule. Record with
  MediaRecorder and transcribe with faster-whisper on the laptop.

iOS Safari and Android Chrome specifics
- Camera and mic need a secure context (HTTPS or localhost); on plain http
  `navigator.mediaDevices` is undefined
  ([MDN](https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia)).
- Audio playback and speech synthesis on iOS need a user gesture. Start playback
  from the tap handler, or "unlock" an `<audio>` element on the first tap and reuse
  it ([WebKit bug 218815](https://bugs.webkit.org/show_bug.cgi?id=218815) and
  community reports; behavior should be checked on the demo phone).
- WebKit bug 218815 reports that `speechSynthesis.speak` can mute an active
  getUserMedia audio track on iOS. Another reason to play server-generated WAV
  through an `<audio>` element instead of browser TTS, and to stop the mic track
  before playback. Fix status UNVERIFIED.
- Use `<input type="file" accept="image/*" capture="environment">` as a fallback
  for photos; it opens the native camera, which VoiceOver users already know.
- Set `playsinline` on the preview `<video>` so iOS does not go fullscreen.

Test protocol (30 minutes): turn on VoiceOver (iOS) or TalkBack (Android), close
your eyes, and complete: open page, ask about a sign, hear answer, switch to
Document, ask an unanswerable question, hear the refusal. Note every place you got
stuck and fix it.

## 6. Phone to laptop HTTPS on a LAN

Why: browsers expose camera and mic only to secure contexts (HTTPS, localhost)
([MDN](https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia)).
A phone hitting `http://192.168.x.x` gets no camera.

Network
- Do not trust venue Wi-Fi: many event networks isolate clients so devices cannot
  reach each other (common practice, UNVERIFIED for the Roux venue). Use the Windows
  Mobile Hotspot on the laptop, or a travel router, and join the phone to it. Give
  the laptop a fixed IP on that network, or note it and generate the cert for it.
- Allow the server port through Windows Defender Firewall for private networks.
  (The user does this; this plan does not change system settings.)

Option A: mkcert (recommended, about 15 minutes)
1. Install mkcert on the laptop and run `mkcert -install` to create a local CA
   ([mkcert README](https://github.com/FiloSottile/mkcert)).
2. Create a cert for every name the phone will use:
   `mkcert 192.168.137.1 localhost 127.0.0.1` (192.168.137.1 is the usual Windows
   hotspot address, UNVERIFIED on this laptop; check with `ipconfig`).
3. Start the server with the generated cert and key (for uvicorn:
   `--ssl-certfile` and `--ssl-keyfile`).
4. Find the CA file: `mkcert -CAROOT` prints the folder; copy only `rootCA.pem`.
   Never copy `rootCA-key.pem`: the README warns it "gives complete power to
   intercept secure requests from your machine".
5. iOS: send `rootCA.pem` to the phone (AirDrop or email, per the mkcert README),
   open it, install it under Settings, Profile Downloaded, then go to Settings,
   General, About, Certificate Trust Settings and turn on full trust for it
   ([Apple support 102390](https://support.apple.com/en-us/102390)). Without the
   second step Safari still rejects the cert.
6. Android: Settings, Security, Encryption and credentials, Install a certificate,
   CA certificate, pick `rootCA.pem`, accept the warning (menu names vary by vendor;
   path from [HTTP Toolkit on Android 11](https://httptoolkit.com/blog/android-11-trust-ca-certificates/)
   and [MIT KB](https://kb.mit.edu/confluence/display/istcontrib/Installing+Certificates+on+Android)).
   Chrome on Android trusts user-installed CAs for websites (MIT KB; UNVERIFIED for
   the newest Chrome). Apps do not, which does not matter here.
7. Open `https://192.168.137.1:8443` on the phone, allow camera and microphone when
   asked. Permission prompts must be answered at least once per origin (MDN), so do
   this before the demo, not during it.
8. After the hackathon: remove the profile from the phone and run
   `mkcert -uninstall` on the laptop.

Option B: Android over USB, no certificate
- `adb reverse tcp:8443 tcp:8443` maps the phone's localhost to the laptop, and
  localhost is a secure context, so plain `http://localhost:8443` gets camera and
  mic. Needs adb and USB debugging; no Wi-Fi involved. Good backup for an Android
  demo phone.

Option C: Android Chrome flag (dev only)
- `chrome://flags/#unsafely-treat-insecure-origin-as-secure` with
  `http://192.168.137.1:8443` lets Chrome treat that origin as secure (UNVERIFIED
  for the current Chrome version). No iOS equivalent.

Option D: laptop only
- Open `https://localhost:8443` in the laptop browser and use the webcam. Keeps the
  demo alive if the phone path dies.

Pre-demo check: phone shows the padlock, camera preview runs, a test WAV plays, a
round trip `/ask` returns in the expected time.

## 7. Impact slide

Headline: "Millions read the world with a camera app. Those apps go quiet when the
signal does."

Numbers (pick 3 for the slide):

| Number | Source |
|---|---|
| At least 2.2 billion people have a near or distance vision impairment; at least 1 billion of those could have been prevented or are not yet addressed | [WHO fact sheet, 10 Feb 2026](https://www.who.int/news-room/fact-sheets/detail/blindness-and-visual-impairment) |
| 43 million people blind and 295 million with moderate to severe vision impairment in 2020; blindness projected to 61 million by 2050 | [IAPB Vision Atlas, Magnitude of Vision Loss](https://www.iapb.org/wp-content/uploads/2021/02/Vision-Atlas_Evidence-Series_Magnitude-of-VIsion-Loss_24022021.pdf) (figures via search summary of IAPB and [Orbis](https://www.orbis.org/en/news/2021/new-global-blindness-data); confirm against the PDF before the slide) |
| United States, 2024: about 7.15 million people with vision loss that glasses cannot fix (best corrected), including about 0.71 million blind | [CDC VEHSS modeled estimates](https://www.cdc.gov/vision-health-data/prevalence-estimates/vision-loss-prevalence.html) |
| US visual impairment and blindness projected to double to more than 8 million by 2050 | [NEI news release, 2016 study](https://www.nei.nih.gov/about/news-and-events/news/visual-impairment-blindness-cases-us-expected-double-2050) |
| Be My Eyes: about 11.5 million volunteers and 1.1 million blind and low-vision users (live counter, read Nov 2026) | [Be My Eyes about page](https://www.bemyeyes.com/about) |

Prior art and the gap Maya fills:

| Tool | What it does | Limit relevant to Maya | Source |
|---|---|---|---|
| Seeing AI (Microsoft, 2017) | Short text, documents, products, scene description | Scene description and handwriting need internet | [Wikipedia](https://en.wikipedia.org/wiki/Seeing_AI); [seeingai.com](https://www.seeingai.com/) does not state offline scope (UNVERIFIED per feature) |
| Be My Eyes / Be My AI | Live volunteer video calls; AI image description | Needs a connection and, for calls, a human; Be My AI is GPT-4 based (widely reported, UNVERIFIED: OpenAI page blocked automated fetch) | [bemyeyes.com/about](https://www.bemyeyes.com/about) |
| Envision app / glasses | Text reading, scene description, Ask Envision | Describe Scene, Ask Envision, and calls need internet; Android app needs data even for offline features | [Envision support](https://support.letsenvision.com/hc/en-us/articles/7947948935441) and [FAQ](https://support.letsenvision.com/hc/en-us/articles/13539683947153-Do-I-need-an-Internet-connection-or-mobile-data-to-use-all-the-features-of-the-Envision-App) (content via search snippets) |
| Google Lookout (Android) | 7 modes: Text, Explore (beta), Food labels, Documents, Currency, Images with AI Q&A, Find | Android only; Images Q&A in English only; Help page does not say which modes work offline | [Google Help](https://support.google.com/accessibility/android/answer/9031274?hl=en) |
| OKO (AYES) | Reads pedestrian signals with the camera, audio and haptic walk cues | Crosswalk signals only; on-device claim from press interviews, not docs (UNVERIFIED) | [Innovation Origins](https://innovationorigins.com/en/free-ticker-app-oko-from-ayes-allows-the-blind-and-visually-impaired-to-cross-roads-safely-again) |
| NaviLens | Reads special printed codes from up to 100 ft | Works only where codes are installed | [navilens.com](https://www.navilens.com/en/) |

What Maya adds (one line each on the slide):
- Fully offline and private: nothing leaves the laptop.
- Built for students and engineers: slides, plots, documents with "not in the
  document" answers, and code that runs.
- Multimodal in one button: image, video, speech, sounds.
- Honest by design: describes, never decides; limits measured and published.

Avoid on the slide: any claim that Maya is safer than a cane or guide dog, any
pedestrian safety statistic we did not source, and any accuracy number we did not
measure.

## 8. Unverified items to check before Friday

- Which Seeing AI channels work offline (test in airplane mode or read the user manual).
- Be My AI model name (OpenAI customer story blocked to automated fetch).
- Envision pages were read through search snippets, not fetched directly (403).
- IAPB 43 million and 295 million: open the PDF and confirm.
- faster-whisper, AST, and coder model VRAM on this GPU: measure.
- Whether AST labels crosswalk chirps usefully.
- iOS speechSynthesis and getUserMedia mute bug status on the demo phone's iOS version.
- Windows hotspot IP and firewall rule on the demo laptop.
- Chrome insecure-origin flag behavior on the current Android Chrome.
