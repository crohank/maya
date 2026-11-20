"""Simulated live walk: walk v3 triggers decide when Cosmos is asked for a move; otherwise it describes.

One Cosmos worker (one GPU) and one voice. A clock runs on measured Cosmos times:
- the worker is free -> if a trigger is waiting, ask MOVE about the newest one, else ask DESCRIBE
  if the voice will be free (no queueing behind speech, docs/decisions.md D8);
- caption (speech) starts when the answer is ready and the voice is free, and lasts the
  estimated speaking time (2.5 words per second);
- a MOVE whose speech starts after the object's closest point (largest box) is marked LATE.
Writes OUT/sim.mp4 (boxes + captions) and OUT/log.csv.
"""
import csv
import json
import os
import subprocess
import tempfile
import time

import av
import numpy as np
import torch
from PIL import Image, ImageDraw, ImageFont
from transformers import AutoModelForImageTextToText, AutoProcessor

REPO = "/Users/zyrus/Documents/Projects/maya-main"
SRC = "/Users/zyrus/Downloads/bicycle-ride-in-london-canary-wharf-jubilee-plaza-and-reuters-plaza.mp4"
OUT = f"{REPO}/results/live/london_cosmos_sim"
WINDOW_S, FPS_IN, WPS, TRIGGER_TTC, TRACK_COOLDOWN = 2.0, 4, 3.0, 4.0, 4.0

DESCRIBE = """I am blind and I am walking. The video comes from a phone camera on my chest, facing where I walk. The last frame is now. Please be my eyes.

Tell me only about people, vehicles and obstacles near me, within about 5 steps. Ignore buildings, the sky and anything far away. Describe what you see; do not tell me what to do.

What is on my left, what is ahead of me, and what is on my right? For each one, say what it is, about how many steps away, and whether it is coming toward me, moving away, crossing, or not moving. If a side has nothing near, say "nothing".
Answer in this format:
Left: ...
Ahead: ...
Right: ..."""
MOVE = """I am blind and I am walking. The video comes from a phone camera on my chest, facing where I walk. The last frame is now. Please be my eyes.

A {object} is coming toward me, {side} of me, about {seconds} seconds away.
Tell me how to move so I do not walk into it. Give one instruction with a number of steps: "2 steps left", "1 step right", "slow down", "stop", or "keep straight" if it will pass me safely. Then say why in one short sentence.
Answer in this format:
Instruction: ...
Reason: ..."""
SIDE_WORD = {"left": "on the left", "right": "on the right", "ahead": "straight ahead"}


def load_tracks():
    return [json.loads(l) for l in open(f"{REPO}/results/perception/london_walking.jsonl")]


def t_close(rows, tid):
    best = (0.0, None)
    for f in rows:
        for tr in f["tracks"]:
            if tr["id"] == tid and tr["box"][3] - tr["box"][1] > best[0]:
                best = (tr["box"][3] - tr["box"][1], f["t"])
    return best[1]


def load_triggers(rows):
    """First walk v3 event per track (word or new tone), urgency under TRIGGER_TTC."""
    seen, out = {}, []
    for x in csv.DictReader(open(f"{REPO}/results/live/london_walking_v3/log.csv")):
        if not (x["source"] == "fast" or x["kind"] == "new"):
            continue
        tid, ready, urg = int(x["track"]), float(x["ready"]), float(x["urgency"])
        if urg >= TRIGGER_TTC or (tid in seen and ready - seen[tid] < TRACK_COOLDOWN):
            continue
        seen[tid] = ready
        out.append(dict(t=ready, track=tid, cls=x["cls"], side=x["side"], urgency=urg,
                        t_close=t_close(rows, tid)))
    return sorted(out, key=lambda e: e["t"])


def cut(t_end, path):
    t0 = max(0.0, t_end - WINDOW_S)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t0:.3f}", "-i", SRC, "-t", f"{t_end - t0:.3f}",
                    "-vf", f"fps={FPS_IN}", "-an", "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
                    path], check=True)


