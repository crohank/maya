# Research prompts for Claude chat

Each prompt is self-contained. Paste one per chat and turn on web search / research
mode. Ask for sources on every claim. Paste the answers back here and I will
fold them into `docs/decisions.md` and the build plan.

---

## Prompt 1: Distance, motion, and obstacle perception for a blind walker (highest priority)

```
I am building "Maya", an offline assistant for people with low vision, for a
hackathon (code due Nov 19 2026, live demo Nov 20). Rules: open-weight models only,
all inference local, no cloud APIs at runtime.

Hardware: laptop with RTX 5060 Laptop GPU (Blackwell, sm_120, 8 GB VRAM, about
5 GB free after the desktop), Ryzen 9 8940HX, 31 GB RAM, Windows 11 with Docker on
WSL2, PyTorch 2.9 + CUDA 12.8. The phone browser streams camera video to the laptop.

What I measured so far: a 4B video VLM (nvidia/Cosmos3-Edge, NF4 4-bit) answers
"what is the nearest obstacle and where" on a 2 s clip in about 0.5 s, so latency is
fine. But on 4 sidewalk test clips it is weak at exactly what a walker needs:
- nearest obstacle (missed a pole + trash can directly ahead, a curb at a
  crosswalk, sandwich-board signs close on the left)
- direction of motion (said "walking away" for people crossing sideways, "coming
  toward you" for a bus driving away)
- distance ("two steps ahead" for a truck far away)
- when asked to steer ("move left / move right + reason") it said "move right"
  65 of 85 times regardless of scene, and steered into people, a fence, the road.
- Adding its own previous answers to the prompt made it copy itself.

I want a fast perception layer in front of the VLM. Research and recommend:
1. Object detectors that run under about 20 ms per frame on an 8 GB laptop GPU and
   have permissive licenses (Apache-2.0 / MIT, avoid AGPL like Ultralytics YOLO):
   e.g. RT-DETR / RT-DETRv2 / D-FINE / YOLOX / RTMDet. Give exact Hugging Face or
   GitHub IDs, license, COCO mAP, measured speed, and which classes matter for
   sidewalks (person, bicycle, car, bus, truck, pole, bench, fire hydrant, stop sign).
   Which detect poles, trash cans, curbs, stairs, sandwich boards? Any open
   datasets or models for sidewalk obstacles and curbs specifically?
2. Monocular depth models (Depth Anything V2 Small/Base/Large, Depth Anything V2
   Metric, Depth Pro, Metric3D v2, UniDepth, Video Depth Anything): exact IDs,
   license per size (I believe only V2 Small is Apache-2.0, check), metric vs
   relative depth, speed at 518 px on a laptop GPU, accuracy outdoors at 1 to 10 m.
3. Multi-object trackers (ByteTrack, OC-SORT, BoT-SORT, Norfair): license, how to
   get direction of motion (approaching / receding / crossing) and time-to-contact
   from box size growth + depth change. Formulas and pitfalls when the camera
   itself is walking (ego-motion).
4. How to turn tracks into a short spoken warning ("Person near, ahead left,
   approaching") with low false alarms: thresholds, hysteresis, how often to speak.
   Cite prior assistive navigation work (research papers 2022 to 2026 on vision
   assistance for blind and low-vision pedestrians, apps like Seeing AI, Be My Eyes,
   Envision, Lookout, NaviLens, OKO for crosswalks) and what users actually want
   to hear (frequency, wording, directional vs descriptive cues).
5. How to fuse tracker state into the VLM prompt so the VLM adds context (signs,
   curb, crosswalk) without copying itself. Any papers on "structured scene state
   + VLM" for navigation.
6. An evaluation protocol I can run in a few hours: label key events on short
   sidewalk clips, measure hit rate and warning lead time. Any public egocentric
   sidewalk / blind navigation video datasets with labels (e.g. for obstacle or
   curb detection) that are freely downloadable.

Output: a ranked recommendation for a stack that fits 8 GB alongside a 2.4 GB VLM,
with exact model IDs, licenses, expected latency, and a one-day build plan.
Flag anything you could not verify.
```

---

## Prompt 2: Image reading (OCR) model and the Qwen3-VL slowness

