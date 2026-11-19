"""Pixel measurements for short synthetic clips (flat background, a few flat colors).

`facts(frames, times)` returns plain sentences such as "3 objects appeared in
total" or "the background is blue at the end", or [] when the clip does not
look synthetic, so real-world video goes to the VLM without them. Objects are
connected components of one palette color, tracked by nearest centroid.
"""
import colorsys

import cv2
import numpy as np

WORK_W = 320                 # frames are measured at 320x240 for a 640x480 clip
PALETTE_MAX = 12
SYNTH_COVER = 0.97           # share of pixels the palette must explain
# Measured: the 15 practice-pack clips 0.958 to 1.0; six street clips in
# test_videos/ 0.525 to 0.727. Palette cover alone does not separate them (0.99+ on both).
FLAT_MIN = 0.9
FLAT_MIN_DENOISED = 0.95
MIN_AREA = 0.0004            # of frame area; 31 px at 320x240
MAX_OBJECTS = 15             # more components than this per frame: not a shapes clip
MAX_FPS = 12


def color_name(rgb):
    r, g, b = (c / 255 for c in rgb)
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    if v < 0.2:
        return "black"
    if s < 0.18:
        return "white" if v > 0.85 else "gray"
    h *= 360
    if h < 15 or h >= 340:
        return "red" if v > 0.45 else "dark red"
    if h < 40:
        return "orange" if v > 0.6 else "brown"
    if h < 70:
        return "yellow"
    if h < 165:
        return "green"
    if h < 195:
        return "cyan"
    if h < 255:
        return "blue"
    if h < 290:
        return "purple"
    return "pink"