def main():
    os.makedirs(OUT, exist_ok=True)
    rows = load_tracks()
    dur = rows[-1]["t"]
    triggers = load_triggers(rows)
    print("triggers:", [(round(e["t"], 2), e["track"], e["cls"], e["side"], e["urgency"]) for e in triggers], flush=True)

    mid = "nvidia/Cosmos3-Edge"
    proc = AutoProcessor.from_pretrained(mid)
    model = AutoModelForImageTextToText.from_pretrained(mid, dtype=torch.bfloat16).to("mps").eval()

    def ask(prompt, t_end, td):
        clip = f"{td}/win_{t_end:.2f}.mp4"
        cut(t_end, clip)
        msgs = [{"role": "user", "content": [{"type": "video", "path": clip}, {"type": "text", "text": prompt}]}]
        x = proc.apply_chat_template(msgs, add_generation_prompt=True, tokenize=True, return_dict=True,
                                     return_tensors="pt", enable_thinking=False,
                                     processor_kwargs={"fps": FPS_IN}).to("mps")
        t = time.perf_counter()
        with torch.inference_mode():
            out = model.generate(**x, max_new_tokens=128, do_sample=False, repetition_penalty=1.1)
        text = proc.decode(out[0][x["input_ids"].shape[-1]:], skip_special_tokens=True).split("</think>")[-1].strip()
        return text, time.perf_counter() - t

    # warm-up so the first timed call is not a cold one
    with tempfile.TemporaryDirectory() as td:
        ask("Hi", 2.0, td)

    log, clock, voice_free, done = [], WINDOW_S, 0.0, set()
    with tempfile.TemporaryDirectory() as td:
        while clock < dur:
            waiting = [e for e in triggers if e["t"] <= clock and id(e) not in done]
            if waiting:
                e = waiting[-1]
                done.update(id(w) for w in waiting)  # older waiting triggers are dropped as stale
                prompt = MOVE.format(object=e["cls"], side=SIDE_WORD.get(e["side"], e["side"]),
                                     seconds=max(1, round(e["urgency"])))
                mode = "MOVE"
            elif voice_free <= clock:
                e, prompt, mode = None, DESCRIBE, "DESCRIBE"
            else:
                nxt = min([voice_free] + [t["t"] for t in triggers if id(t) not in done and t["t"] > clock])
                clock = nxt
                continue
            text, dt = ask(prompt, clock, td)
            ready = clock + dt
            spoken = text
            if mode == "MOVE":
                # Only the instruction is spoken; the reason stays in the caption.
                spoken = next((l.split(":", 1)[1].strip() for l in text.splitlines()
                               if l.lower().startswith("instruction")), text)
                # Newest wins: a move cuts off whatever is being spoken.
                for r in log:
                    if r["speech_end"] > ready >= r["speech_start"]:
                        r["speech_end"] = round(ready, 2)
                        r["cut_off"] = True
                voice_free = min(voice_free, ready)
            start = max(ready, voice_free)
            dropped = bool(e and e["t_close"] is not None and start > e["t_close"] + 0.5)
            speak = 0.0 if dropped else len(spoken.split()) / WPS
            if not dropped:
                voice_free = start + speak
            late = bool(e and e["t_close"] is not None and start > e["t_close"])
            row = dict(mode=mode, request_t=round(clock, 2), model_s=round(dt, 2), speech_start=round(start, 2),
                       speech_end=round(start + speak, 2), track=e["track"] if e else "", trigger=(
                           f"{e['cls']} {e['side']} ttc {e['urgency']:.1f}s" if e else ""),
                       t_close=e["t_close"] if e else "", late=late, dropped=dropped, cut_off=False,
                       spoken=spoken, text=text)
            log.append(row)
            print(row, flush=True)
            clock = ready

    with open(f"{OUT}/log.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(log[0]))
        w.writeheader()
        w.writerows(log)
    render(rows, log, dur)


def wrap(d, text, font, width):
    lines = []
    for para in text.splitlines():
        cur = ""
        for word in para.split():
            nxt = (cur + " " + word).strip()
            if d.textlength(nxt, font=font) > width:
                lines.append(cur)
                cur = word
            else:
                cur = nxt
        if cur:
            lines.append(cur)
    return lines


def render(rows, log, dur):
    font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 15)
    small = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 13)
    col = {"left": (255, 140, 0), "ahead": (230, 0, 0), "right": (0, 120, 255)}
    W, H, PAD = 768, 432, 150
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{W}x{H + PAD}", "-r", "30", "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                           f"{OUT}/sim.mp4"], stdin=subprocess.PIPE)
    with av.open(SRC) as c:
        for f in c.decode(video=0):
            t = f.time
            if t > dur:
                break
            im = f.to_image().convert("RGB")
            d = ImageDraw.Draw(im)
            fr = min(rows, key=lambda r: abs(r["t"] - t))
            busy = [r for r in log if r["request_t"] <= t < r["request_t"] + r["model_s"]]
            live = [r for r in log if r["speech_start"] <= t < r["speech_end"]] or \
                   [r for r in log if r.get("dropped") and r["speech_start"] <= t < r["speech_start"] + 1.0]
            focus = {r["track"] for r in busy + live if r["track"] != ""}
            for tr in fr["tracks"]:
                x1, y1, x2, y2 = tr["box"]
                if y2 - y1 < 0.12:
                    continue
                wdt = 6 if tr["id"] in focus else 2
                d.rectangle((x1 * W, y1 * H, x2 * W, y2 * H), outline=col.get(tr["side"], (255, 255, 0)), width=wdt)
            canvas = Image.new("RGB", (W, H + PAD), (0, 0, 0))
            canvas.paste(im, (0, 0))
            d = ImageDraw.Draw(canvas)
            d.rectangle((0, 0, 260, 22), fill=(0, 0, 0))
            status = f"t={t:5.2f}s"
            if busy:
                b = busy[0]
                status += f"  Cosmos: {b['mode']} asked at {b['request_t']:.1f}s"
            d.text((6, 3), status, fill=(255, 255, 255), font=small)
            if live:
                r = live[-1]
                tag = f"[{r['mode']}]" + (f"  trigger: {r['trigger']}" if r["trigger"] else "")
                if r["late"]:
                    tag += "  LATE (object at closest point already)"
                colr = (255, 80, 80) if r["mode"] == "MOVE" else (120, 220, 120)
                d.text((10, H + 6), tag, fill=colr, font=font)
                if r.get("dropped"):
                    tag += "  DROPPED (object passed before answer)"
                    d.text((10, H + 6), tag, fill=colr, font=font)
                body = ("SAYS: " + r["spoken"]) if r["mode"] == "MOVE" else r["text"]
                if r["mode"] == "MOVE":
                    body += "\n" + next((l for l in r["text"].splitlines() if l.lower().startswith("reason")), "")
                for i, line in enumerate(wrap(d, body, font, W - 20)[:6]):
                    d.text((10, H + 28 + 19 * i), line, fill=(255, 255, 255), font=font)
            ff.stdin.write(np.asarray(canvas).tobytes())
    ff.stdin.close()
    ff.wait()
    print("wrote", f"{OUT}/sim.mp4", flush=True)


if __name__ == "__main__":
    main()
