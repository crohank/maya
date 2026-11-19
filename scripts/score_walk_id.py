"""Identity-matched walk scorer for SANPO clips (instance masks + perception tracks).

The class scorer (scripts/score_walk.py) credits any "Person ..." in a crowd. This
one credits a warning only when the track that triggered it is the labelled
instance, found by comparing perception boxes with SANPO instance masks.

Usage (maya-engine, CPU, no network), from the repo root:
  python -I -B scripts/score_walk_id.py cache            # mask grids, once per clip
  python -I -B scripts/score_walk_id.py check            # box-mask alignment report
Scoring is called from scripts/walk_v4.py (score_clip).

Coordinates: masks are 2208x1242 PNGs (source frames), clips 1280x720 scaled from
the same frames (scripts/sanpo_fetch.py: ffmpeg scale=1280:720, no crop), boxes are
normalised to the clip. Both are 16:9, so a normalised box maps straight onto the
mask after resampling to the 320x180 grid that scripts/sanpo_events.py uses.
Time: mask NNNNNN.png is clip frame N (t = N / meta fps); perception frames carry
the clip frame time, so frame index = round(t * fps). `check` measures both.

Rules:
- Box-instance match per perception frame: rect IoU = mask pixels inside the box /
  (box pixels + mask pixels - mask pixels inside the box), over SANPO pedestrian,
  rider and vehicle instances. Each box takes its best instance if IoU >= MIN_IOU.
  A whole person mask fills about half its box, so a perfect match scores 0.5 to 0.7.
- Tracks of an instance over a time window: tracks assigned to it in at least
  MIN_FRAMES frames of the window (an id switch gives two tracks).
- must_warn event (merged crowd events keep every member): a warning, word or tone,
  credits the event when its triggering track is a track of one member over
  [earliest - 1, member t_close + 0.5], it starts no earlier than
  score_walk.earliest(event) and it ENDS by that member's t_close. One warning
  credits one event (events in t_close order, earliest warning first, a word
  before a tone at the same time).
- Side right (first cue): the credited warning's side equals the label side.
  Side right (last cue): the last on-time warning about the event before it
  passes (what the walker heard most recently) has the label side.
  Side right (any cue): a second pass that also requires the side to match.
- Precision: a warning is relevant when its track is a track of some instance
  that comes within NEAR_M in the corridor (|X| <= 1.0 m, from
  data/sanpo/labels/<stem>_tracks.json), with the warning starting in
  [t_ref - 5, t_ref + 1] (t_ref = the instance's nearest corridor frame).
  Precision over all warnings. Must-precision: relevant to a must_warn member.
"""
import collections
import glob
import json
import math
import sys
from pathlib import Path

import numpy as np

DATA = Path("data/sanpo")
CACHE = Path("results/sanpo/walk_v4_cache")
GRID_W, GRID_H = 320, 180
SEM = {12: "person", 13: "bicycle", 21: "car"}
SEM_OF = {"pedestrian": 12, "rider": 13, "vehicle": 21}
MIN_IOU = 0.25
MIN_FRAMES = 2
NEAR_M = 5.0
CORRIDOR_M = 1.0
PREC_BEFORE, PREC_AFTER = 5.0, 1.0
LABEL_GRID_S, EARLY_WARN_S = 0.5, 3.0


def earliest(e):
    return min(e["t_start"] - LABEL_GRID_S, e["t_close"] - EARLY_WARN_S)


def build_cache(stem):
    from PIL import Image
    seg = DATA / "seg" / stem
    paths = sorted(glob.glob(str(seg / "masks" / "*.png")))
    n = int(Path(paths[-1]).stem) + 1
    keys = {0: 0}
    lab = np.zeros((n, GRID_H, GRID_W), np.uint16)
    have = np.zeros(n, bool)
    for p in paths:
        f = int(Path(p).stem)
        a = np.array(Image.open(p).convert("RGB"))
        h, w = a.shape[:2]
        rows = ((np.arange(GRID_H) + 0.5) * h / GRID_H).astype(int)
        cols = ((np.arange(GRID_W) + 0.5) * w / GRID_W).astype(int)
        a = a[rows][:, cols].astype(np.int64)
        sem, inst = a[..., 0], a[..., 1] * 256 + a[..., 2]
        key = np.where(np.isin(sem, list(SEM)), sem * 65536 + inst, 0)
        out = np.zeros(key.shape, np.uint16)
        for k in np.unique(key):
            if k:
                out[key == k] = keys.setdefault(int(k), len(keys))
        lab[f], have[f] = out, True
    table = np.array(sorted(keys, key=keys.get), np.int64)
    CACHE.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(CACHE / f"{stem}.npz", lab=lab, have=have, keys=table)
    return lab, have, table


