"""Simulated live run of Cosmos3-Edge + Piper TTS over a walking video.

The video clock keeps running while the model and TTS compute, so each query
only sees frames up to "now" and its speech starts late by the real compute
time. Output per mode in results/live/<video>_<mode>/:
  annotated.mp4   original video + captions + TTS audio at the real speak time
  log.csv         one row per query: window, latencies, lag, answer
  summary.md      latency/lag stats and the transcript

Run inside the cosmos-tf container:
  python scripts/live_harness.py --video test_videos/clip.mp4 --modes describe,guide
"""
import argparse
import csv
import os
import re
import statistics
import subprocess
import tempfile
import time
import wave
from pathlib import Path

import torch
from huggingface_hub import hf_hub_download
from transformers import AutoModelForImageTextToText, AutoProcessor

MODEL_ID = os.environ.get("COSMOS_MODEL", "ubr-physical-ai/Cosmos3-Edge-NF4-bnb")
PROCESSOR_ID = os.environ.get("COSMOS_PROCESSOR", MODEL_ID)
VOICE = "en/en_US/lessac/medium/en_US-lessac-medium.onnx"

SYSTEM = (
    "You are the eyes of a blind pedestrian. The video is from a camera on their "
    "chest, facing where they walk. Say where things are (left, right, ahead) "
    "and how many steps away. Answer in one short sentence. Never say it is "
    "safe to cross or go, and never make crossing decisions."
)
PROMPTS = {
    "describe": (
        "Name the nearest person, vehicle, or obstacle in my path and where it is, "
        "in under 10 words. Example answers: 'Person walking toward you, slightly "
        "left.' 'Bus passing on your right.' 'Pole two steps ahead.'"
    ),
    # Experimental: steering cues. Evaluated, not shipped (see docs/decisions.md D2).
    "instruct": (
        "I am walking on this sidewalk. Tell me how to avoid the nearest person or "
        "obstacle in my path. Reply in under 12 words as: action, reason. Action is "
        "one of: move left, move right, keep straight, slow down. Examples: "
        "'Move right, person walking toward you on your left.' "
        "'Keep straight, path ahead is clear of people.' "
        "'Slow down, group of people stopped ahead.'"
    ),
    "guide": (
        "I am walking on this sidewalk. Name the nearest person or obstacle in my "
        "path and where it is, and say which side has open space. Example: "
        "'Person two steps ahead, open space on your left.'"
    ),
}

UNSAFE = re.compile(
    r"\b(safe to (cross|go|walk)|you can (cross|go)|go ahead|it'?s (clear|safe)|"
    r"cross now|start crossing|(path|way|road|street|coast)( ahead)? is clear)\b",
    re.I,
)
SAFE_SUFFIX = "I can describe what I see, but I can't tell you when it's safe."


def safety_filter(text):
    """Drop sentences that imply a go/cross decision; append the fixed disclaimer."""
    if not UNSAFE.search(text):
        return text, False
    kept = [s for s in re.split(r"(?<=[.!?])\s+", text) if not UNSAFE.search(s)]
    return " ".join(kept + [SAFE_SUFFIX]).strip(), True


def first_sentences(text, n):
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return " ".join(parts[:n])


def ffprobe_duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
        capture_output=True, text=True, check=True,
    )
    return float(out.stdout.strip())


def has_audio(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index",
         "-of", "csv=p=0", path],
        capture_output=True, text=True,
    )
    return bool(out.stdout.strip())


def cut_window(src, start, end, dst, fps, width):
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{start:.2f}", "-i", src,
         # Bound the long side, so portrait phone video costs the same tokens as
         # landscape (448 wide portrait was 1,598 tokens vs 646 landscape).
         "-t", f"{end - start:.2f}", "-vf",
         f"fps={fps},scale={width}:{width}:force_original_aspect_ratio=decrease:force_divisible_by=2",
         "-an",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", dst],
        check=True,
    )


class Tts:
    def __init__(self):
        from piper import PiperVoice
        path = hf_hub_download("rhasspy/piper-voices", VOICE)
        hf_hub_download("rhasspy/piper-voices", VOICE + ".json")
        self.voice = PiperVoice.load(path)

    def say(self, text, path):
        with wave.open(path, "wb") as w:
            self.voice.synthesize_wav(text, w)
        with wave.open(path) as w:
            return w.getnframes() / w.getframerate()


