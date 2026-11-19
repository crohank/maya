"""Walk mode v3, "cane companion": tones for repeats, words for news.

Built on the v2 fast path (scripts/fused_harness.py, docs/decisions.md D9) from
precomputed tracks (results/perception/<stem>.jsonl). No GPU, no Cosmos.

- Earcons: a 150 ms stereo tone panned to the side the object will pass on,
  pitch and per-track repeat rate by time to contact.
- Words only for a new kind of object, a vehicle, or time to contact under
  WORD_TTC_S, and at most once per track. Everything else is a tone.
- Collision-course filter: the box centre is extrapolated with its lateral rate
  over the time to contact and converted to metres with the class height; only
  tracks inside the walking corridor warn.
- The voice and the tone player are separate channels (tones can play over
  speech) unless single_channel=1.

Describes, never steers: words are "<Class> [crossing] <side>." only.

Run inside the maya-engine image from the repo root:
  python scripts/walk_v3.py eval    # variants on the 4 labelled clips, writes results/walk_v3.md
  python scripts/walk_v3.py grid    # threshold grid, writes results/walk_v3_grid.md
  python scripts/walk_v3.py run --video test_videos/london_walking.mp4 [--set key=value]
      # writes results/live/<stem>_v3/ (annotated.mp4, log.csv, summary.md, tones/)
"""
import argparse
import collections
import csv
import glob
import json
import math
import shutil
import statistics
import subprocess
import tempfile
import time
import wave
from pathlib import Path

import numpy as np

import fused_harness as fh
import live_harness as lh
import score_walk as sw

# Real-world size used to turn an image offset into metres. Widths are used when
# the box is cut by the top or bottom frame edge (a close person on a chest
# camera). Poles have no entry: their boxes are almost always cut by the top.
HEIGHT_M = {"person": 1.7, "bicycle": 1.7, "motorcycle": 1.5, "car": 1.5, "truck": 2.5,
            "bus": 3.0, "stroller": 1.0, "wheelchair": 1.3, "scooter": 1.6,
            "trash can": 1.0, "fire hydrant": 0.8, "traffic cone": 0.7, "bench": 0.9, "cart": 1.0}
WIDTH_M = {"person": 0.5, "stroller": 0.6, "wheelchair": 0.7, "trash can": 0.6}
EDGE = 0.02

BASE = dict(
    ttc=4.0, min_h=0.15, confirm=2, window=3,
    filter="world",        # v2 | img | world | world_v2
    # Half width at contact. 0.8 m (walker plus passer plus margin) missed the labelled
    # must_warn passers, who go by 1 to 2 m to the side (results/walk_v3_grid.md).
    corridor_m=1.6,
    img_half=0.25,
    side="pred",           # v2 | pred
    side_m=0.25,
    lat_window=0.75,
    # Extrapolating over the full TTC amplifies lateral-rate noise; 0 to 1 s scored the same.
    max_horizon=0.5,
    lat_gain=1.0,
    yaw_comp=1,            # Fifth Ave pans right: every track drifts +0.1 to +0.2 width/s
    cross_h=0.30, cross_urgency=2.0, cross_horizon=1.0,
    vehicle_bypass=1,      # vehicles skip the corridor test, as in v2
    words="once",          # once | v2 (4 s per-track cooldown, every best track) | off
    new_kind_s=8.0,
    word_ttc=1.5,
    tones=1,
    lead_tone="busy",      # never | busy | always
    tone_s=0.15, tone_gap=0.85, tone_stale=0.3,
    tone_repeat=(3.0, 2.0, 1.0),   # seconds between tones per track, low / mid / high urgency
    bands=(2.5, 1.5),      # TTC under 2.5 s is mid, under 1.5 s is high
    word_stale=0.75,
    single_channel=0,
)
TONE_HZ = (660.0, 990.0, 1480.0)
PAN = {"left": -0.8, "ahead": 0.0, "right": 0.8}
SR = 22050
SAME_TEXT_S = fh.SAME_TEXT_COOLDOWN_S
# Piper synthesis of a two-word phrase: speech start minus ready time in the logged v2
# runs (results/live/*_fastonly2/log.csv) was 0.032 s min, 0.042 s p25 over 57 utterances.
SYNTH_S = 0.05
PHRASE_DIR = "results/live/phrases_v3"


def slope(ts, vs):
    tm, vm = sum(ts) / len(ts), sum(vs) / len(vs)
    den = sum((t - tm) ** 2 for t in ts)
    return sum((t - tm) * (v - vm) for t, v in zip(ts, vs)) / den if den > 1e-9 else 0.0