def load_cache(stem):
    p = CACHE / f"{stem}.npz"
    if not p.exists():
        return build_cache(stem)
    z = np.load(p)
    return z["lab"], z["have"], z["keys"]


def box_px(box):
    x1, y1, x2, y2 = box
    c0, c1 = int(math.floor(x1 * GRID_W)), int(math.ceil(x2 * GRID_W))
    r0, r1 = int(math.floor(y1 * GRID_H)), int(math.ceil(y2 * GRID_H))
    return max(0, r0), min(GRID_H, r1), max(0, c0), min(GRID_W, c1)


def frame_ious(lab_f, box, nkeys):
    """IoU of the box with every instance key in one mask frame."""
    r0, r1, c0, c1 = box_px(box)
    area = np.bincount(lab_f.ravel(), minlength=nkeys)
    if r1 <= r0 or c1 <= c0:
        return np.zeros(nkeys)
    inter = np.bincount(lab_f[r0:r1, c0:c1].ravel(), minlength=nkeys).astype(float)
    barea = (r1 - r0) * (c1 - c0)
    iou = inter / np.maximum(1, barea + area - inter)
    iou[0] = 0.0
    return iou


class Clip:
    """Box-instance assignments for one SANPO clip."""

    def __init__(self, stem, frames, offset=0):
        self.stem = stem
        self.meta = json.load(open(DATA / "seg" / stem / "meta.json"))
        self.fps = self.meta["fps"]
        lab, have, keys = load_cache(stem)
        self.keys = keys
        self.assign = []          # (t, track id, cls, (sem, inst) or None, iou)
        self.best = []            # best IoU per box, for the alignment check
        for fr in frames:
            f = int(round(fr["t"] * self.fps)) + offset
            if not (0 <= f < len(have)) or not have[f]:
                continue
            for tr in fr["tracks"]:
                iou = frame_ious(lab[f], tr["box"], len(keys))
                k = int(np.argmax(iou))
                self.best.append(float(iou[k]))
                inst = (int(keys[k]) >> 16, int(keys[k]) & 0xFFFF) if iou[k] >= MIN_IOU else None
                self.assign.append((fr["t"], tr["id"], tr["cls"], inst, float(iou[k])))
        self.by_inst = collections.defaultdict(list)
        for t, tid, _, inst, _ in self.assign:
            if inst:
                self.by_inst[inst].append((t, tid))

    def tracks_of(self, inst, a, b):
        n = collections.Counter(tid for t, tid in self.by_inst.get(inst, []) if a <= t <= b)
        return {tid for tid, c in n.items() if c >= MIN_FRAMES}

    def inst_of(self, tid, t, half=1.0):
        """Instance a track is assigned to most often within t +- half (or None)."""
        n = collections.Counter(inst for tt, i, _, inst, _ in self.assign
                                if i == tid and inst and abs(tt - t) <= half)
        return n.most_common(1)[0][0] if n else None


def members(e):
    """(sem, inst, t_close) of every instance merged into a label event, from its note."""
    note = e["note"]
    head = note.split("SANPO ", 1)[1].split(",", 1)[0].split()
    sem = SEM_OF[head[0]]
    out = [(sem, int(head[2]), e["t_close"])]
    if "others: " in note:
        for part in note.split("others: ", 1)[1].split(", "):
            w = part.split()
            out.append((sem, int(w[1]), float(w[3].rstrip("s"))))
    return out


def relevant_instances(stem):
    tj = json.load(open(DATA / "labels" / f"{stem}_tracks.json"))
    inv = {v: k for k, v in SEM.items()}
    out = []
    for tr in tj["tracks"]:
        t, z, x = np.array(tr["t"]), np.array(tr["z"]), np.array(tr["x"])
        inside = np.abs(x) <= CORRIDOR_M
        if not inside.any():
            continue
        k = int(np.argmin(np.where(inside, z, np.inf)))
        if z[k] <= NEAR_M:
            out.append(((inv[tr["cls"]], tr["inst"]), float(t[k]), float(z[k])))
    return out