def flatness(frames):
    """Share of horizontally adjacent pixel pairs that differ by at most 4 in every channel."""
    sel = frames[::max(1, len(frames) // 12)]
    return float(np.mean([(np.abs(np.diff(f.astype(np.int16), axis=1)).max(-1) <= 4).mean() for f in sel]))


def _palette(frames):
    """Dominant colors over the clip, or None when the clip is not flat-colored."""
    px = np.concatenate([f[::4, ::4].reshape(-1, 3) for f in frames])
    q = (px // 16).astype(np.int32)
    key = q[:, 0] * 256 + q[:, 1] * 16 + q[:, 2]
    keys, counts = np.unique(key, return_counts=True)
    order = np.argsort(-counts)
    cents = []
    for k in order:
        if counts[k] < 0.0005 * len(px):
            break
        sel = px[key == keys[k]].astype(np.float32)
        c = sel.mean(0)
        if all(np.abs(c - p).max() > 40 for p in cents):
            cents.append(c)
        if len(cents) >= PALETTE_MAX:
            break
    pal = np.array(cents, np.float32)
    d = np.abs(px[:, None, :].astype(np.float32) - pal[None]).max(-1)
    cover = float((d.min(1) < 40).mean())
    return (pal if cover >= SYNTH_COVER else None), cover


def _lut(pal):
    """Nearest palette index for every 5-bit-per-channel color, -1 when none is within 40."""
    g = (np.arange(32) * 8 + 4).astype(np.int16)
    cube = np.stack(np.meshgrid(g, g, g, indexing="ij"), -1).reshape(-1, 3)
    d = np.abs(cube[:, None, :] - pal[None].astype(np.int16)).max(-1)
    lut = d.argmin(-1)
    lut[d.min(-1) >= 40] = -1
    return lut


def _label(frame, lut):
    q = (frame >> 3).astype(np.int32)
    return lut[(q[..., 0] << 10) | (q[..., 1] << 5) | q[..., 2]]


def _objects(lab, bg, pal_n, area):
    """Components per palette color, minus thin lines and parts inside a larger one."""
    h, w = lab.shape
    objs, lines = [], []
    k3 = np.ones((3, 3), np.uint8)
    cnt = np.bincount(lab[lab >= 0].ravel(), minlength=pal_n)
    for c in range(pal_n):
        if c == bg:
            continue
        m = (lab == c).astype(np.uint8)
        if not m.any():
            continue
        n, _, st, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
        for i in range(1, n):
            x, y, bw, bh, a = st[i]
            if bw > 0.5 * w and bh <= 0.02 * h:
                lines.append((c, x, y, bw, bh))
        # Anti-aliased rims get their own palette entry and would form a ring
        # around every shape. Opening removes them; a color that is all thin
        # strokes (sign border, digits) and does not hug a larger color is kept raw.
        opened = cv2.morphologyEx(m, cv2.MORPH_OPEN, k3)
        if opened.sum() < 0.3 * m.sum():
            bigger = np.isin(lab, [k for k in range(pal_n) if k != bg and cnt[k] > cnt[c]]).astype(np.uint8)
            if (m & cv2.dilate(bigger, k3, iterations=2)).sum() > 0.5 * m.sum():
                continue
            opened = m
        n, _, st, cen = cv2.connectedComponentsWithStats(opened, connectivity=8)
        for i in range(1, n):
            x, y, bw, bh, a = st[i]
            if a < MIN_AREA * area or (bw > 0.5 * w and bh <= 0.02 * h):
                continue
            objs.append({"c": c, "box": (x, y, bw, bh), "a": int(a), "xy": tuple(cen[i])})
    keep = []
    for o in objs:
        x, y, bw, bh = o["box"]
        inside = any(p is not o and p["a"] > o["a"] and p["box"][0] <= x + 2 and p["box"][1] <= y + 2
                     and p["box"][0] + p["box"][2] + 2 >= x + bw and p["box"][1] + p["box"][3] + 2 >= y + bh
                     for p in objs)
        if not inside:
            keep.append(o)
    return keep, lines


def _track(per_frame, times, diag):
    tracks = []
    for fi, objs in enumerate(per_frame):
        live = [t for t in tracks if fi - t["last"] <= 3]
        used = set()
        pairs = sorted(((np.hypot(o["xy"][0] - t["xy"][-1][0], o["xy"][1] - t["xy"][-1][1]), oi, ti)
                        for oi, o in enumerate(objs) for ti, t in enumerate(live) if o["c"] == t["c"]),
                       key=lambda p: p[0])
        taken = set()
        for d, oi, ti in pairs:
            if oi in used or ti in taken or d > 0.25 * diag:
                continue
            t, o = live[ti], objs[oi]
            t["xy"].append(o["xy"]); t["box"].append(o["box"]); t["a"].append(o["a"])
            t["f"].append(fi); t["last"] = fi
            used.add(oi); taken.add(ti)
        for oi, o in enumerate(objs):
            if oi not in used:
                tracks.append({"c": o["c"], "xy": [o["xy"]], "box": [o["box"]], "a": [o["a"]],
                               "f": [fi], "last": fi})
    # A track seen in fewer than 3 frames is a flicker from anti-aliasing or a merge.
    return [t for t in tracks if len(t["f"]) >= 3]


def _turns(vals, prom):
    """Turning points ("max" or "min") of a 3-tap smoothed series that reverse by at least prom."""
    v = np.asarray(vals, float)
    if len(v) < 5:
        return []
    v = np.convolve(np.pad(v, 1, mode="edge"), np.ones(3) / 3, mode="valid")
    out, lo, hi, trend = [], v[0], v[0], 0
    for x in v[1:]:
        if trend == 0:
            hi, lo = max(hi, x), min(lo, x)
            if x <= hi - prom:
                trend, lo = -1, x
            elif x >= lo + prom:
                trend, hi = 1, x
        elif trend == 1:
            if x > hi:
                hi = x
            elif x <= hi - prom:
                out.append("max")
                trend, lo = -1, x
        else:
            if x < lo:
                lo = x
            elif x >= lo + prom:
                out.append("min")
                trend, hi = 1, x
    return out


def _shape(t, w, h):
    """circle, square, rectangle, triangle or None, from fill ratio and aspect of the box."""
    fr = [a / max(1, b[2] * b[3]) for a, b in zip(t["a"], t["box"])
          if b[0] > 1 and b[1] > 1 and b[0] + b[2] < w - 1 and b[1] + b[3] < h - 1]
    if len(fr) < 3:
        return None
    fill = float(np.median(fr))
    asp = float(np.median([b[2] / max(1, b[3]) for b in t["box"]]))
    sq = 0.8 < asp < 1.25
    if fill > 0.9:
        return "square" if sq else "rectangle"
    if 0.7 < fill <= 0.86:
        return "circle" if sq else "oval"
    if 0.4 < fill < 0.6:
        return "triangle"
    return None


def _fmt_t(t):
    return f"{t:.1f} s"


def _dir_words(dx, dy, w, h):
    words = []
    if abs(dx) > 0.05 * w:
        words.append("right" if dx > 0 else "left")
    if abs(dy) > 0.05 * h:
        words.append("down" if dy > 0 else "up")
    return words


def facts(frames, times):
    """frames: list of HxWx3 uint8 RGB arrays; times: seconds for each."""
    if len(frames) < 3:
        return [], {"synthetic": False}
    step = max(1, round((len(times) - 1) / max(1e-6, times[-1] - times[0]) / MAX_FPS))
    keep = list(range(0, len(frames), step))
    if keep[-1] != len(frames) - 1:
        keep.append(len(frames) - 1)
    frames, times = [frames[i] for i in keep], [times[i] for i in keep]
    h0, w0 = frames[0].shape[:2]
    scale = min(1.0, WORK_W / w0)
    small = [cv2.resize(f, (round(w0 * scale), round(h0 * scale)), interpolation=cv2.INTER_AREA)
             if scale < 1 else f for f in frames]
    flat = flatness(small)
    info = {"synthetic": False, "flat": round(flat, 3)}
    if flat < FLAT_MIN:
        # Sensor-like noise on a flat clip: denoised, practice clips with added
        # Gaussian noise sigma 8 to 32 measured 0.94 to 1.0, the street clips 0.79 to 0.93.
        den = [cv2.bilateralFilter(cv2.medianBlur(f, 5), 7, 50, 7) for f in small]
        flat = flatness(den)
        info["flat_denoised"] = round(flat, 3)
        if flat < FLAT_MIN_DENOISED:
            return [], info
        small = den
    pal, cover = _palette(small)
    info.update(synthetic=pal is not None, cover=round(cover, 3))
    if pal is None:
        return [], info
    h, w = small[0].shape[:2]
    area, diag = h * w, float(np.hypot(h, w))
    names = [color_name(c) for c in pal]
    lut = _lut(pal)
    bgs, per_frame, lines_seen = [], [], set()
    for f in small:
        lab = _label(f, lut)
        cnt = np.bincount(lab[lab >= 0].ravel(), minlength=len(pal))
        bg = int(cnt.argmax())
        bgs.append(bg)
        objs, lines = _objects(lab, bg, len(pal), area)
        if len(objs) > MAX_OBJECTS:
            info["too_many"] = len(objs)
            return [], info
        per_frame.append(objs)
        for c, *_ in lines:
            lines_seen.add(names[c])

    out = []
    if bgs[0] == bgs[-1] and len(set(bgs)) == 1:
        out.append(f"The background stays {names[bgs[0]]} the whole time.")
    else:
        seq = [bgs[0]]
        for b in bgs[1:]:
            if b != seq[-1]:
                seq.append(b)
        out.append("The background color changes: " + ", then ".join(names[b] for b in seq)
                   + f". It is {names[bgs[0]]} at the start and {names[bgs[-1]]} at the end.")

    tracks = _track(per_frame, times, diag)
    if not tracks:
        out.append("No separate objects are visible on the background.")
        return out, info
    n_frames = len(small)
    counts = [sum(1 for t in tracks if fi in t["f"]) for fi in range(n_frames)]
    tracks.sort(key=lambda t: t["f"][0])
    first_t = [times[t["f"][0]] for t in tracks]
    for t in tracks:
        shape = _shape(t, w, h)
        t["name"] = f"{names[t['c']]} {shape or 'object'}"
        t["short"] = f"{names[t['c']]}" + (f" {shape}" if shape else "")

    def verb(n, v):
        return v + ("s" if n == 1 else "")

    def n_obj(n):
        return f"{n} object" + ("" if n == 1 else "s")

    out.append(f"{n_obj(len(tracks))} in total {verb(len(tracks), 'appear')} over the clip. "
               f"Visible at the start: {counts[0]}. Most at once: {max(counts)}. "
               f"Visible at the end: {counts[-1]}.")
    late = [t for t in tracks if t["f"][0] > 0]
    if len(late) >= 2 and len(tracks) <= 12:
        out.append("Order of appearance: " + "; ".join(
            f"{t['short']} at {_fmt_t(ft)}" for t, ft in zip(tracks, first_t)) + ".")
    elif len(tracks) <= 12:
        out.append("Objects: " + ", ".join(t["short"] for t in tracks) + ".")
    if len(tracks) > 1 and first_t[-1] - first_t[0] > 0.2:
        out.append(f"First object to appear: {tracks[0]['short']}. "
                   f"Last object to appear: {tracks[-1]['short']}.")
    gone = [t for t in tracks if t["f"][-1] < n_frames - 1 - 3]
    if gone:
        out.append(f"{n_obj(len(gone))} {verb(len(gone), 'disappear')} before the end: " + "; ".join(
            f"{t['short']} at {_fmt_t(times[t['f'][-1]])}" for t in gone) + ".")

    def on_border(b):
        return b[0] <= 1 or b[1] <= 1 or b[0] + b[2] >= w - 1 or b[1] + b[3] >= h - 1

    # Both edges must shift the same way to count as motion, so a bar growing
    # from a fixed base reads as "taller", not "moves up".
    def shift(a0, a1, e0, e1):
        return min(a1 - a0, e1 - e0, key=abs) if (a1 - a0) * (e1 - e0) > 0 else 0

    for t in tracks:
        if len(t["f"]) < 5:
            continue
        inner = [(p, b) for p, b in zip(t["xy"], t["box"]) if not on_border(b)] or list(zip(t["xy"], t["box"]))
        (bx0, by0, bw0, bh0), (bx1, by1, bw1, bh1) = inner[0][1], inner[-1][1]
        nm = t["name"]
        bounces = _turns([p[1] for p, _ in inner], 0.04 * h).count("max")
        x_rev = len(_turns([p[0] for p, _ in inner], 0.04 * w))
        dw = _dir_words(shift(bx0, bx1, bx0 + bw0, bx1 + bw1), shift(by0, by1, by0 + bh0, by1 + bh1), w, h)
        if bounces:
            out.append(f"The {nm} moves up and down; it reaches a lowest point and rises again "
                       f"{bounces} time{'s' if bounces > 1 else ''} (it bounces {bounces} "
                       f"time{'s' if bounces > 1 else ''}).")
        if x_rev:
            out.append(f"The {nm} reverses its left-right direction {x_rev} "
                       f"time{'s' if x_rev > 1 else ''}.")
        if dw and not bounces:
            (x0, y0), (x1, y1) = t["xy"][0], t["xy"][-1]
            out.append(f"The {nm} moves {' and '.join(dw)} overall "
                       f"(from x={x0 / w:.2f}, y={y0 / h:.2f} to x={x1 / w:.2f}, y={y1 / h:.2f} "
                       "of the frame, y grows downward).")
        if bh1 > 1.25 * bh0 + 2:
            out.append(f"The {nm} gets taller (height {bh0} to {bh1} px).")
        elif bh1 < 0.8 * bh0 - 2:
            out.append(f"The {nm} gets shorter (height {bh0} to {bh1} px).")
        if bw1 > 1.25 * bw0 + 2:
            out.append(f"The {nm} gets wider (width {bw0} to {bw1} px).")
        elif bw1 < 0.8 * bw0 - 2:
            out.append(f"The {nm} gets narrower (width {bw0} to {bw1} px).")

    long_tracks = [t for t in tracks if len(t["f"]) >= 5]
    if len(long_tracks) == 2:
        a, b = long_tracks
        common = sorted(set(a["f"]) & set(b["f"]))
        if len(common) >= 5:
            def gap(fi):
                ba, bb = a["box"][a["f"].index(fi)], b["box"][b["f"].index(fi)]
                gx = max(ba[0], bb[0]) - min(ba[0] + ba[2], bb[0] + bb[2])
                gy = max(ba[1], bb[1]) - min(ba[1] + ba[3], bb[1] + bb[3])
                return max(gx, gy, 0)
            g0, g1 = gap(common[0]), gap(common[-1])
            pair = f"{a['name']} and the {b['name']}"
            if g1 <= 2 and g0 > 0.05 * w:
                out.append(f"The {pair} move toward each other until they touch.")
            elif g1 < 0.6 * g0:
                out.append(f"The {pair} get closer together (gap {g0} to {g1} px).")
            elif g1 > 1.6 * g0 + 5:
                out.append(f"The {pair} move apart (gap {g0} to {g1} px).")
    if lines_seen:
        out.append("There is also a thin " + " and ".join(sorted(lines_seen))
                   + " line (a floor or baseline), not counted as an object.")
    return out, info