def annotate(frames, aspect, cfg):
    """Add lateral rate (_lat, width fraction per s, with the outward drift of
    walking forward removed) to every track."""
    hist = collections.defaultdict(collections.deque)
    for fr in frames:
        t = fr["t"]
        for tr in fr["tracks"]:
            x1, y1, x2, y2 = tr["box"]
            cx = (x1 + x2) / 2
            q = hist[tr["id"]]
            q.append((t, cx, math.log(max(1e-6, math.sqrt(max(1e-9, (x2 - x1) * (y2 - y1)))))))
            while q and t - q[0][0] > cfg["lat_window"] + 1e-6:
                q.popleft()
            tr["_lat"] = None
            if len(q) >= 3 and q[-1][0] - q[0][0] >= 0.25:
                ts = [p[0] for p in q]
                # u = f X / Z, so du/dt = f Xdot / Z + u * (-Zdot / Z); the second term
                # is the expansion drift and is subtracted (perception.py does the same).
                tr["_lat"] = slope(ts, [p[1] for p in q]) - (cx - 0.5) * slope(ts, [p[2] for p in q])
        if cfg["yaw_comp"]:
            lats = [tr["_lat"] for tr in fr["tracks"]
                    if tr["_lat"] is not None and tr["box"][3] - tr["box"][1] >= 0.05]
            if len(lats) >= 3:
                med = statistics.median(lats)
                for tr in fr["tracks"]:
                    if tr["_lat"] is not None:
                        tr["_lat"] -= med
        for tr in fr["tracks"]:
            tr["_aspect"] = aspect
            tr["_hcap"] = cfg["max_horizon"]
            if tr["_lat"] is not None:
                tr["_lat"] *= cfg["lat_gain"]


def predict(tr, horizon):
    """Predicted lateral offset at contact: (cx in image at current depth, metres or None)."""
    x1, y1, x2, y2 = tr["box"]
    u = (x1 + x2) / 2 - 0.5 + (tr["_lat"] or 0.0) * min(horizon, tr["_hcap"])
    h, w = y2 - y1, x2 - x1
    X = None
    if tr["cls"] in HEIGHT_M and y1 > EDGE and y2 < 1 - EDGE and h > 0:
        X = HEIGHT_M[tr["cls"]] * u * tr["_aspect"] / h
    elif tr["cls"] in WIDTH_M and x1 > EDGE and x2 < 1 - EDGE and w > 0:
        X = WIDTH_M[tr["cls"]] * u / w
    return 0.5 + u, X


def corridor_ok(tr, horizon, cfg):
    x1, _, x2, _ = tr["box"]
    v2_ok = x1 < fh.V2_CORRIDOR[1] and x2 > fh.V2_CORRIDOR[0]
    if cfg["filter"] == "v2":
        return v2_ok
    cxp, X = predict(tr, horizon)
    img_ok = abs(cxp - 0.5) <= cfg["img_half"]
    if cfg["filter"] == "img":
        return img_ok
    world_ok = abs(X) <= cfg["corridor_m"] if X is not None else img_ok
    return world_ok and (v2_ok or cfg["filter"] == "world")


def urgency(tr, cfg):
    if tr["cls"] not in fh.NAMES or tr["conf"] < 0.4:
        return None, None
    x1, y1, x2, y2 = tr["box"]
    if y2 - y1 < cfg["min_h"]:
        return None, None
    veh = tr["cls"] in fh.VEHICLES
    if tr["motion"] == "approaching" and tr["ttc_s"] is not None and tr["ttc_s"] < cfg["ttc"]:
        if (veh and cfg["vehicle_bypass"]) or corridor_ok(tr, tr["ttc_s"], cfg):
            return tr["ttc_s"], tr["ttc_s"]
    if tr["motion"].startswith("crossing") and y2 - y1 >= cfg["cross_h"] \
            and corridor_ok(tr, cfg["cross_horizon"], cfg):
        return cfg["cross_urgency"], cfg["cross_horizon"]
    return None, None


def side_of(tr, horizon, cfg):
    if cfg["side"] == "pred":
        cxp, X = predict(tr, horizon)
        if X is not None:
            return "left" if X < -cfg["side_m"] else "right" if X > cfg["side_m"] else "ahead"
    else:
        cxp = (tr["box"][0] + tr["box"][2]) / 2
    lo, hi = fh.V2_CENTRE
    return "left" if cxp < lo else "right" if cxp > hi else "ahead"


def band(u, cfg):
    return 2 if u < cfg["bands"][1] else 1 if u < cfg["bands"][0] else 0