def score_clip(clip, events, warnings):
    """warnings: dicts with kind (word|tone), t, t_end, track, side.
    Returns per_event (must_warn), precision counts and a reason count per warning."""
    mw = sorted((e for e in events if e["must_warn"]), key=lambda e: e["t_close"])
    ev_tracks = []
    for e in mw:
        mem = []
        for sem, inst, tc in members(e):
            mem.append(((sem, inst), tc, clip.tracks_of((sem, inst), earliest(e) - 1.0, tc + 0.5)))
        ev_tracks.append(mem)

    def credit(need_side):
        used, res = set(), []
        for e, mem in zip(mw, ev_tracks):
            ok = [w for w in warnings if id(w) not in used and w["t"] >= earliest(e)
                  and (not need_side or w["side"] == e["side"])
                  and any(w["track"] in trs and w["t_end"] <= tc for _, tc, trs in mem)]
            first = min(ok, key=lambda w: (w["t"], w["kind"] != "word")) if ok else None
            if first:
                used.add(id(first))
            deadline = max(tc for _, tc, _ in mem)
            res.append(dict(event=e, first=first, matched=sorted(set().union(*[m[2] for m in mem])),
                            spare=(min(tc for _, tc, trs in mem if first["track"] in trs)
                                   - first["t_end"]) if first else None, deadline=deadline))
        return res

    per_event = credit(False)
    per_side = credit(True)
    for p, q, mem in zip(per_event, per_side, ev_tracks):
        e = p["event"]
        p["side_first"] = bool(p["first"] and p["first"]["side"] == e["side"])
        p["side_any"] = q["first"] is not None
        about = [w for w in warnings if w["t"] >= earliest(e)
                 and any(w["track"] in trs and w["t_end"] <= tc for _, tc, trs in mem)]
        p["last"] = max(about, key=lambda w: w["t_end"]) if about else None
        p["side_last"] = bool(p["first"] and p["last"]["side"] == e["side"])
    rel = relevant_instances(clip.stem)
    rel_tracks = [(inst, tr, clip.tracks_of(inst, tr - PREC_BEFORE - 1.0, tr + PREC_AFTER))
                  for inst, tr, _ in rel]
    must_sets = [(e, set().union(*[m[2] for m in mem])) for e, mem in zip(mw, ev_tracks)]
    reasons = collections.Counter()
    n_rel = n_must = 0
    for w in warnings:
        hit = any(w["track"] in trs and tr - PREC_BEFORE <= w["t"] <= tr + PREC_AFTER
                  for _, tr, trs in rel_tracks)
        must = any(w["track"] in trs and earliest(e) <= w["t"] <= e["t_close"] + 1.0
                   for e, trs in must_sets)
        n_rel += hit
        n_must += must
        w["relevant"], w["must"] = hit, must
        if hit:
            reasons["relevant"] += 1
        elif clip.inst_of(w["track"], w.get("t_trig", w["t"])) is None:
            reasons["track matches no mask instance"] += 1
        elif any(w["track"] in trs for _, _, trs in rel_tracks):
            reasons["near instance, outside its time window"] += 1
        else:
            reasons["instance never within 5 m in corridor"] += 1
    return dict(per_event=per_event, n=len(warnings), rel=n_rel, must=n_must, reasons=reasons)


def cmd_cache():
    for seg in sorted((DATA / "seg").iterdir()):
        lab, have, keys = build_cache(seg.name)
        print(f"{seg.name}: {int(have.sum())} mask frames, {len(keys) - 1} instances", flush=True)


def cmd_check():
    """Alignment: median best IoU per box with mask frame offsets -2..+2, and a
    horizontal mirror of the boxes as a no-alignment reference."""
    lines = ["| clip | " + " | ".join(f"offset {o:+d}" for o in (-2, -1, 0, 1, 2))
             + " | mirrored boxes | boxes matched at offset 0 |", "|---" * 7 + "|"]
    for p in sorted(glob.glob("results/sanpo/perception/sanpo_*.jsonl")):
        stem = Path(p).stem
        frames = [json.loads(l) for l in open(p)]
        meds = []
        for o in (-2, -1, 0, 1, 2):
            c = Clip(stem, frames, o)
            meds.append(np.median(c.best) if c.best else float("nan"))
            if o == 0:
                matched = sum(1 for a in c.assign if a[3]) / max(1, len(c.assign))
        mir = json.loads(json.dumps(frames))
        for fr in mir:
            for tr in fr["tracks"]:
                x1, y1, x2, y2 = tr["box"]
                tr["box"] = [1 - x2, y1, 1 - x1, y2]
        cm = Clip(stem, mir, 0)
        lines.append(f"| {stem} | " + " | ".join(f"{m:.2f}" for m in meds)
                     + f" | {np.median(cm.best):.2f} | {100 * matched:.0f}% |")
        print(lines[-1], flush=True)
    return lines


if __name__ == "__main__":
    {"cache": cmd_cache, "check": cmd_check}[sys.argv[1]]()
