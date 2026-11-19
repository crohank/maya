"""Automatic walk-event labels for SANPO clips from depth + panoptic masks.

Usage (maya-engine, CPU, no network):
  python -I scripts/sanpo_events.py [--stems a,b] [--corridor 1.0] [--near 3.0] [--sheet]
Reads data/sanpo/seg/<stem>/{masks/*.png,depth.npz,meta.json} and data/sanpo/index.json,
writes data/sanpo/labels/<stem>.json in the test_videos/labels schema plus
data/sanpo/labels/<stem>_tracks.json (per-instance distance series, for checking).

Rule (docs/sanpo_eval.md has the reasoning, limits and what was checked by eye):
- Instances of SANPO classes pedestrian (12), rider (13) and vehicle (21), keyed by
  (class, instance id); SANPO instance ids are temporally consistent within a session.
- Per frame: mask resampled to the 320x180 depth grid and eroded by 1 px; Z = median
  CREStereo depth over it, X = median of (u - cx) / fx * Z. Median filter over 3 frames.
  Frames whose visible mask height in metres does not fit Z are dropped.
- Corridor |X| <= 1.0 m; t_close = frame of minimum Z among corridor frames.
- Closing: Z fell by at least 1.0 m over the 3 s before t_close, with at least 0.6 s
  of history. A person walking ahead at the walker's pace does not close.
- must_warn: corridor Z < 3 m and closing; vehicles also need own speed >= 1.5 m/s
  (closing rate minus walker speed from SANPO poses, combined with lateral rate).
  must_warn events of one class and side within 1 s are merged.
  Kept as must_warn false: closing at 3 to 5 m, passing within 2 m outside the
  corridor, under 3 m but not closing, parked vehicles.
- t_start: first frame with Z <= 10 m, no earlier than t_close - 2.5 s (--approach).
  Hand-labelled must_warn events have a median t_close - t_start of 1.5 s, so the
  strict scorer opens at t_close - 3 for both sets.
- side: mask centroid at t_close, frame thirds (as test_videos/labels/README.md).
"""
import argparse
import glob
import json
import os
from pathlib import Path

import numpy as np
from PIL import Image

DATA = Path("data/sanpo")
CLS = {12: "person", 13: "bicycle", 21: "car"}
# The harness says "Truck"/"Bus"/"Motorbike"; SANPO has one vehicle class. A
# rider is also detected as a person, and "Person ahead" about a cyclist still
# warns, so riders accept person words.
KEYWORDS = {12: [], 13: ["person", "rider", "motorbike", "scooter"],
            21: ["truck", "bus", "pickup", "van", "motorbike"]}
GRID_W, GRID_H = 320, 180
APPROACH_S = 2.5
ORDER = ["id", "t_start", "t_close", "cls", "side", "dist_bucket", "motion", "must_warn",
         "keywords", "note"]


def intrinsics(sid):
    for r in json.load(open(DATA / "index.json")):
        if r["sid"] == sid:
            d = r["desc"]
            cam = d["session_camera_details"][d["session_camera_location"].index("camera_chest")]
            p = cam["left_camera_params"]
            s = GRID_W / p["image_width"]
            return p["fx"] * s, p["cx"] * s, cam["model"], p["h_fov"]
    raise KeyError(sid)


def erode(m):
    e = m.copy()
    e[1:] &= m[:-1]
    e[:-1] &= m[1:]
    e[:, 1:] &= m[:, :-1]
    e[:, :-1] &= m[:, 1:]
    return e


def medfilt3(a):
    if len(a) < 3:
        return a
    p = np.concatenate([a[:1], a, a[-1:]])
    return np.median(np.stack([p[:-2], p[1:-1], p[2:]]), axis=0)


def instance_series(seg, fx, cx):
    meta = json.load(open(seg / "meta.json"))
    dz = np.load(seg / "depth.npz")
    depth, dframes = dz["depth"].astype(np.float32), list(dz["frame"])
    dmap = {int(f): i for i, f in enumerate(dframes)}
    us = (np.arange(GRID_W) - cx) / fx
    series = {}
    for mp in sorted(glob.glob(str(seg / "masks" / "*.png"))):
        f = int(Path(mp).stem)
        if f not in dmap:
            continue
        a = np.array(Image.open(mp).convert("RGB"))
        h, w = a.shape[:2]
        rows = ((np.arange(GRID_H) + 0.5) * h / GRID_H).astype(int)
        cols = ((np.arange(GRID_W) + 0.5) * w / GRID_W).astype(int)
        a = a[rows][:, cols].astype(np.int32)
        sem, inst = a[..., 0], a[..., 1] * 256 + a[..., 2]
        d = depth[dmap[f]]
        valid = (d > 0.2) & (d < 80)
        for c in CLS:
            cm = sem == c
            if not cm.any():
                continue
            for i in np.unique(inst[cm]):
                full = cm & (inst == i)
                m = full & valid
                if int(m.sum()) < 12:
                    continue
                # Depth at mask borders mixes in the occluder or the background.
                core = erode(m)
                m2 = core if core.sum() >= 12 else m
                z = d[m2]
                zc = float(np.median(z))
                x = float(np.median(us[np.nonzero(m2)[1]] * z))
                ys, xs = np.nonzero(full)
                series.setdefault((c, int(i)), []).append(
                    (f / meta["fps"], zc, x, float(xs.mean() / GRID_W), int(ys.min()), int(ys.max()),
                     int(full.sum())))
    return meta, series