class Voice:
    """Piper with every phrase synthesised up front. Speech starts SYNTH_S after the
    voice picks a phrase, a constant, so runs are repeatable: timing the real
    synthesis per call moved the v2 re-simulation between 10/29 and 12/29 on time."""

    # Piper (VITS) samples noise, so the same phrase comes out a few ms longer or
    # shorter each time and that alone moved scores; phrases are synthesised once
    # into PHRASE_DIR and reused.
    def __init__(self, length_scale, phrase_dir=PHRASE_DIR):
        self.dir = Path(phrase_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.length_scale = length_scale
        self.tts = None
        self.cache = {}
        for name in fh.NAMES.values():
            for verb in ("", " crossing"):
                for side in PAN:
                    self.get(f"{name}{verb} {side}.")

    def get(self, text):
        if text not in self.cache:
            path = self.dir / (text.lower().replace(" ", "_").strip(".") + ".wav")
            if not path.exists():
                if self.tts is None:
                    self.tts = lh.Tts(self.length_scale)
                self.tts.say(text, str(path))
            with wave.open(str(path)) as w:
                dur = w.getnframes() / w.getframerate()
            self.cache[text] = (dur, SYNTH_S, path)
        return self.cache[text], False

    def say(self, text, path):
        """fused_harness.speak interface; sleeps so its own timer sees SYNTH_S."""
        (dur, syn, src), _ = self.get(text)
        time.sleep(syn)
        shutil.copy(src, path)
        return dur


def simulate(frames, cfg, voice):
    """One walk through the clip. Returns (words, tones), both lists of dicts with
    status; spoken words and played tones carry start/end."""
    hist = collections.defaultdict(lambda: collections.deque(maxlen=cfg["window"]))
    worded = {}          # track id -> time a word was queued (once) / last word (v2)
    kind_last = {}       # class name -> last word time
    last_tone = {}
    pending, words, tones = [], [], []
    st = dict(voice_free=0.0, tone_free=0.0, last_text="", last_text_t=-99.0)

    def play_tone(t, c, kind):
        start = max(t, st["tone_free"])
        if cfg["single_channel"] and start < st["voice_free"]:
            start = st["voice_free"]
        e = dict(source="tone", ready=t, kind=kind, track=c["track"], cls=c["cls"],
                 side=c["side"], urgency=c["urgency"], band=band(c["urgency"], cfg),
                 win_start=c["win_start"], win_end=c["win_end"], X=c["X"])
        if start - t > cfg["tone_stale"]:
            e["status"] = "stale"
        else:
            e.update(status="tone", audio_start=start, audio_dur=cfg["tone_s"])
            st["tone_free"] = start + cfg["tone_s"] + cfg["tone_gap"]
            last_tone[c["track"]] = start
        tones.append(e)

    def drop(p, status):
        p["status"] = status
        words.append(p)
        if cfg["words"] == "once" and worded.get(p["track"]) == p["ready"]:
            worded.pop(p["track"])
        if kind_last.get(p["name"]) == p["ready"]:
            kind_last[p["name"]] = p["prev_kind"]

    def flush(now):
        while pending:
            T = max(st["voice_free"], min(p["ready"] for p in pending))
            if T > now:
                break
            fresh = []
            for p in [p for p in pending if p["ready"] <= T]:
                pending.remove(p)
                if T - p["ready"] > cfg["word_stale"]:
                    drop(p, "stale")
                else:
                    fresh.append(p)
            if not fresh:
                continue
            pick = min(fresh, key=lambda p: p["urgency"])
            for p in fresh:
                if p is not pick:
                    drop(p, "stale")
            if pick["answer"].lower() == st["last_text"] and T - st["last_text_t"] < SAME_TEXT_S:
                pick["status"] = "repeat"
                words.append(pick)
                if cfg["tones"]:
                    play_tone(T, pick, "repeat")
                continue
            (dur, syn, path), _ = voice.get(pick["answer"])
            start = T + syn
            if cfg["single_channel"]:
                start = max(start, st["tone_free"] - cfg["tone_gap"])
            pick.update(status="spoken", audio_start=start, audio_dur=dur, wav=str(path),
                        tts_s=syn, lag=start - pick["win_end"])
            words.append(pick)
            st["voice_free"] = start + dur
            st["last_text"], st["last_text_t"] = pick["answer"].lower(), pick["ready"]
            last_tone[pick["track"]] = start + dur

    for fr in frames:
        t = fr["t"]
        now = t + sum(fr.get("timing", {}).values()) / 1000.0
        flush(now)
        seen, cands = set(), []
        for tr in fr["tracks"]:
            u, horizon = urgency(tr, cfg)
            hist[tr["id"]].append(u)
            seen.add(tr["id"])
            if u is not None and sum(k is not None for k in hist[tr["id"]]) >= cfg["confirm"]:
                cands.append((u, horizon, tr))
        for tid in list(hist):
            if tid not in seen:
                hist[tid].append(None)
        if not cands:
            continue
        u, horizon, tr = min(cands, key=lambda c: c[0])
        tid, name = tr["id"], fh.NAMES[tr["cls"]]
        side = side_of(tr, horizon, cfg)
        verb = " crossing" if tr["motion"].startswith("crossing") else ""
        c = dict(source="fast", track=tid, cls=tr["cls"], name=name, side=side, urgency=u,
                 ready=now, win_start=max(0.0, t - cfg["window"] / 8), win_end=t,
                 answer=f"{name}{verb} {side}.", X=predict(tr, horizon)[1],
                 raw=json.dumps({k: v for k, v in tr.items() if not k.startswith("_")}))
        veh = tr["cls"] in fh.VEHICLES
        if cfg["words"] == "once":
            want = tid not in worded and (veh or now - kind_last.get(name, -99) > cfg["new_kind_s"]
                                          or u < cfg["word_ttc"])
        elif cfg["words"] == "v2":
            want = now - worded.get(tid, -99) >= fh.V2_TRACK_COOLDOWN_S
        else:
            want = False
        if want:
            c["prev_kind"] = kind_last.get(name, -99)
            worded[tid] = now
            kind_last[name] = now
            pending.append(c)
            busy = st["voice_free"] > now + 0.05 or len(pending) > 1
            if cfg["tones"] and (cfg["lead_tone"] == "always" or (cfg["lead_tone"] == "busy" and busy)):
                play_tone(now, c, "lead")
        elif cfg["tones"] and not any(p["track"] == tid for p in pending):
            if now - last_tone.get(tid, -99) >= cfg["tone_repeat"][band(u, cfg)]:
                play_tone(now, c, "repeat" if tid in last_tone else "new")
    flush(float("inf"))
    words.sort(key=lambda e: e["ready"])
    return words, tones


def tone_name(e):
    return f"[tone {e['side']}, {('low', 'mid', 'high')[e['band']]}]"


def cue_score(events, words, tones):
    """Cue view of the strict scorer, must_warn only. A cue is a spoken word or a
    played tone. It counts for an event when it starts no earlier than
    score_walk.earliest(event), ENDS by t_close, is on the event's side, and is
    about the event's class (word: names it; tone: the track that fired it has
    that class, which the walker does not hear). One cue credits one event."""
    mw = sorted((e for e in events if e["must_warn"]), key=lambda e: e["t_close"])
    cues = [dict(kind="word", t=w["t"], t_end=w["t_end"], answer=w["answer"],
                 side_ok=lambda e, w=w: sw.mentions(w["answer"], sw.SIDE_WORDS[e["side"]]),
                 cls_ok=lambda e, w=w: sw.mentions(w["answer"], e["words"])) for w in words]
    cues += [dict(kind="tone", t=x["audio_start"], t_end=x["audio_start"] + x["audio_dur"],
                  answer=tone_name(x), side_ok=lambda e, x=x: x["side"] == e["side"],
                  cls_ok=lambda e, x=x: sw.mentions(fh.NAMES[x["cls"]], e["words"])) for x in tones]
    used, per_event = set(), []
    for e in mw:
        ok = [c for c in cues if id(c) not in used and c["cls_ok"](e) and c["side_ok"](e)
              and sw.earliest(e) <= c["t"] and c["t_end"] <= e["t_close"]]
        first = min(ok, key=lambda c: (c["t"], c["kind"] != "word")) if ok else None
        if first:
            used.add(id(first))
        per_event.append(dict(event=e, first=first,
                              spare=e["t_close"] - first["t_end"] if first else None))
    rel_t = sum(1 for c in cues if c["kind"] == "tone" and any(
        c["cls_ok"](e) and sw.earliest(e) <= c["t"] <= e["t_close"] + sw.WINDOW_AFTER_CLOSE for e in mw))
    return per_event, rel_t


def score_run(events, words, tones, minutes):
    spoken = [dict(answer=w["answer"], t=w["audio_start"], t_end=w["audio_start"] + w["audio_dur"])
              for w in words if w["status"] == "spoken"]
    played = [x for x in tones if x["status"] == "tone"]
    pe, rel = sw.strict_score(events, spoken)
    cpe, rel_t = cue_score(events, spoken, played)
    return dict(pe=pe, rel=rel, cpe=cpe, rel_t=rel_t, n_words=len(spoken), n_tones=len(played),
                minutes=minutes)


def total(rows):
    pe = [p for r in rows for p in r["pe"]]
    cpe = [p for r in rows for p in r["cpe"]]
    n_w, n_t = sum(r["n_words"] for r in rows), sum(r["n_tones"] for r in rows)
    mins = sum(r["minutes"] for r in rows)
    hits = [p for p in pe if p["first"]]
    chits = [p for p in cpe if p["first"]]
    spare = [p["spare"] for p in chits]
    return dict(
        mw=len(pe), on_time=len(hits), on_time_side=sum(1 for p in hits if p["side_ok"]),
        word_prec=(sum(r["rel"] for r in rows), n_w),
        cued=len(chits), cued_word=sum(1 for p in chits if p["first"]["kind"] == "word"),
        cued_tone=sum(1 for p in chits if p["first"]["kind"] == "tone"),
        cue_spare=statistics.median(spare) if spare else None,
        tone_prec=(sum(r["rel_t"] for r in rows), n_t),
        utt_min=n_w / mins, tone_min=n_t / mins)


def load_clips():
    clips = []
    for lp in sorted(glob.glob("test_videos/labels/*.json")):
        stem = Path(lp).stem
        video = f"test_videos/{stem}.mp4"
        frames = [json.loads(line) for line in open(f"results/perception/{stem}.jsonl")]
        clips.append(dict(stem=stem, video=video, frames=frames, events=sw.load_labels(lp),
                          aspect=video_aspect(video), minutes=frames[-1]["t"] / 60))
    return clips


def video_aspect(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries",
                          "stream=width,height", "-of", "csv=p=0", path],
                         capture_output=True, text=True, check=True).stdout.split(",")
    return int(out[0]) / int(out[1])


