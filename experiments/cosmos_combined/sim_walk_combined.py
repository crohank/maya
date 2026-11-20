"""Combined walk simulation: the teammate's Cosmos MOVE/DESCRIBE loop with boxes
(experiments/cosmos_mac/sim_walk_cosmos_only.py) plus Maya's walk audio
(scripts/walk_v3.py): panned beeps, short object words, curb, crosswalk and
crossing-stage words, siren, horn and reversing-truck words, all in the Piper voice.

Differences from the Mac script:
- Cosmos3-Edge 4-bit (ubr-physical-ai/Cosmos3-Edge-NF4-bnb) on CUDA, the same
  loader as maya/video.py; the BF16 reasoner (7.7 GB) does not fit the 6 GB left
  on the 8 GB card. Prompts, triggers and clock are unchanged.
- Speech is synthesised with Piper and timed by its real length, not 3 words/s.
- One voice for everything. Priority: MOVE and alerts 3, walk words 2, DESCRIBE 1.
  A higher-priority line cuts off a DESCRIBE; otherwise it waits up to WAIT_S.

Run in the maya-engine image with the worktree at /app and the main checkout
(clips, perception tracks, scene rows) at /main:
  python experiments/cosmos_combined/sim_walk_combined.py --stem yt_siren1
"""
import argparse
import csv
import hashlib
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import av
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, "/app/scripts")
import live_harness as lh  # noqa: E402
import walk_scene  # noqa: E402
import walk_v3 as w3  # noqa: E402

sys.path.insert(0, "/app/experiments/cosmos_mac")
from sim_walk_cosmos_only import DESCRIBE, MOVE, SIDE_WORD, TRACK_COOLDOWN, TRIGGER_TTC, MIN_CONF, wrap  # noqa: E402

WINDOW_S, FPS_IN = 2.0, 4
WAIT_S = {3: 2.0, 2: 0.75, 1: 0.0}
PRIO = {"MOVE": 3, "ALERT": 3, "WALK": 2, "DESCRIBE": 1}
COLOR = {"MOVE": (255, 80, 80), "ALERT": (255, 200, 0), "WALK": (120, 180, 255), "DESCRIBE": (120, 220, 120)}
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
SMALL = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


class Speech:
    """Piper wavs keyed by a hash of the text (Cosmos lines are too long for walk_v3.Voice file names)."""

    def __init__(self, d):
        self.dir = Path(d)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.tts = None

    def get(self, text):
        path = self.dir / (hashlib.sha1(text.encode()).hexdigest()[:16] + ".wav")
        if not path.exists():
            self.tts = self.tts or lh.Tts(w3.fh.V2_LENGTH_SCALE)
            self.tts.say(text, str(path))
        return path, len(w3.read_mono(path)) / w3.SR


def cut(src, t_end, path):
    t0 = max(0.0, t_end - WINDOW_S)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t0:.3f}", "-i", src, "-t", f"{t_end - t0:.3f}",
                    "-vf", f"fps={FPS_IN},scale=-2:432", "-an", "-c:v", "libx264", "-preset", "veryfast",
                    "-pix_fmt", "yuv420p", path], check=True)


def t_close(frames, tid):
    best = (0.0, None)
    for f in frames:
        for tr in f["tracks"]:
            if tr["id"] == tid and tr["box"][3] - tr["box"][1] > best[0]:
                best = (tr["box"][3] - tr["box"][1], f["t"])
    return best[1]