def ask(model, proc, clip, question, max_new_tokens):
    messages = [
        {"role": "system", "content": [{"type": "text", "text": SYSTEM}]},
        {"role": "user", "content": [
            {"type": "video", "path": clip},
            {"type": "text", "text": question},
        ]},
    ]
    inputs = proc.apply_chat_template(
        messages, add_generation_prompt=True, tokenize=True, return_dict=True,
        return_tensors="pt", enable_thinking=False,
    ).to(model.device)
    with torch.inference_mode():
        out = model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False)
    text = proc.decode(out[0][inputs["input_ids"].shape[-1]:], skip_special_tokens=True)
    return text.strip(), inputs["input_ids"].shape[-1]


def srt_time(t):
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def render(src, dur, events, out_mp4, work):
    srt = Path(work) / "captions.srt"
    with open(srt, "w") as f:
        for i, e in enumerate(events):
            end = e["audio_start"] + e["audio_dur"] + 1.0
            if i + 1 < len(events):
                end = min(end, events[i + 1]["audio_start"])
            end = min(end, dur)
            if end <= e["audio_start"]:
                continue
            f.write(f"{i + 1}\n{srt_time(e['audio_start'])} --> {srt_time(end)}\n")
            f.write(f"[saw {e['win_start']:.1f}-{e['win_end']:.1f}s, newest frame {e['lag']:.1f}s old]\n")
            f.write(f"{e['answer']}\n\n")

    spoken = [e for e in events if e["audio_start"] < dur]
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", src]
    for e in spoken:
        cmd += ["-i", e["wav"]]
    parts, labels = [], []
    for i, e in enumerate(spoken):
        ms = int(e["audio_start"] * 1000)
        parts.append(f"[{i + 1}:a]adelay={ms}:all=1[a{i}]")
        labels.append(f"[a{i}]")
    if has_audio(src):
        parts.append("[0:a]volume=0.2[bg]")
        labels.append("[bg]")
    parts.append(f"{''.join(labels)}amix=inputs={len(labels)}:normalize=0:duration=longest[aout]")
    parts.append(
        f"[0:v]subtitles={srt}:force_style='FontSize=16,Outline=2,MarginV=20'[vout]"
    )
    cmd += ["-filter_complex", ";".join(parts), "-map", "[vout]", "-map", "[aout]",
            "-t", f"{dur:.2f}", "-c:v", "libx264", "-preset", "veryfast", "-c:a", "aac", out_mp4]
    subprocess.run(cmd, check=True)