def run_v3(clips, cfg, voice):
    rows, sims = [], []
    for c in clips:
        frames = json.loads(json.dumps(c["frames"]))
        annotate(frames, c["aspect"], cfg)
        words, tones = simulate(frames, cfg, voice)
        rows.append(score_run(c["events"], words, tones, c["minutes"]))
        sims.append((words, tones))
    return rows, sims


def run_v2(clips, voice):
    """The unmodified v2 code path (fused_harness candidates + speaker)."""
    rows = []
    tmp = Path(tempfile.mkdtemp())
    for c in clips:
        cands = fh.speak(fh.fast_candidates_v2(c["frames"]), voice, tmp, fh.V2_FAST_STALE_S)
        rows.append(score_run(c["events"], cands, [], c["minutes"]))
    return rows


def run_logged_v2(clips):
    rows = []
    for c in clips:
        spoken, _ = sw.load_log(f"results/live/{c['stem']}_fastonly2/log.csv")
        ws = [dict(answer=r["answer"], status="spoken", audio_start=r["t"],
                   audio_dur=r["t_end"] - r["t"]) for r in spoken]
        rows.append(score_run(c["events"], ws, [], c["minutes"]))
    return rows


def fmt_row(name, s):
    f = lambda a, b: f"{a}/{b}"
    pct = lambda a, b: f"{a}/{b} ({100 * a / b:.0f}%)" if b else "n/a"
    return (f"| {name} | {f(s['on_time'], s['mw'])} | {f(s['on_time_side'], s['mw'])} | "
            f"{pct(*s['word_prec'])} | {s['utt_min']:.1f} | {f(s['cued'], s['mw'])} | "
            f"{s['cued_word']} + {s['cued_tone']} | {sw.num(s['cue_spare'])} | "
            f"{pct(*s['tone_prec'])} | {s['tone_min']:.1f} | {s['utt_min'] + s['tone_min']:.1f} |")


