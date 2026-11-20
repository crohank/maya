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

# v1 prompts. v0 (the Mac prompts) on 8 real clips: 18 of 24 MOVE lines LATE, and the
# model picked "1 step right" or "slow down" whatever the scene, twice stepping toward
# the object ("1 step right" for a pole on the right). CHOICE offers only moves that do
# not head toward the object's side and asks for the instruction alone (fewer tokens).
CHOICE = """I am blind and I am walking. The video comes from a phone camera on my chest, facing where I walk. The last frame is now.

A {object} is {side}, about {seconds} seconds from reaching me.
Pick the one instruction that keeps me clear of it, judging the free space you see: {options}.
Answer with only the instruction."""
OPTIONS = {"left": ['"1 step right"', '"slow down"', '"keep straight"'],
           "right": ['"1 step left"', '"slow down"', '"keep straight"'],
           "ahead": ['"1 step left"', '"1 step right"', '"slow down"', '"stop"']}
SHORT_DESCRIBE = """I am blind and I am walking. The video comes from a phone camera on my chest, facing where I walk. The last frame is now.

Name at most two things within about 5 steps that matter for my next steps: people coming toward me, obstacles in my path, a curb or crosswalk. Say what, which side, and how many steps, in 8 words or fewer, like "Bench left, 3 steps. Person ahead, 4 steps."
Never mention clothing or colors. Describe; do not tell me what to do. If nothing is near, say "Clear."
"""
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


def cut(src, t_end, path, window=WINDOW_S, fps=FPS_IN):
    t0 = max(0.0, t_end - window)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t0:.3f}", "-i", src, "-t", f"{t_end - t0:.3f}",
                    "-vf", f"fps={fps},scale=-2:432", "-an", "-c:v", "libx264", "-preset", "veryfast",
                    "-pix_fmt", "yuv420p", path], check=True)


def t_close(frames, tid):
    best = (0.0, None)
    for f in frames:
        for tr in f["tracks"]:
            if tr["id"] == tid and tr["box"][3] - tr["box"][1] > best[0]:
                best = (tr["box"][3] - tr["box"][1], f["t"])
    return best[1]


def triggers_from(frames, words, tones, gate=0.0, ttc_max=TRIGGER_TTC):
    """The teammate's rule on Maya's own walk events: first word or new tone per track,
    urgency under TRIGGER_TTC, detector confidence at least MIN_CONF, 4 s per-track cooldown."""
    ev = [(x["ready"], x) for x in words if x["source"] == "fast" and x["status"] == "spoken"]
    ev += [(x["ready"], x) for x in tones if x.get("kind") == "new" and x["status"] == "tone"]
    seen, out = {}, []
    for ready, x in sorted(ev, key=lambda v: v[0]):
        tid, urg = x["track"], float(x["urgency"])
        X = x.get("X")
        # gate: ask for a move only when walk v3 predicts the object passes within gate metres
        # of the walker's centre line (X is None for objects it cannot place; those pass).
        if gate and X is not None and abs(float(X)) > gate:
            continue
        if urg >= ttc_max or (tid in seen and ready - seen[tid] < TRACK_COOLDOWN):
            continue
        conf = min(((f["t"], tr["conf"]) for f in frames for tr in f["tracks"] if tr["id"] == tid),
                   key=lambda v: abs(v[0] - ready), default=(0, 0))[1]
        if conf < MIN_CONF:
            continue
        seen[tid] = ready
        out.append(dict(t=ready, track=tid, cls=x["cls"], side=x["side"], urgency=urg, t_close=t_close(frames, tid),
                        X=x.get("X")))
    return out



def move_options(e, o):
    """v1: fixed per side. x: from the predicted pass offset X (metres, + is right): a step
    away from the side it passes on, or stop; both sides when it comes straight on."""
    if o["options"] == "sk":
        return ['"stop"', '"keep straight"']
    if o["options"] == "v1" or e.get("X") in (None, ""):
        return OPTIONS.get(e["side"], OPTIONS["ahead"])
    X = float(e["X"])
    if abs(X) < 0.2:
        return ['"1 step left"', '"1 step right"', '"keep straight"' if o["options"] == "xk" else '"stop"']
    away = '"1 step right"' if X < 0 else '"1 step left"'
    return [away, '"keep straight"'] if o["options"] == "xk" else [away, '"stop"']