def triggers_from(frames, words, tones):
    """The teammate's rule on Maya's own walk events: first word or new tone per track,
    urgency under TRIGGER_TTC, detector confidence at least MIN_CONF, 4 s per-track cooldown."""
    ev = [(x["ready"], x) for x in words if x["source"] == "fast" and x["status"] == "spoken"]
    ev += [(x["ready"], x) for x in tones if x.get("kind") == "new" and x["status"] == "tone"]
    seen, out = {}, []
    for ready, x in sorted(ev, key=lambda v: v[0]):
        tid, urg = x["track"], float(x["urgency"])
        if urg >= TRIGGER_TTC or (tid in seen and ready - seen[tid] < TRACK_COOLDOWN):
            continue
        conf = min(((f["t"], tr["conf"]) for f in frames for tr in f["tracks"] if tr["id"] == tid),
                   key=lambda v: abs(v[0] - ready), default=(0, 0))[1]
        if conf < MIN_CONF:
            continue
        seen[tid] = ready
        out.append(dict(t=ready, track=tid, cls=x["cls"], side=x["side"], urgency=urg, t_close=t_close(frames, tid)))
    return out


def cosmos_loop(src, dur, triggers, speech):
    from maya.video import cosmos_loader
    cm = cosmos_loader()
    proc, model, torch = cm["proc"], cm["model"], cm["torch"]

    def ask(prompt, t_end, td, max_new):
        clip = f"{td}/win_{t_end:.2f}.mp4"
        cut(src, t_end, clip)
        msgs = [{"role": "user", "content": [{"type": "video", "path": clip}, {"type": "text", "text": prompt}]}]
        x = proc.apply_chat_template(msgs, add_generation_prompt=True, tokenize=True, return_dict=True,
                                     return_tensors="pt", enable_thinking=False,
                                     processor_kwargs={"fps": FPS_IN}).to(model.device)
        t = time.perf_counter()
        with torch.inference_mode():
            out = model.generate(**x, max_new_tokens=max_new, do_sample=False, repetition_penalty=1.1)
        text = proc.decode(out[0][x["input_ids"].shape[-1]:], skip_special_tokens=True).split("</think>")[-1].strip()
        return text, time.perf_counter() - t

    with tempfile.TemporaryDirectory() as td:
        ask("Hi", WINDOW_S, td, 4)
    rows, clock, voice_free, done = [], WINDOW_S, 0.0, set()
    with tempfile.TemporaryDirectory() as td:
        while clock < dur - 0.5:
            waiting = [e for e in triggers if e["t"] <= clock and id(e) not in done]
            if waiting:
                e = waiting[-1]
                done.update(id(w) for w in waiting)
                prompt, mode = MOVE.format(object=e["cls"], side=SIDE_WORD.get(e["side"], e["side"]),
                                           seconds=max(1, round(e["urgency"]))), "MOVE"
            elif voice_free <= clock:
                e, prompt, mode = None, DESCRIBE, "DESCRIBE"
            else:
                clock = min([voice_free] + [t["t"] for t in triggers if id(t) not in done and t["t"] > clock])
                continue
            text, dt = ask(prompt, clock, td, 32 if mode == "DESCRIBE" else 128)
            ready = clock + dt
            spoken = text
            if mode == "MOVE":
                spoken = next((ln.split(":", 1)[1].strip() for ln in text.splitlines()
                               if ln.lower().startswith("instruction")), text.splitlines()[0] if text else "")
            spoken = spoken.replace("\n", " ").strip()
            _, sdur = speech.get(spoken) if spoken else (None, 0.0)
            voice_free = max(voice_free, ready) + sdur
            rows.append(dict(mode=mode, request_t=round(clock, 2), model_s=round(dt, 2), ready=round(ready, 2),
                             track=e["track"] if e else "", t_close=e["t_close"] if e else None,
                             trigger=f"{e['cls']} {e['side']} ttc {e['urgency']:.1f}s" if e else "",
                             spoken=spoken, text=text))
            print(mode, round(clock, 2), round(dt, 2), spoken[:80], flush=True)
            clock = ready
    del model
    torch.cuda.empty_cache()
    return rows