HEAD = ("| variant | words on time | words on time, side right | word precision | utt/min | "
        "cued on time, side right | by word + by tone | cue spare median (s) | tone precision | "
        "tones/min | sounds/min |\n|---|---|---|---|---|---|---|---|---|---|---|")

VARIANTS = [
    ("v3 recommended (BASE)", {}),
    ("v3 words only, no tones", dict(tones=0)),
    ("v3 tones over speech off (single channel)", dict(single_channel=1)),
    ("v3 no corridor filter (v2 trigger: box overlaps 0.25 to 0.75)", dict(filter="v2")),
    ("v3 no corridor filter, v2 side", dict(filter="v2", side="v2")),
    ("v3 v2 side rule", dict(side="v2")),
    ("v3 image corridor (predicted centre in 0.25 to 0.75)", dict(filter="img")),
    ("v3 world corridor and box overlaps corridor", dict(filter="world_v2")),
    ("v3 corridor 0.8 m", dict(corridor_m=0.8)),
    ("v3 corridor 1.2 m", dict(corridor_m=1.2)),
    ("v3 corridor 2.0 m", dict(corridor_m=2.0)),
    ("v3 no extrapolation (horizon 0)", dict(max_horizon=0.0)),
    ("v3 extrapolate over full TTC", dict(max_horizon=4.0)),
    ("v3 no yaw compensation", dict(yaw_comp=0)),
    ("v3 not once per track (v2 4 s word cooldown) + tones", dict(words="v2")),
    ("v3 lead tone always", dict(lead_tone="always")),
    ("v3 no lead tone", dict(lead_tone="never")),
    ("v3 tone gap 0.35 s", dict(tone_gap=0.35)),
    ("v3 tone gap 0.35 s, repeats 1.5/1.0/0.6 s", dict(tone_gap=0.35, tone_repeat=(1.5, 1.0, 0.6))),
    ("v3 repeat tones only under 1.5 s TTC", dict(tone_repeat=(99.0, 99.0, 1.0))),
    ("v3 new kind after 4 s", dict(new_kind_s=4.0)),
    ("v3 new kind after 15 s", dict(new_kind_s=15.0)),
    ("v3 word TTC 2.5 s", dict(word_ttc=2.5)),
    ("v3 TTC 5 s", dict(ttc=5.0)),
    ("v3 side dead zone 0.15 m", dict(side_m=0.15)),
    ("v3 side dead zone 0.40 m", dict(side_m=0.40)),
]