def run_mode(model, proc, tts, args, mode, dur, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    wav_dir = out_dir / "wav"
    wav_dir.mkdir(exist_ok=True)
    events = []
    with tempfile.TemporaryDirectory() as td:
        # Vision loop: the GPU never waits for speech. Each look starts the moment
        # the previous one returns, so a fresh answer is always close at hand.
        t_video = args.window
        while t_video < dur:
            ws = max(0.0, t_video - args.window)
            clip = f"{td}/win.mp4"
            cut_window(args.video, ws, t_video, clip, args.fps, args.width)
            t0 = time.perf_counter()
            question = PROMPTS[mode]
            if args.memory and events:
                past = "; ".join(
                    f"{t_video - e['win_end']:.1f}s ago: '{e['answer']}'"
                    for e in events[-args.memory:]
                )
                question += (
                    f" Your earlier answers ({past}). If the same thing is still in "
                    "view, say whether it is now closer, farther, or moving across."
                )
            raw, n_in = ask(model, proc, clip, question, args.max_new_tokens)
            model_s = time.perf_counter() - t0
            answer, flagged = safety_filter(first_sentences(raw, args.sentences))
            events.append(dict(
                idx=len(events), win_start=ws, win_end=t_video, input_tokens=n_in,
                model_s=model_s, ready=t_video + model_s, flagged=flagged, raw=raw,
                answer=answer, status="", tts_s=0.0, audio_start=None, audio_dur=0.0,
                lag=None, age=None, wav="",
            ))
            t_video += max(model_s, args.min_interval)

        # Speaker: when free, say only the newest finished answer; older ones are
        # stale and dropped. Identical consecutive answers stay silent.
        t_free, last_idx, last_spoken = 0.0, -1, ""
        while True:
            pending = [e for e in events if e["idx"] > last_idx]
            if not pending:
                break
            ready_now = [e for e in pending if e["ready"] <= t_free]
            e = ready_now[-1] if ready_now else pending[0]
            for older in pending:
                if older["idx"] < e["idx"]:
                    older["status"] = "stale"
            last_idx = e["idx"]
            if e["answer"].lower() == last_spoken.lower():
                e["status"] = "repeat"
                continue
            e["wav"] = str(wav_dir / f"{e['idx']:03d}.wav")
            t1 = time.perf_counter()
            e["audio_dur"] = tts.say(e["answer"], e["wav"])
            e["tts_s"] = time.perf_counter() - t1
            e["audio_start"] = max(t_free, e["ready"]) + e["tts_s"]
            e["lag"] = e["audio_start"] - e["win_end"]
            e["age"] = e["audio_start"] - e["win_start"]
            e["status"] = "spoken"
            t_free = e["audio_start"] + e["audio_dur"]
            last_spoken = e["answer"]

        for e in events:
            said = (f"speaks at {e['audio_start']:5.1f}s (newest frame {e['lag']:.1f}s old, "
                    f"oldest {e['age']:.1f}s old)  {e['answer']}") if e["status"] == "spoken" \
                else f"({e['status']})  {e['answer']}"
            print(f"[{mode}] saw {e['win_start']:5.1f}-{e['win_end']:5.1f}s  "
                  f"{e['input_tokens']:5d} tok  model {e['model_s']:4.2f}s  {said}", flush=True)

        spoken = [e for e in events if e["status"] == "spoken"]
        render(args.video, dur, spoken, str(out_dir / "annotated.mp4"), td)

    with open(out_dir / "log.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[k for k in events[0] if k != "wav"])
        w.writeheader()
        for e in events:
            w.writerow({k: (round(v, 3) if isinstance(v, float) else v) for k, v in e.items() if k != "wav"})

    def stat(key, rows):
        vals = [e[key] for e in rows]
        return f"median {statistics.median(vals):.2f}s, max {max(vals):.2f}s"

    count = {s: sum(e["status"] == s for e in events) for s in ("spoken", "stale", "repeat")}
    with open(out_dir / "summary.md", "w") as f:
        f.write(f"# Live harness: {Path(args.video).name}, mode `{mode}`\n\n")
        f.write(f"Window {args.window}s at {args.fps} fps, width {args.width}px. "
                f"{len(events)} looks over {dur:.1f}s of video: {count['spoken']} spoken, "
                f"{count['stale']} dropped as stale, {count['repeat']} silent repeats.\n\n")
        f.write(f"- Model time per look: {stat('model_s', events)}\n")
        f.write(f"- TTS time: {stat('tts_s', spoken)}\n")
        f.write(f"- Speech start minus newest frame seen: {stat('lag', spoken)}\n")
        f.write(f"- Speech start minus oldest frame seen: {stat('age', spoken)}\n")
        f.write(f"- Answers rewritten by safety filter: {sum(e['flagged'] for e in events)}\n\n")
        f.write("| # | Saw (s) | Spoken at (s) | Newest frame age (s) | Answer |\n|---|---|---|---|---|\n")
        for e in spoken:
            f.write(f"| {e['idx']} | {e['win_start']:.1f}-{e['win_end']:.1f} | {e['audio_start']:.1f} | "
                    f"{e['lag']:.1f} | {e['answer']} |\n")
    print(f"[{mode}] wrote {out_dir}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--modes", default="instruct,describe")
    ap.add_argument("--window", type=float, default=2.0, help="seconds of history per query")
    ap.add_argument("--fps", type=float, default=4.0)
    ap.add_argument("--width", type=int, default=448)
    ap.add_argument("--min-interval", type=float, default=0.0, help="min seconds between queries")
    ap.add_argument("--sentences", type=int, default=1)
    ap.add_argument("--max-new-tokens", type=int, default=24)
    ap.add_argument("--memory", type=int, default=0,
                    help="previous answers (with age) added to each prompt")
    ap.add_argument("--out", default="results/live")
    args = ap.parse_args()

    dur = ffprobe_duration(args.video)
    t = time.perf_counter()
    proc = AutoProcessor.from_pretrained(PROCESSOR_ID)
    model = AutoModelForImageTextToText.from_pretrained(MODEL_ID, device_map="cuda").eval()
    tts = Tts()
    print(f"Loaded model + TTS in {time.perf_counter() - t:.1f}s; video {dur:.1f}s")

    # One warm-up call so CUDA kernel compile time does not land on the first live answer.
    with tempfile.TemporaryDirectory() as td:
        cut_window(args.video, 0, min(args.window, dur), f"{td}/w.mp4", args.fps, args.width)
        ask(model, proc, f"{td}/w.mp4", "What do you see?", 8)

    for mode in args.modes.split(","):
        run_mode(model, proc, tts, args, mode, dur,
                 Path(args.out) / f"{Path(args.video).stem}_{mode}"
                 f"{f'_mem{args.memory}' if args.memory else ''}")
    print(f"Peak VRAM {torch.cuda.max_memory_allocated() / 2**30:.2f} GiB")


if __name__ == "__main__":
    main()