```
I am building an offline low-vision assistant (open-weight models only, local
inference) on an RTX 5060 Laptop GPU (Blackwell sm_120, 8 GB VRAM, about 5 GB
free), PyTorch 2.9.0 + CUDA 12.8 + cuDNN 9, transformers 5.23, bitsandbytes 0.50,
Docker on WSL2.

Task: read signs, labels, bus numbers, whiteboards, slides, plots from a phone
photo, and answer questions about them.

Measured on 10 test images (3 real street frames, 7 synthetic):
- nvidia/Cosmos3-Edge NF4: 5/10, median 1.2 s, 2.4 GiB peak. Failures: missed a
  tiny sign, misread small print, looped repeating lines on a busy sign.
- Qwen/Qwen3-VL-4B-Instruct, BF16 weights quantized on load to NF4 with
  bitsandbytes (vision tower and lm_head kept BF16): 6/10 but 20 to 60 s per image.
  Text-only decode is 15 tok/s. Generating 1 token after a 640x360 image takes
  15 s, and the vision tower alone takes 14.7 s. Everything is on cuda:0, sdpa.

Questions:
1. Is there a known slowdown for Qwen2.5-VL / Qwen3-VL vision encoders on
   PyTorch 2.9 / cuDNN 9.x / Blackwell, e.g. Conv3d patch embedding in bf16, or
   the vision attention path? What is the fix (disable cuDNN for conv3d, replace
   Conv3d with Linear, a specific torch/cuDNN version, flash-attn / sdpa settings)?
   Cite GitHub issues.
2. Fastest way to run Qwen3-VL-4B or 8B on an 8 GB Blackwell laptop GPU: vLLM
   (AWQ / FP8 official checkpoints, does vLLM support sm_120 in a Docker image?),
   llama.cpp with Qwen3-VL GGUF + mmproj (which repos, which quant, measured
   speed), SGLang, LMDeploy. Which official quantized Qwen3-VL checkpoints exist
   (FP8, AWQ), and their licenses?
3. Alternatives that read text well and fit under 4 GB: e.g. Florence-2, PaddleOCR
   (PP-OCRv5), Surya OCR, GOT-OCR2, InternVL3.5-2B/4B, SmolVLM2, Moondream, Gemma
   3n, MiniCPM-V 4.x, olmOCR. For each: exact ID, license, OCR benchmark scores
   (OCRBench, TextVQA, DocVQA), speed, and whether a "dedicated OCR model + small
   LLM" pipeline beats one VLM for street signs.
4. Practical tricks for small text in a phone photo: tiling / zoom crops,
   resolution limits (max_pixels) per model, text detection first then crop.

Output: a recommendation for the image path (model + runtime + settings) with
expected accuracy and latency on my GPU, plus the most likely fix for the
Qwen3-VL slowness. Flag anything you could not verify.
```

---

## Prompt 3: Hackathon demo, evaluation, and judging plan

```
I am in the IEEE AI Hackathon, Multimodal LLM Challenge (Roux Institute, Portland
ME). Code due Thursday Nov 19 2026 end of day, live demo Friday Nov 20 1 PM.
Rules: open-weight models only, local inference, no cloud APIs in the running
system. Judging: multimodal checklist + our own test results 30%, live demo works
start to finish in an easy app 25%, architecture (model choices, named limits,
runs well locally) 20%, impact 15%, judges' Q&A 10%. Bonus for web + mobile.

Product: "Maya", an offline assistant for students and engineers with low vision.
Phone browser captures camera/mic/photos, a laptop (RTX 5060 8 GB) runs all models.
Tap to ask, voice in, voice out. Safety rule: Maya describes, never decides (never
"safe to cross").

Required capabilities: image Q&A (signs, slides, plots), audio (transcribe speech,
identify sounds like sirens, horns, crosswalk chirps), document Q&A with "not in the
document" answers, code generation + execution, short video Q&A.

Planned models: Cosmos3-Edge (video), Qwen3-VL (images), faster-whisper (speech),
AST AudioSet classifier (sounds), Qwen2.5-Coder 7B (code), Piper TTS. Router is
keyword rules, no LLM.

Measured: walking-video latency about 1 s from frame to speech, but distance and
motion-direction errors, and steering instructions were unreliable (we dropped them).

Help me with:
1. With about 24 hours left and one developer plus an AI coding agent, what is the
   minimum build that scores well? Rank features by points per hour.
2. A 5-minute live demo script that cannot fail: what to show, in what order, what
   to pre-record as a fallback, how to handle the phone-to-laptop HTTPS setup.
3. How to present test results honestly and convincingly (tables, what metrics
   judges respect, how to show failures as "named limits").
4. Likely judge questions on safety, latency, model choice, privacy, and why not
   just use a phone app like Seeing AI or Be My Eyes; strong short answers.
5. Accessibility must-haves for the web UI (screen reader, voice-only use, large
   targets, contrast) so the app itself is usable by the target user.
6. Prior art and impact numbers (low-vision population, current tools, their
   limits like needing internet) with sources, for a one-slide impact pitch.

Output: a prioritized checklist and timeline for the next 24 hours, the demo
script, and a Q&A cheat sheet. Flag anything you could not verify.
```