def cosmos_loop(src, dur, triggers, speech, o):
    from maya.video import cosmos_loader
    cm = o.get("cm") or cosmos_loader()
    o["cm"] = cm
    proc, model, torch = cm["proc"], cm["model"], cm["torch"]

    def ask(prompt, t_end, td, max_new):
        clip = f"{td}/win_{t_end:.2f}.mp4"
        cut(src, t_end, clip, o["window"], o["fps_in"])
        msgs = [{"role": "user", "content": [{"type": "video", "path": clip}, {"type": "text", "text": prompt}]}]
        x = proc.apply_chat_template(msgs, add_generation_prompt=True, tokenize=True, return_dict=True,
                                     return_tensors="pt", enable_thinking=False,
                                     processor_kwargs={"fps": o["fps_in"]}).to(model.device)
        t = time.perf_counter()
        with torch.inference_mode():
            out = model.generate(**x, max_new_tokens=max_new, do_sample=False, repetition_penalty=1.1)
        text = proc.decode(out[0][x["input_ids"].shape[-1]:], skip_special_tokens=True).split("</think>")[-1].strip()
        return text, time.perf_counter() - t

    with tempfile.TemporaryDirectory() as td:
        ask("Hi", WINDOW_S, td, 4)
    rows, clock, voice_free, done, last_desc, last_desc_t = [], o["window"], 0.0, set(), None, -99.0
    with tempfile.TemporaryDirectory() as td:
        while clock < dur - 0.5:
            waiting = [e for e in triggers if e["t"] <= clock and id(e) not in done]
            if waiting:
                e = waiting[-1]
                done.update(id(w) for w in waiting)
                side = SIDE_WORD.get(e["side"], e["side"])
                sec = max(1, round(e["urgency"]))
                if o["move"] == "choice":
                    prompt = CHOICE.format(object=e["cls"], side=side, seconds=sec,
                                           options=", ".join(move_options(e, o)))
                else:
                    prompt = MOVE.format(object=e["cls"], side=side, seconds=sec)
                mode = "MOVE"
            elif voice_free <= clock and clock - last_desc_t >= o["describe_gap"] and o["describe"] != "off":
                e, mode = None, "DESCRIBE"
                prompt = SHORT_DESCRIBE if o["describe"] == "short" else DESCRIBE
                last_desc_t = clock
            else:
                nxt = [t["t"] for t in triggers if id(t) not in done and t["t"] > clock]
                if voice_free > clock:
                    nxt.append(voice_free)
                if o["describe"] != "off":
                    nxt.append(max(voice_free, last_desc_t + o["describe_gap"]))
                nxt = [n for n in nxt if n > clock]
                if not nxt:
                    break
                clock = min(nxt)
                continue
            max_new = o["describe_tokens"] if mode == "DESCRIBE" else o["move_tokens"]
            text, dt = ask(prompt, clock, td, max_new)
            ready = clock + dt
            spoken = text
            if mode == "MOVE":
                spoken = next((ln.split(":", 1)[1].strip() for ln in text.splitlines()
                               if ln.lower().startswith("instruction")), text.splitlines()[0] if text else "")
                spoken = spoken.strip().strip('"').strip()
                if o["move"] == "choice" and spoken.lower().rstrip(".") == "keep straight":
                    spoken = ""   # nothing to do: stay quiet, the beep already marked it
                elif spoken and not spoken.endswith("."):
                    spoken += "."
                spoken = spoken[:1].upper() + spoken[1:]
            spoken = spoken.replace("\n", " ").strip()
            if mode == "DESCRIBE":
                if spoken.lower().strip(".") in ("clear", "clear around you") or spoken == last_desc:
                    spoken_out = ""   # repeats and "Clear." carry nothing a walker can use
                else:
                    spoken_out = spoken
                last_desc = spoken
                spoken = spoken_out
            _, sdur = speech.get(spoken) if spoken else (None, 0.0)
            voice_free = max(voice_free, ready) + sdur
            rows.append(dict(mode=mode, request_t=round(clock, 2), model_s=round(dt, 2), ready=round(ready, 2),
                             track=e["track"] if e else "", t_close=e["t_close"] if e else None,
                             trigger=f"{e['cls']} {e['side']} ttc {e['urgency']:.1f}s" if e else "",
                             spoken=spoken, text=text))
            print(mode, round(clock, 2), round(dt, 2), spoken[:80], flush=True)
            clock = ready
    return rows


def schedule(items, speech):
    """One voice: items sorted by ready time, priority cuts and short waits. Adds start/end/status."""
    out, cur = [], None
    for it in sorted(items, key=lambda i: i["ready"]):
        if not it["spoken"]:
            it.update(status="silent", start=None, end=None)
            out.append(it)
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