def schedule(items, speech):
    """One voice: items sorted by ready time, priority cuts and short waits. Adds start/end/status."""
    out, cur = [], None
    for it in sorted(items, key=lambda i: i["ready"]):
        if not it["spoken"]:
            continue
        path, d = speech.get(it["spoken"])
        it.update(wav=str(path), dur=d, prio=PRIO[it["mode"]])
        r = it["ready"]
        if cur and r < cur["end"]:
            if it["prio"] > cur["prio"] and cur["mode"] == "DESCRIBE":
                cur.update(end=r, cut_off=True)
                start = r
            elif cur["end"] - r <= WAIT_S[it["prio"]]:
                start = cur["end"]
            else:
                it.update(status="dropped", start=None, end=None)
                out.append(it)
                continue
        else:
            start = r
        it.update(start=start, end=start + d, status="spoken", cut_off=False)
        if it["mode"] == "MOVE" and it["t_close"] is not None:
            it["late"] = start > it["t_close"]
        out.append(it)
        cur = it
    return out


def render(src, frames, sched, tones, dur, out_mp4, bg_volume=0.45):
    with av.open(src) as c:
        st = c.streams.video[0]
        sw, sh = st.codec_context.width, st.codec_context.height
    W = 768 if sw >= sh else 540
    H = int(round(sh * W / sw / 2) * 2)
    PAD = 150
    font, small = ImageFont.truetype(FONT, 15 if W > 600 else 13), ImageFont.truetype(SMALL, 13)
    side_col = {"left": (255, 140, 0), "ahead": (230, 0, 0), "right": (0, 120, 255)}
    with tempfile.TemporaryDirectory() as td:
        silent = f"{td}/v.mp4"
        ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                               "-s", f"{W}x{H + PAD}", "-r", "30", "-i", "-", "-c:v", "libx264", "-pix_fmt",
                               "yuv420p", silent], stdin=subprocess.PIPE)
        spoken = [s for s in sched if s["status"] == "spoken"]
        with av.open(src) as c:
            for f in c.decode(video=0):
                t = float(f.time)
                if t > dur:
                    break
                im = f.to_image().convert("RGB").resize((W, H))
                d = ImageDraw.Draw(im)
                fr = min(frames, key=lambda r: abs(r["t"] - t))
                live = [s for s in spoken if s["start"] <= t < s["end"] + 0.6]
                focus = {s.get("track") for s in live if s.get("track") not in ("", None)}
                for tr in fr["tracks"]:
                    x1, y1, x2, y2 = tr["box"]
                    if y2 - y1 < 0.12:
                        continue
                    d.rectangle((x1 * W, y1 * H, x2 * W, y2 * H), outline=side_col.get(tr["side"], (255, 255, 0)),
                                width=6 if tr["id"] in focus else 2)
                canvas = Image.new("RGB", (W, H + PAD), (0, 0, 0))
                canvas.paste(im, (0, 0))
                d = ImageDraw.Draw(canvas)
                beep = [x for x in tones if x["status"] == "tone" and x["audio_start"] <= t < x["audio_start"] + 0.5]
                status = f"t={t:5.2f}s" + (f"  beep {beep[-1]['side']}" if beep else "")
                d.rectangle((0, 0, 200, 20), fill=(0, 0, 0))
                d.text((6, 3), status, fill=(255, 255, 255), font=small)
                y = H + 6
                for s in live[-3:]:
                    tag = f"[{s['mode']}] " + (f"({s['trigger']}) " if s.get("trigger") else "")
                    if s.get("late"):
                        tag += "LATE "
                    body = tag + s["spoken"]
                    if s["mode"] == "MOVE":
                        reason = next((ln for ln in s["text"].splitlines() if ln.lower().startswith("reason")), "")
                        body += ("  " + reason) if reason else ""
                    for line in wrap(d, body, font, W - 20)[:3]:
                        if y > H + PAD - 18:
                            break
                        d.text((10, y), line, fill=COLOR[s["mode"]], font=font)
                        y += 18
                ff.stdin.write(np.asarray(canvas).tobytes())
        ff.stdin.close()
        ff.wait()

        cfg = dict(w3.BASE)
        mix = np.zeros((int(w3.SR * dur) + w3.SR, 2), np.float32)
        for s in spoken:
            x = w3.read_mono(s["wav"])[:int((s["end"] - s["start"]) * w3.SR)]
            i = int(s["start"] * w3.SR)
            seg = mix[i:i + len(x)]
            seg += x[:len(seg), None] * 0.9
        for e in tones:
            if e["status"] != "tone":
                continue
            x = w3.tone_wav(e["side"], e["band"], cfg)
            i = int(e["audio_start"] * w3.SR)
            seg = mix[i:i + len(x)]
            seg += x[:len(seg)]
        track = f"{td}/a.wav"
        w3.write_wav(track, mix[:int(w3.SR * dur)])
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", silent, "-i", track]
        if lh.has_audio(src):
            cmd += ["-i", src, "-filter_complex",
                    f"[2:a]volume={bg_volume},aformat=channel_layouts=stereo[bg];"
                    "[1:a][bg]amix=inputs=2:normalize=0:duration=first[aout]", "-map", "0:v", "-map", "[aout]"]
        else:
            cmd += ["-map", "0:v", "-map", "1:a"]
        cmd += ["-t", f"{dur:.2f}", "-c:v", "copy", "-c:a", "aac", out_mp4]
        subprocess.run(cmd, check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stem", required=True)
    ap.add_argument("--video", help="default /main/data/walk8/<stem>.mp4")
    ap.add_argument("--out-video", required=True)
    args = ap.parse_args()
    src = args.video or f"/main/data/walk8/{args.stem}.mp4"
    frames = [json.loads(line) for line in open(f"/main/results/perception/{args.stem}.jsonl")]
    dur = min(frames[-1]["t"], lh.ffprobe_duration(src))

    cfg = dict(w3.BASE, scene=1, scene_tag="v2", sounds=1)
    w3.annotate(frames, w3.video_aspect(src), cfg)
    rows = [json.loads(line) for line in open(f"/main/results/scene/{args.stem}_v2.jsonl")]
    scene = walk_scene.scene_cues(rows, dict(walk_scene.CUE, traffic=cfg["scene_traffic"]), frames)
    if lh.has_audio(src):
        from maya import audio, sound
        from maya.engine import Engine
        heard = sound.alert_timeline(Engine(), audio.load(src))
        scene = list(scene) + [dict(t=end, ready=end + dt, answer=ph.split(" ", 1)[1].capitalize() + ".", kind="sound")
                               for end, dt, ph in heard]
        import torch
        torch.cuda.empty_cache()
    voice = w3.Voice(w3.fh.V2_LENGTH_SCALE)
    words, tones = w3.simulate(frames, cfg, voice, scene)

    speech = Speech("/app/results/live/phrases_combined")
    triggers = triggers_from(frames, words, tones)
    print("triggers:", [(round(e["t"], 2), e["cls"], e["side"], e["urgency"]) for e in triggers], flush=True)
    cosmos = cosmos_loop(src, dur, triggers, speech)

    items = [dict(c) for c in cosmos]
    for x in words:
        if x["status"] != "spoken":
            continue
        mode = "ALERT" if x["source"] == "scene" else "WALK"
        items.append(dict(mode=mode, ready=round(x["ready"], 2), spoken=x["answer"], text=x["answer"],
                          track=x["track"] if mode == "WALK" else "", t_close=None, trigger=""))
    sched = schedule(items, speech)
    out_dir = Path(f"/app/results/live/{args.stem}_cosmos_combined")
    out_dir.mkdir(parents=True, exist_ok=True)
    keys = ["mode", "request_t", "model_s", "ready", "start", "end", "status", "cut_off", "late", "trigger", "track",
            "spoken", "text"]
    with open(out_dir / "log.csv", "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
        wr.writeheader()
        for s in sched:
            wr.writerow({k: (round(v, 2) if isinstance(v, float) else v) for k, v in s.items()})
    Path(args.out_video).parent.mkdir(parents=True, exist_ok=True)
    render(src, frames, sched, tones, dur, args.out_video)
    print("wrote", args.out_video, flush=True)


if __name__ == "__main__":
    main()