GRIDS = [
    {"yaw_comp": [0, 1], "corridor_m": [0.8, 1.2, 1.6, 2.0, 3.0], "side": ["v2", "pred"],
     "max_horizon": [4.0, 2.0, 1.0], "tone_gap": [0.10, 0.35, 0.85]},
    {"yaw_comp": [1], "side": ["pred"], "corridor_m": [1.6, 2.0, 2.5],
     "max_horizon": [1.0, 0.5, 0.0], "tone_gap": [0.35, 0.85],
     "tone_repeat": [(1.5, 1.0, 0.6), (3.0, 2.0, 1.0), (99.0, 99.0, 0.6)], "word_ttc": [1.5, 2.5]},
]


def cmd_grid(args):
    import itertools
    clips = load_clips()
    voice = Voice(fh.V2_LENGTH_SCALE)
    lines = ["# Walk v3 grid", "",
             "Same 4 clips and labels the settings are judged on, so the best row is tuned "
             "to this set. Other settings as BASE in scripts/walk_v3.py. Columns as in "
             "results/walk_v3.md.", ""]
    for n, grid in enumerate(GRIDS, 1):
        lines += [f"## Grid {n}", "",
                  "| " + " | ".join(grid) + HEAD.split("\n")[0].replace("| variant ", ""),
                  "|" + "---|" * (len(grid) + 10)]
        for combo in itertools.product(*grid.values()):
            cfg = dict(BASE, **dict(zip(grid, combo)))
            s = total(run_v3(clips, cfg, voice)[0])
            lines.append("| " + " | ".join(str(v) for v in combo) + fmt_row("", s)[3:])
            print(lines[-1], flush=True)
        lines.append("")
    Path(args.out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {args.out}")


def cmd_eval(args):
    clips = load_clips()
    voice = Voice(fh.V2_LENGTH_SCALE)
    lines = [HEAD]
    lines.append(fmt_row("v2 logged run (results/live/*_fastonly2)", total(run_logged_v2(clips))))
    lines.append(fmt_row("v2 re-simulated (fused_harness code, cached Piper)", total(run_v2(clips, voice))))
    detail = None
    for name, over in VARIANTS:
        cfg = dict(BASE, **over)
        rows, sims = run_v3(clips, cfg, voice)
        lines.append(fmt_row(name, total(rows)))
        print(lines[-1], flush=True)
        if not over:
            detail = (rows, sims)
    per_clip = [HEAD]
    for c, r in zip(clips, detail[0]):
        per_clip.append(fmt_row(c["stem"], total([r])))
    ev_lines = []
    for c, r in zip(clips, detail[0]):
        ev_lines += [f"### {c['stem']}", "",
                     "| id | cls | side | t_close | strict word | cue (kind, time, what) | cue spare |",
                     "|---|---|---|---|---|---|---|"]
        for p, cp in zip(r["pe"], r["cpe"]):
            e, f, cf = p["event"], p["first"], cp["first"]
            ev_lines.append("| " + " | ".join([
                e["id"], e["cls"], e["side"], f"{e['t_close']:.1f}",
                f"{f['t']:.2f}-{f['t_end']:.2f} {f['answer']}{'' if p['side_ok'] else ' (side wrong)'}" if f else "miss",
                f"{cf['kind']} {cf['t']:.2f}-{cf['t_end']:.2f} {cf['answer']}" if cf else "miss",
                sw.num(cp["spare"])]) + " |")
        ev_lines.append("")
    Path(args.out).write_text(REPORT.format(
        table="\n".join(lines), per_clip="\n".join(per_clip), events="\n".join(ev_lines),
        base=json.dumps(BASE)), encoding="utf-8")
    print(f"wrote {args.out}")


REPORT = """# Walk mode v3 ("cane companion"): scores

Generated by `python scripts/walk_v3.py eval` (maya-engine image, no GPU) from
the precomputed tracks in `results/perception/*.jsonl` and the hand labels in
`test_videos/labels/*.json`. 4 clips, 29 must_warn events, 2.0 minutes.

**Caveat.** Every threshold here was chosen and scored on the same 4 clips, by
one annotator, so these numbers are optimistic. They need new clips to confirm.

Columns:
- words on time / side right / word precision / utt/min: the original strict
  table of `scripts/score_walk.py`, spoken words only. Comparable with v2.
- cued on time, side right: cue view. A spoken word or a played tone counts
  when it starts no earlier than the strict scorer's earliest time, ENDS by
  t_close, is on the labelled side, and is about the event's class (a tone
  carries no class word; the track that fired it must have the class). One cue
  credits one event. Split into credited by a word and by a tone.
- tone precision: tones whose track class matches some must_warn event between
  its earliest time and t_close + 1 s, over all tones.
- sounds/min = utterances per minute + tones per minute.

{table}

## v3 recommended, per clip

{per_clip}

## v3 recommended, per event (must_warn)

{events}

Recommended settings (BASE): `{base}`

Notes:
- Lateral position at contact uses the class height (or width when the box is cut by the top or bottom edge) to turn the image offset into metres; camera yaw is the per-frame median lateral rate over all tracks.
- The cue view still matches by class, not identity: in a crowd a tone about one person can be credited to another person on the same side.
- Tones play over speech unless single_channel=1. Word timing uses a fixed 0.05 s synthesis delay and phrases cached in results/live/phrases_v3/.
"""


def tone_wav(side, b, cfg):
    n = int(SR * cfg["tone_s"])
    t = np.arange(n) / SR
    f = TONE_HZ[b]
    x = np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t)
    ramp = int(SR * 0.01)
    env = np.ones(n)
    env[:ramp] = 0.5 - 0.5 * np.cos(np.pi * np.arange(ramp) / ramp)
    env[-ramp:] = env[:ramp][::-1]
    x = 0.45 * x * env / 1.3
    a = (PAN[side] + 1) * np.pi / 4
    return np.stack([x * np.cos(a), x * np.sin(a)], axis=1)