def find_video(stem):
    for p in (f"/main/data/walk8/{stem}.mp4", f"/main/data/realtest/{stem}.mp4", f"/main/test_videos/{stem}.mp4",
              f"/main/data/user_clips/{stem}.mp4"):
        if Path(p).exists():
            return p
    raise SystemExit(f"no video for {stem}")


def run_clip(stem, o, speech, voice):
    src = o.get("video") or find_video(stem)
    frames = [json.loads(line) for line in open(f"/main/results/perception/{stem}.jsonl")]
    dur = min(frames[-1]["t"], lh.ffprobe_duration(src))
    cfg = dict(w3.BASE, scene=1, scene_tag="v2", sounds=1, steps=o["steps"], **w3.parse_sets(o["wset"]))
    w3.annotate(frames, w3.video_aspect(src), cfg)
    scene = []
    sp = Path(f"/main/results/scene/{stem}_{o['scene_tag']}.jsonl")
    if sp.exists():
        rows = [json.loads(line) for line in open(sp)]
        stripe_cues = []
        if o["corner"] == "stripes":
            # Cosmos-only stack: the corner word comes from stripes.py (pixels), and a row
            # counts as "at the edge" for traffic and obstacle words when stripes were seen
            # in the last 3 s or the ground crop said street.
            st = [json.loads(line) for line in open(f"/main/results/scene/{stem}_stripes.jsonl")]
            run, last = 0, -99.0
            for r in st:
                run = run + 1 if r["stripes"] else 0
                # stripes reaching the bottom edge are under the walker: already crossing
                # (v2 review: "Curb and crosswalk ahead" said mid-crossing 4 times)
                under = o["stripe_under"] < 9 and ((r.get("nearest") or 0) >= o["stripe_under"] or o["stripe_road"] and any(
                    x["road"] for x in rows if r["t"] - 2 <= x["t"] <= r["t"]))
                if run == 2 and r["t"] - last > 8 and not under:
                    last = r["t"]
                    stripe_cues.append(dict(t=r["t"], ready=r["t"] + 0.05, answer=o["corner_word"], kind="corner"))
            seen = [r["t"] for r in st if r["stripes"]]
            for r in rows:
                r["edge"] = r["road"] or any(r["t"] - 3 <= s <= r["t"] for s in seen)
        scene = walk_scene.scene_cues(rows, dict(walk_scene.CUE, traffic=cfg["scene_traffic"], stages=o["stages"],
                                                 obstacles=o["vlm_obstacles"], traffic_gap=o["traffic_gap"]), frames)
        if o["corner"] == "stripes":
            scene = [c for c in scene if c["kind"] != "corner"] + stripe_cues
            if o["traffic_near_corner"]:
                # "Cars passing." matters while waiting at the curb; inside the crosswalk
                # or on the sidewalk it was mostly noise (v3 review)
                scene = [c for c in scene if c["kind"] != "traffic" or any(
                    s["t"] - 1 <= c["t"] <= s["t"] + o["traffic_near_corner"] for s in stripe_cues)]
    if o["path_obstacles"]:
        pp = Path(f"/main/results/scene/{stem}_path.jsonl")
        if pp.exists():
            rows_p = [json.loads(line) for line in open(pp)]
            last = {}
            for a, b in zip(rows_p, rows_p[1:]):
                nm = b["name"]
                if nm and a["name"] == nm and b["t"] - last.get(nm, -99) > 10:
                    last[nm] = b["t"]
                    scene.append(dict(t=b["t"], ready=b["t"] + b["lat"], kind="path", answer=f"{nm} ahead."))
    if o["stairs"]:
        stp = Path(f"/main/results/scene/{stem}_stairs.jsonl")
        if stp.exists():
            rows_s = [json.loads(line) for line in open(stp)]
            last = -99.0
            for a, b in zip(rows_s, rows_s[1:]):
                if a["answer"] == b["answer"] != "no" and b["t"] - last > 15:
                    last = b["t"]
                    scene.append(dict(t=b["t"], ready=b["t"] + b["lat"], kind="stairs",
                                      answer=f"Stairs ahead, going {b['answer']}."))
    if lh.has_audio(src):
        from maya import audio, sound
        from maya.engine import Engine
        eng = o.setdefault("eng", Engine())
        heard = sound.alert_timeline(eng, audio.load(src), repeat_s=o["alert_repeat"])
        scene = list(scene) + [dict(t=end, ready=end + dt, answer=ph.split(" ", 1)[1].capitalize() + ".", kind="sound")
                               for end, dt, ph in heard]
    words, tones = w3.simulate(frames, cfg, voice, scene)
    triggers = triggers_from(frames, words, tones, o["move_gate"], o["trigger_ttc"])
    print(stem, "triggers:", [(round(e["t"], 2), e["cls"], e["side"], e["urgency"]) for e in triggers], flush=True)
    cosmos = cosmos_loop(src, dur, triggers, speech, o)
    items = [dict(c) for c in cosmos]
    for x in words:
        if x["status"] != "spoken":
            continue
        mode = "ALERT" if x["source"] == "scene" else "WALK"
        if mode == "WALK" and o["walk_words"] == "off":
            continue
        items.append(dict(mode=mode, ready=round(x["ready"], 2), spoken=x["answer"], text=x["answer"],
                          track=x["track"] if mode == "WALK" else "", t_close=None, trigger=""))
    sched = schedule(items, speech)
    out_dir = Path(f"/app/results/live/{stem}_cc_{o['tag']}")
    out_dir.mkdir(parents=True, exist_ok=True)
    keys = ["mode", "request_t", "model_s", "ready", "start", "end", "status", "cut_off", "late", "trigger", "track",
            "t_close", "spoken", "text"]
    with open(out_dir / "log.csv", "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
        wr.writeheader()
        for s in sched:
            wr.writerow({k: (round(v, 2) if isinstance(v, float) else v) for k, v in s.items()})
    (out_dir / "settings.json").write_text(json.dumps({k: v for k, v in o.items() if k not in ("cm", "eng")}))
    if o.get("render_dir"):
        name = o.get("names", {}).get(stem, stem)
        out_mp4 = f"{o['render_dir']}/{name}.mp4"
        Path(out_mp4).parent.mkdir(parents=True, exist_ok=True)
        render(src, frames, sched, tones, dur, out_mp4)
        print("wrote", out_mp4, flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stems", nargs="+")
    ap.add_argument("--tag", required=True)
    ap.add_argument("--move", default="choice", choices=["team", "choice"])
    ap.add_argument("--move-tokens", type=int, default=12)
    ap.add_argument("--describe", default="short", choices=["team", "short", "off"])
    ap.add_argument("--describe-tokens", type=int, default=24)
    ap.add_argument("--describe-gap", type=float, default=4.0)
    ap.add_argument("--window", type=float, default=2.0)
    ap.add_argument("--fps-in", type=int, default=4)
    ap.add_argument("--walk-words", default="on", choices=["on", "off"])
    ap.add_argument("--move-gate", type=float, default=0.0, help="metres; 0 = every trigger")
    ap.add_argument("--scene-tag", default="v2", help="v2: Qwen3-VL scene rows; cv2: Cosmos")
    ap.add_argument("--corner", default="vlm", choices=["vlm", "stripes"])
    ap.add_argument("--steps", type=int, default=0)
    ap.add_argument("--stairs", type=int, default=0)
    ap.add_argument("--path-obstacles", type=int, default=0)
    ap.add_argument("--options", default="v1", choices=["v1", "x", "xk", "sk"])
    ap.add_argument("--trigger-ttc", type=float, default=TRIGGER_TTC)
    ap.add_argument("--stages", type=int, default=1)
    ap.add_argument("--vlm-obstacles", type=int, default=1)
    ap.add_argument("--corner-word", default="Crosswalk ahead.")
    ap.add_argument("--wset", action="append", default=[], help="walk_v3 BASE key=value")
    ap.add_argument("--stripe-under", type=float, default=9.0, help="skip the corner word when stripes reach this low")
    ap.add_argument("--traffic-gap", type=float, default=8.0)
    ap.add_argument("--traffic-near-corner", type=float, default=0.0, help="seconds after a corner word; 0 = anywhere")
    ap.add_argument("--stripe-road", type=int, default=0, help="1: also skip when Cosmos ground said street (v3: too strong, 1 corner word in 22 clips)")
    ap.add_argument("--alert-repeat", type=float, default=10.0)
    ap.add_argument("--render-dir")
    ap.add_argument("--names", help="json map stem -> output file name")
    args = ap.parse_args()
    o = dict(vars(args))
    o["names"] = json.loads(args.names) if args.names else {}
    speech = Speech("/app/results/live/phrases_combined")
    voice = w3.Voice(w3.fh.V2_LENGTH_SCALE)
    for stem in args.stems:
        run_clip(stem, o, speech, voice)


if __name__ == "__main__":
    main()