def plausible(z, y0, y1, fx):
    """Visible mask height in metres must fit the depth: at least 0.4 m (or half the
    frame's vertical extent at that depth, for objects cut by the frame), at most 4 m."""
    h = (y1 - y0 + 1) / fx * z
    extent = GRID_H / fx * z
    return (h >= np.minimum(0.4, 0.5 * extent)) & (h <= 4.0)


def ego_speed(seg, meta):
    """Walker speed (m/s) at clip time t from SANPO camera positions, over +-0.5 s."""
    p = seg / "poses.csv"
    if not p.exists():
        return None
    rows = [r.split(",") for r in p.read_text().splitlines()[1:]]
    pos = np.array([[float(r[1]), float(r[2]), float(r[3])] for r in rows])
    src_fps = meta["fps"] * meta.get("step", 1)
    h = int(round(src_fps / 2))

    def at(t):
        j = meta["start_frame"] + int(round(t * src_fps))
        a, b = max(0, j - h), min(len(pos) - 1, j + h)
        return float(np.linalg.norm(pos[b] - pos[a]) / max(1e-6, (b - a) / src_fps))
    return at


def events_for(series, fx, corridor, near, ego=None, approach=APPROACH_S):
    events, tracks = [], []
    for (c, i), rows in series.items():
        rows.sort()
        t = np.array([r[0] for r in rows])
        z = medfilt3(np.array([r[1] for r in rows]))
        x = medfilt3(np.array([r[2] for r in rows]))
        ok = plausible(z, np.array([r[4] for r in rows]), np.array([r[5] for r in rows]), fx)
        t, z, x, rows = t[ok], z[ok], x[ok], [r for r, o in zip(rows, ok) if o]
        if len(rows) < 3:
            continue
        cxn = np.array([r[3] for r in rows])
        tracks.append({"cls": CLS[c], "inst": i, "t": t.round(3).tolist(), "z": z.round(2).tolist(),
                       "x": x.round(2).tolist()})
        inside = np.abs(x) <= corridor
        kind = None
        if inside.any():
            k = int(np.argmin(np.where(inside, z, np.inf)))
        else:
            k = int(np.argmin(z))
        before = (t >= t[k] - 3.0) & (t <= t[k])
        closing = float(z[before].max() - z[k])
        # Under 0.6 s of history the closing figure is one or two noisy frames.
        is_closing = closing >= 1.0 and t[k] - t[0] >= 0.6
        if inside[k] and z[k] < near and is_closing:
            kind = "must"
        elif inside[k] and z[k] < 5.0 and is_closing:
            kind = "mid"
        elif not inside[k] and z[k] < 2.0 and abs(x[k]) <= 2.0 and is_closing:
            kind = "side"
        elif inside[k] and z[k] < near:
            kind = "notclosing"
        if kind is None:
            continue
        far = np.nonzero(z[: k + 1] <= 10.0)[0]
        t_start = float(t[far[0]]) if len(far) else float(t[0])
        # The strict scorer accepts speech from min(t_start - 0.5, t_close - 3); a person
        # in view for 20 s would otherwise let any early "Person ahead" count.
        t_start = max(t_start, float(t[k]) - approach)
        side = "left" if cxn[k] < 1 / 3 else "right" if cxn[k] > 2 / 3 else "ahead"
        win = (t >= t[k] - 1.0) & (t <= t[k])
        dzdt = np.polyfit(t[win], z[win], 1)[0] if win.sum() >= 3 else 0.0
        dxdt = np.polyfit(t[win], x[win], 1)[0] if win.sum() >= 3 else 0.0
        motion = "crossing" if abs(dxdt) > abs(dzdt) and abs(dxdt) > 0.3 else \
            "approaching" if dzdt < -0.3 else "receding" if dzdt > 0.3 else "static"
        own = float(np.hypot(-dzdt - ego(t[k]), dxdt)) if ego and win.sum() >= 3 else None
        # A parked car beside the sidewalk closes at walking speed and is not a hazard.
        # 1.5 m/s leaves room for chest sway: 10 deg/s of yaw moves a point at 2 m by 0.35 m/s.
        if kind == "must" and c == 21 and own is not None and own < 1.5:
            kind = "parked"
        zk = float(z[k])
        note = (f"auto: SANPO {['pedestrian', 'rider', 'vehicle'][list(CLS).index(c)]} inst {i}, "
                f"nearest Z {zk:.1f} m, X {x[k]:+.1f} m at {t[k]:.2f}s, closed {closing:.1f} m in 3 s"
                + (f", own speed {own:.1f} m/s" if own is not None else "") + f" ({kind})")
        events.append({"t_start": round(min(t_start, float(t[k])), 2), "t_close": round(float(t[k]), 2),
                       "cls": CLS[c], "side": side,
                       "dist_bucket": "near" if zk < 2 else "mid" if zk < 5 else "far",
                       "motion": motion, "must_warn": kind == "must",
                       "keywords": KEYWORDS[c], "note": note, "inst": i, "sem": c})
    events = merge_crowd(events)
    events.sort(key=lambda e: (e["t_close"], e["cls"]))
    for n, e in enumerate(events, 1):
        e["id"] = f"e{n}"
    return events, tracks