def write_wav(path, stereo):
    pcm = (np.clip(stereo, -1, 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def read_mono(path):
    with wave.open(str(path)) as w:
        assert w.getframerate() == SR and w.getsampwidth() == 2, path
        x = np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(np.float32) / 32767
        return x.reshape(-1, w.getnchannels()).mean(axis=1)


def render(video, dur, words, tones, cfg, out_dir, td):
    tone_dir = out_dir / "tones"
    tone_dir.mkdir(exist_ok=True)
    bank = {}
    for side in PAN:
        for b in range(3):
            bank[side, b] = tone_wav(side, b, cfg)
            write_wav(tone_dir / f"{side}_{('low', 'mid', 'high')[b]}.wav", bank[side, b])
    mix = np.zeros((int(SR * dur) + SR, 2), np.float32)
    for w in words:
        x = read_mono(w["wav"])
        i = int(w["audio_start"] * SR)
        seg = mix[i:i + len(x)]
        seg += x[:len(seg), None] * 0.9
    for e in tones:
        x = bank[e["side"], e["band"]]
        i = int(e["audio_start"] * SR)
        seg = mix[i:i + len(x)]
        seg += x[:len(seg)]
    track = Path(td) / "track.wav"
    write_wav(track, mix[:int(SR * dur)])

    items = [(w["audio_start"], w["audio_start"] + w["audio_dur"] + 1.0, w["answer"]) for w in words]
    items += [(e["audio_start"], e["audio_start"] + 0.4,
               {"left": "<< ", "right": "", "ahead": "^ "}[e["side"]] + "beep"
               + {"left": "", "right": " >>", "ahead": " ^"}[e["side"]]
               + f" ({e['urgency']:.1f}s)") for e in tones]
    items.sort()
    srt = Path(td) / "captions.srt"
    with open(srt, "w") as f:
        for i, (s, e, text) in enumerate(items):
            e = min(e, dur)
            if e > s:
                f.write(f"{i + 1}\n{lh.srt_time(s)} --> {lh.srt_time(e)}\n{text}\n\n")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", video, "-i", str(track)]
    vf = f"[0:v]subtitles={srt}:force_style='FontSize=16,Outline=2,MarginV=20'[vout]"
    if lh.has_audio(video):
        # A mono source track would otherwise make amix output mono and lose the pan.
        af = "[0:a]volume=0.2,aformat=channel_layouts=stereo[bg];[1:a][bg]amix=inputs=2:normalize=0:duration=first[aout]"
        cmd += ["-filter_complex", vf + ";" + af, "-map", "[vout]", "-map", "[aout]"]
    else:
        cmd += ["-filter_complex", vf, "-map", "[vout]", "-map", "1:a"]
    cmd += ["-t", f"{dur:.2f}", "-c:v", "libx264", "-preset", "veryfast", "-c:a", "aac",
            str(out_dir / "annotated.mp4")]
    subprocess.run(cmd, check=True)


def parse_sets(sets):
    over = {}
    for s in sets or []:
        k, v = s.split("=", 1)
        if k not in BASE:
            raise SystemExit(f"unknown setting {k}")
        d = BASE[k]
        over[k] = (tuple(float(x) for x in v.split(",")) if isinstance(d, tuple)
                   else type(d)(v) if not isinstance(d, str) else v)
    return over


def cmd_run(args):
    cfg = dict(BASE, **parse_sets(args.set))
    stem = Path(args.video).stem
    frames = [json.loads(line) for line in open(f"results/perception/{stem}.jsonl")]
    annotate(frames, video_aspect(args.video), cfg)
    voice = Voice(fh.V2_LENGTH_SCALE)
    words, tones = simulate(frames, cfg, voice)
    out_dir = Path(args.out) / f"{stem}_{args.tag}"
    (out_dir / "wav").mkdir(parents=True, exist_ok=True)
    spoken = [w for w in words if w["status"] == "spoken"]
    played = [x for x in tones if x["status"] == "tone"]
    for i, w in enumerate(spoken):
        dst = out_dir / "wav" / f"{i:03d}.wav"
        shutil.copy(w["wav"], dst)
        w["wav"] = str(dst)
    dur = lh.ffprobe_duration(args.video)
    with tempfile.TemporaryDirectory() as td:
        render(args.video, dur, spoken, played, cfg, out_dir, td)

    rows = sorted(words + tones, key=lambda e: e["ready"])
    for e in rows:
        if e["source"] == "tone":
            e["answer"] = tone_name(e)
    keys = ["idx", "source", "kind", "track", "cls", "side", "urgency", "X", "win_start", "win_end",
            "ready", "status", "audio_start", "audio_dur", "lag", "answer", "raw"]
    with open(out_dir / "log.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        for i, e in enumerate(rows):
            e["idx"] = i
            w.writerow({k: (round(v, 3) if isinstance(v, float) else v) for k, v in e.items()})
    lp = Path(f"test_videos/labels/{stem}.json")
    score_line = ""
    if lp.exists():
        s = total([score_run(sw.load_labels(lp), words, tones, frames[-1]["t"] / 60)])
        score_line = HEAD + "\n" + fmt_row(stem, s) + "\n\n"
    count = collections.Counter((e["source"], e["status"]) for e in rows)
    with open(out_dir / "summary.md", "w", encoding="utf-8") as f:
        f.write(f"# Walk v3: {Path(args.video).name}\n\nSettings: `{json.dumps(cfg)}`\n\n")
        f.write(f"By source and status: {dict(count)}\n\n{score_line}")
        f.write("| Sound | Saw (s) | Plays at (s) | What |\n|---|---|---|---|\n")
        for e in rows:
            if e["status"] in ("spoken", "tone"):
                f.write(f"| {'word' if e['source'] == 'fast' else 'tone'} | {e['win_end']:.1f} | "
                        f"{e['audio_start']:.2f} | {e['answer']} |\n")
    print(f"wrote {out_dir}: {len(spoken)} words, {len(played)} tones")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("eval")
    e.add_argument("--out", default="results/walk_v3.md")
    g = sub.add_parser("grid")
    g.add_argument("--out", default="results/walk_v3_grid.md")
    r = sub.add_parser("run")
    r.add_argument("--video", required=True)
    r.add_argument("--set", action="append", help="key=value override of BASE")
    r.add_argument("--tag", default="v3")
    r.add_argument("--out", default="results/live")
    args = ap.parse_args()
    {"eval": cmd_eval, "grid": cmd_grid, "run": cmd_run}[args.cmd](args)


if __name__ == "__main__":
    main()