def merge_crowd(events, gap=1.0):
    """One must_warn event per (class, side) within gap seconds of t_close: the scorer
    credits one utterance per event, and "Person right." covers a group passing
    together (test_videos/labels/README.md labels crowds by their closest member)."""
    must = sorted((e for e in events if e["must_warn"]), key=lambda e: e["t_close"])
    rest = [e for e in events if not e["must_warn"]]
    groups = []
    for e in must:
        g = next((g for g in groups if g[0]["cls"] == e["cls"] and g[0]["side"] == e["side"]
                  and e["t_close"] - g[-1]["t_close"] <= gap), None)
        (g.append(e) if g else groups.append([e]))
    for g in groups:
        e = dict(g[0])
        e["t_start"] = min(m["t_start"] for m in g)
        if len(g) > 1:
            e["note"] += f"; group of {len(g)}, others: " + ", ".join(
                f"inst {m['inst']} at {m['t_close']:.2f}s" for m in g[1:])
        e["members"] = [(m["sem"], m["inst"], m["t_close"]) for m in g]
        rest.append(e)
    return rest


def sheet(stem, events, out):
    import cv2
    must = [e for e in events if e["must_warn"]]
    if not must:
        return
    meta = json.load(open(DATA / "seg" / stem / "meta.json"))
    cap = cv2.VideoCapture(str(DATA / "clips" / f"{stem}.mp4"))
    tiles = []
    for e in must:
        f = int(round(e["t_close"] * meta["fps"]))
        cap.set(cv2.CAP_PROP_POS_FRAMES, f)
        ok, img = cap.read()
        if not ok:
            continue
        img = cv2.resize(img, (480, 270))
        mp = DATA / "seg" / stem / "masks" / f"{f:06d}.png"
        if mp.exists():
            a = cv2.resize(np.array(Image.open(mp).convert("RGB")), (480, 270),
                           interpolation=cv2.INTER_NEAREST).astype(np.int32)
            for sem, inst, _ in e["members"]:
                m = ((a[..., 0] == sem) & (a[..., 1] * 256 + a[..., 2] == inst)).astype(np.uint8)
                cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                cv2.drawContours(img, cnts, -1, (0, 0, 255), 2)
        cv2.line(img, (160, 0), (160, 270), (255, 255, 0), 1)
        cv2.line(img, (320, 0), (320, 270), (255, 255, 0), 1)
        txt = f"{e['id']} {e['cls']} {e['side']} t={e['t_close']:.1f}"
        cv2.putText(img, txt, (6, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 4)
        cv2.putText(img, txt, (6, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)
        tiles.append(img)
    cols = 4
    while len(tiles) % cols:
        tiles.append(np.zeros_like(tiles[0]))
    grid = np.vstack([np.hstack(tiles[r:r + cols]) for r in range(0, len(tiles), cols)])
    out.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out / f"{stem}_must_warn.jpg"), grid, [cv2.IMWRITE_JPEG_QUALITY, 80])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stems", default="")
    ap.add_argument("--corridor", type=float, default=1.0)
    ap.add_argument("--near", type=float, default=3.0)
    ap.add_argument("--approach", type=float, default=APPROACH_S, help="t_start no earlier than t_close minus this")
    ap.add_argument("--sheet", action="store_true", help="results/sanpo/check/<stem>_must_warn.jpg")
    args = ap.parse_args()
    out = DATA / "labels"
    out.mkdir(parents=True, exist_ok=True)
    stems = args.stems.split(",") if args.stems else sorted(os.listdir(DATA / "seg"))
    for stem in stems:
        seg = DATA / "seg" / stem
        meta0 = json.load(open(seg / "meta.json"))
        fx, cx, model, hfov = intrinsics(meta0["sid"])
        meta, series = instance_series(seg, fx, cx)
        ev, tracks = events_for(series, fx, args.corridor, args.near, ego_speed(seg, meta), args.approach)
        if args.sheet:
            sheet(stem, ev, Path("results/sanpo/check"))
        ev = [{k: e[k] for k in ORDER} for e in ev]
        with open(out / f"{stem}.json", "w") as f:
            f.write("[\n" + ",\n".join("  " + json.dumps(e) for e in ev) + "\n]\n")
        json.dump({"stem": stem, "camera": model, "h_fov": hfov, "tracks": tracks},
                  open(out / f"{stem}_tracks.json", "w"))
        mw = sum(e["must_warn"] for e in ev)
        print(f"{stem}: {len(series)} instances, {len(ev)} events, {mw} must_warn "
              f"({', '.join(e['cls'] + '@' + str(e['t_close']) for e in ev if e['must_warn'])})")


if __name__ == "__main__":
    main()
